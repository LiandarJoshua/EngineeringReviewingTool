from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://erp_user:changeme@localhost:5432/engineering_review"

    # Redis / Celery
    redis_url: str = "redis://:changeme@localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_token: str = "changeme_local"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_primary_model: str = "qwen2.5-coder:7b"
    ollama_synthesis_model: str = "mistral:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_reviewer_model: str = "reviewer-model"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_user: str = "minioadmin"
    minio_password: str = "changeme"
    minio_bucket: str = "reviews"

    # LangFuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3001"

    # GitHub integration
    github_token: str = ""                  # PAT with repo + pull-request write scope
    github_webhook_secret: str = ""         # Secret for validating webhook payloads

    # App
    secret_key: str = "changeme_local_jwt_secret"
    environment: str = "development"
    log_level: str = "INFO"

    # Admin credentials (single-user auth)
    admin_email: str = "admin@local.dev"
    admin_password: str = "Admin1234!"

    # Celery queues
    celery_reviews_queue: str = "reviews"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
