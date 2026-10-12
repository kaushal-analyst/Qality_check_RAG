"""RAG orchestration service coordinating retrieval, generation, and verification."""
from typing import Dict, Any, Optional, List
from src.retrieval.hybrid_retriever import retrieve_hybrid_evidence
from src.rag.prompt_builder import build_rag_prompt
from src.rag.llm_adapter import llm_adapter
from src.rag.verification import verify_citations, check_evidence_sufficiency
from src.products.service import get_product_by_id

def answer_quality_question(
    question: str,
    product_id: int,
    customer_id: Optional[int] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    End-to-end grounded RAG answering with product scope, hybrid retrieval,
    prompt-injection defense, and citation verification.
    """
    product = get_product_by_id(product_id)
    if not product:
        return {
            "answer": "Error: Specified product does not exist.",
            "citations": [],
            "evidence_sufficient": False,
            "verification": {"is_grounded": False}
        }

    # 1. Retrieve hybrid evidence with strict product and customer filtering
    evidence_chunks = retrieve_hybrid_evidence(
        query_text=question,
        product_id=product_id,
        customer_id=customer_id,
        top_k=top_k
    )

    is_sufficient = check_evidence_sufficiency(evidence_chunks)

    # 2. Build injection-hardened prompt
    prompt = build_rag_prompt(
        query=question,
        retrieved_chunks=evidence_chunks,
        product_context=product
    )

    # 3. Generate response using LLM or deterministic engine
    raw_answer = llm_adapter.generate_response(
        prompt=prompt,
        query=question,
        retrieved_chunks=evidence_chunks,
        product_context=product
    )

    # 4. Verify citations against actual database chunks
    verification_results = verify_citations(raw_answer, evidence_chunks)

    return {
        "question": question,
        "product_id": product_id,
        "product_name": product["name"],
        "product_sku": product["sku"],
        "answer": raw_answer,
        "retrieved_evidence": evidence_chunks,
        "evidence_sufficient": is_sufficient,
        "verification": verification_results
    }
