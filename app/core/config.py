from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "AI Intelligence Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ALLOW_ORIGINS: str = "*"

    # Database
    DATABASE_URL: str

    # RAG
    CHROMA_PATH: str = "./data/chroma"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM
    LLM_PROVIDER: str = "groq"
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "openai/gpt-oss-20b"

    # Authentication
    JWT_SECRET_KEY: str = Field(default="change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Reddit
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "ai-intelligence-platform/0.1"

    # GitHub
    GITHUB_TOKEN: Optional[str] = None

    # Collector
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    MAX_RETRIES: int = 3

    # Scheduler
    SCHEDULER_ENABLED: bool = False
    COLLECTION_INTERVAL_MINUTES: int = 60

   # n8n
    N8N_HIGH_RELEVANCE_WEBHOOK_URL: Optional[str] = None
    N8N_TREND_ESCALATION_WEBHOOK_URL: Optional[str] = None



settings = Settings()