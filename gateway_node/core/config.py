import os
from pydantic import BaseModel
from typing import Optional

class Settings(BaseModel):
    # App Settings
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Gateway Node")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # URLs
    SCRAPER_URL: str = os.getenv("SCRAPER_URL", "http://localhost:8001")
    RANKER_URL: str = os.getenv("RANKER_URL", "http://localhost:8002")
    BRAIN_URL: str = os.getenv("BRAIN_URL", "http://brain:8001")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_SSL: str = os.getenv("DB_SSL", "prefer")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def scraper_ws_url(self) -> str:
        return self.SCRAPER_URL.replace("http://", "ws://").replace("https://", "wss://")

    @property
    def ranker_ws_url(self) -> str:
        return self.RANKER_URL.replace("http://", "ws://").replace("https://", "wss://")

settings = Settings()
