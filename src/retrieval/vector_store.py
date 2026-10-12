"""Vector store client managing ChromaDB embeddings and semantic search."""
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from src.config import settings

_chroma_client = None
_embedding_model = None

def get_embedding_model():
    """Lazily loads SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        except Exception as e:
            print(f"Warning: Could not load SentenceTransformer ({e}). Using deterministic pseudo-embeddings.")
            _embedding_model = None
    return _embedding_model

def get_chroma_client():
    """Initializes and returns persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
    return _chroma_client

def get_collection(name: str = "product_knowledge"):
    """Gets or creates the Chroma collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generates embedding vectors for a list of texts."""
    model = get_embedding_model()
    if model is not None:
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return vectors.tolist()
    else:
        # Fallback deterministic 64-dim vector if model fails to download
        import hashlib
        embeddings = []
        for text in texts:
            vec = [0.0] * 64
            for word in text.lower().split():
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                idx = h % 64
                vec[idx] += 1.0
            norm = sum(x**2 for x in vec) ** 0.5 or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings

def index_chunks(chunks: List[Dict[str, Any]], doc_metadata: Dict[str, Any]):
    """Indexes document chunks into ChromaDB."""
    if not chunks:
        return
    
    collection = get_collection()
    texts = [c["content"] for c in chunks]
    embeddings = generate_embeddings(texts)
    ids = [c["chunk_id"] for c in chunks]
    
    metadatas = []
    for c in chunks:
        meta = {
            "chunk_id": str(c["chunk_id"]),
            "document_id": str(doc_metadata.get("document_id", "")),
            "doc_db_id": int(doc_metadata.get("id", 0)),
            "product_id": int(c["product_id"]),
            "customer_id": int(c["customer_id"]) if c.get("customer_id") else 0,
            "category": str(doc_metadata.get("category", "")),
            "revision": str(doc_metadata.get("revision", "1.0")),
            "approval_status": str(doc_metadata.get("approval_status", "Approved")),
            "page_number": int(c.get("page_number", 1)),
            "section_title": str(c.get("section_title", "General"))
        }
        metadatas.append(meta)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )

def query_vector_store(
    query_text: str,
    product_id: int,
    customer_id: Optional[int] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Performs semantic search with product and customer metadata filters."""
    collection = get_collection()
    query_embedding = generate_embeddings([query_text])[0]
    
    where_filter: Dict[str, Any] = {"product_id": product_id}
    # Notice: In ChromaDB, multiple filters require $and syntax
    if customer_id:
        where_filter = {
            "$and": [
                {"product_id": product_id},
                {"$or": [{"customer_id": customer_id}, {"customer_id": 0}]}
            ]
        }
        
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    hits = []
    if results and results.get("ids") and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            # Convert cosine distance to similarity score
            sim_score = max(0.0, 1.0 - (distance / 2.0))
            hits.append({
                "chunk_id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": sim_score,
                "source": "vector"
            })
    return hits
