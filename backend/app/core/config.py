from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Grand Central Station"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    MEDIA_ROOT: str = "media"
    ARCHIVE_AFTER_DAYS: int = 30
    MESSAGE_CHECK_INTERVAL: int = Field(60, env="MESSAGE_CHECK_INTERVAL")
    
    RATE_LIMIT_INITIAL_DELAY: int = 1
    RATE_LIMIT_MAX_DELAY: int = 300
    RATE_LIMIT_BACKOFF_FACTOR: float = 2.0
    
    GRINDR_USERNAME: Optional[str] = Field(None, env="GRINDR_USERNAME")
    GRINDR_PASSWORD: Optional[str] = Field(None, env="GRINDR_PASSWORD")
    SNIFFIES_USERNAME: Optional[str] = Field(None, env="SNIFFIES_USERNAME")
    SNIFFIES_PASSWORD: Optional[str] = Field(None, env="SNIFFIES_PASSWORD")
    ALIBABA_USERNAME: Optional[str] = Field(None, env="ALIBABA_USERNAME")
    ALIBABA_PASSWORD: Optional[str] = Field(None, env="ALIBABA_PASSWORD")
    
    ENABLE_AUTO_REPLY: bool = Field(True, env="ENABLE_AUTO_REPLY")
    DEBUG: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()