"""
Core application configuration using Pydantic Settings v2.
Environment variables loaded from .env file.
"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "Churchill Application Portal"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Computed database URL
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{
            self.POSTGRES_USER}:{
            self.POSTGRES_PASSWORD}@{
            self.POSTGRES_HOST}:{
                self.POSTGRES_PORT}/{
                    self.POSTGRES_DB}"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174"]

    # Azure Services
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "documents"
    AZURE_FORM_RECOGNIZER_ENDPOINT: Optional[str] = None
    AZURE_FORM_RECOGNIZER_KEY: Optional[str] = None
    AZURE_VISION_ENDPOINT: Optional[str] = None
    AZURE_VISION_KEY: Optional[str] = None
    AZURE_COMMUNICATION_CONNECTION_STRING: Optional[str] = None

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Email (Azure Communication Services or SMTP fallback)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@churchilleducation.edu.au"
    EMAILS_FROM_NAME: str = "Churchill Education"

    # File Upload
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_DOCUMENT_EXTENSIONS: set[str] = {
        ".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"}

    # Multi-tenancy
    CHURCHILL_RTO_ID: Optional[str] = None  # Set during first migration

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
