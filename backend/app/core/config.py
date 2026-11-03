# backend/app/core/config.py
import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv, find_dotenv
    # Resolve root directory: config.py is in backend/app/core/ (4 levels up)
    root_env = Path(__file__).resolve().parents[3] / ".env"
    if root_env.is_file():
        load_dotenv(dotenv_path=root_env, override=True)
    else:
        # Fallback to search up directory tree
        load_dotenv(find_dotenv(usecwd=True), override=True)
except ImportError:
    pass

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Vectronyx AI Workbench")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database & Supabase
    DB_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "datasets")

    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_super_secret_jwt_key_change_this_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # LLM Providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    
    # Google Gemini (Primary for Reasoning & 1M context)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Groq Cloud (Ultra-fast chat & agent loop)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Vector Store & Embeddings (Zero PyTorch: Gemini Cloud + FastEmbed ONNX)
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "auto")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    FASTEMBED_MODEL: str = os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")
    VECTOR_STORE_PROVIDER: str = os.getenv("VECTOR_STORE_PROVIDER", "supabase_pgvector")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "768"))

    # Research Agent
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    MAX_SCRAPE_DEPTH: int = int(os.getenv("MAX_SCRAPE_DEPTH", "2"))

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    ]

settings = Settings()
