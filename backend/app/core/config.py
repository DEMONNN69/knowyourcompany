"""
Configuration settings for the backend application.
Uses environment variables with Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    APP_NAME: str = "Know Your Company - Company Authenticity Checker"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 86400  # 24 hours
    
    # Database
    DATABASE_URL: Optional[str] = None
    FIRESTORE_PROJECT_ID: Optional[str] = None
    FIRESTORE_CREDENTIALS_PATH: Optional[str] = None
    
    # External APIs
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "KnowYourCompany/0.1.0"
    
    # Timeouts and limits
    HTTP_TIMEOUT_SECONDS: int = 10
    MAX_CONCURRENT_REQUESTS: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
