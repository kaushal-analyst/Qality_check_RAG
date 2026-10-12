import os
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
DATABASE_PATH = DATA_DIR / "quality_ai.db"

# Ensure directories exist
for directory in [DATA_DIR, UPLOADS_DIR, PROCESSED_DIR, VECTOR_STORE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "Code Space Techlab AI Quality Control & Complaint System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DB_PATH: str = str(DATABASE_PATH)
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIRECTORY: str = str(VECTOR_STORE_DIR)
    
    # LLM Settings (Ollama default, optional OpenAI fallback)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:latest")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    USE_MOCK_LLM_IF_UNAVAILABLE: bool = True
    
    # Security & Sessions
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cst-quality-ai-secret-salt-key-2026")
    SESSION_EXPIRY_HOURS: int = 24
    
    # File Upload Limits
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".jpg", ".jpeg", ".png"]
    MAX_FILE_SIZE_MB: int = 50
    
    # RAG Retrieval Settings
    TOP_K_RETRIEVAL: int = 5
    HYBRID_ALPHA: float = 0.6  # 0.6 semantic, 0.4 keyword BM25
    MIN_SIMILARITY_SCORE: float = 0.25
    
    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
