from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Central application settings loaded from environment/.env.
    Defaults favor a simple local SQLite dev setup; override DATABASE_URL for Postgres.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Database (override with postgres URL in production)
    # Examples:
    #   SQLite (dev):  sqlite+aiosqlite:///./buddyagents.db
    #   Postgres:      postgresql://user:password@localhost:5432/buddyagents
    DATABASE_URL: str = "sqlite+aiosqlite:///./buddyagents.db"

    # Redis (optional for caching / task queue)
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # AI Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # GitHub Token (for using GitHub Copilot API as fallback)
    GITHUB_TOKEN: str = ""
    
    # Murf AI TTS Configuration
    MURF_API_KEY: str = ""
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4"  # Your deployment name in Azure
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"  # API version

    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Application meta
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    PROJECT_NAME: str = "BuddyAgents"
    VERSION: str = "0.1.0"

    @property
    def database_url_async(self) -> str:
        """Return an async-compatible SQLAlchemy URL.
        If already async (contains '+asyncpg' or '+aiosqlite'), return as-is.
        If it's a plain Postgres URL, adapt to asyncpg.
        """
        url = self.DATABASE_URL
        if "+asyncpg" in url or "+aiosqlite" in url:
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Fallback for plain sqlite path (sync) -> aiosqlite
        if url.startswith("sqlite:///") and "+aiosqlite" not in url:
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url


settings = Settings()
