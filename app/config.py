from pathlib import Path

from fastapi import FastAPI
from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define the base directory using pathlib
BASE_DIR = Path(__file__).resolve().parent.parent

# Configure loguru
logger.add(f"{BASE_DIR}/logs/logs.log", rotation="100 MB", level="INFO")


class Settings(BaseSettings):
    APP_TITLE_UUID: str = None  # Required value
    SECRET_KEY: str = "default_secret_key"  # Default value
    ALGORITHM: str = "HS256"  # Default value
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKENS_COOKIE_SECURE: bool = True  # Default value, should be set to True in production
    DOCS_URL: str | None = None  # Default value
    REDOC_URL: str | None = None  # Default value
    UVICORN_PORT: str | None = "8000"  # Default value
    ALLOW_ORIGINS: list[str] = ["*"]  # CORS origins

    POSTGRES_USER: str = None
    POSTGRES_PASSWORD: str = None
    POSTGRES_HOST: str = None
    POSTGRES_PORT: str = None
    POSTGRES_DB: str = None
    POSTGRES_SCHEMA: str = None

    # Configuration for loading environment variables from the .env file
    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")


# Create an instance of the settings
settings = Settings()
# Get the database URL
database_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# Create an instance of FastAPI with documentation URLs loaded from environment variables
app = FastAPI(
    docs_url=settings.DOCS_URL if settings.DOCS_URL != "None" else None,
    redoc_url=settings.REDOC_URL if settings.REDOC_URL != "None" else None,
)
