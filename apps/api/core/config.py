import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "FactoryIQ API"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://factoryiq_user:factoryiq_pass@localhost:5432/factoryiq",
        description="Async SQLAlchemy database URL"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/factoryiq",
        description="Sync SQLAlchemy database URL for migrations/seeding"
    )
    
    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # JWT Security Settings
    SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="HMAC SHA256 secret key for signing tokens"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week for development ease
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
