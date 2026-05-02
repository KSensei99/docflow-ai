from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"          # swap: mistral, llama3.2, etc.
    ollama_timeout: int = 120

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "product_catalog"

    # Embedding model (runs locally via sentence-transformers)
    embedding_model: str = "all-MiniLM-L6-v2"

    # File paths
    upload_dir: Path = Path("uploads")
    output_dir: Path = Path("outputs")

    # Pipeline
    confidence_threshold: float = 0.75   # below → HITL review queue
    max_file_size_mb: int = 20

    # Webhook output (optional — set in .env)
    webhook_url: str = ""
    webhook_enabled: bool = False

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure dirs exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
