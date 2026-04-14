import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = "Gateway Node"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Downstream services ──────────────────────────────────────────
    SCRAPER_URL: str = "http://localhost:8001"
    RANKER_URL: str = "http://localhost:8002"
    BRAIN_URL: str = "http://brain:8001"

    # ── Allowed CORS origins (comma-separated in env) ────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── PostgreSQL ───────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres"
    DB_PASSWORD: str  # Required — no insecure default
    DB_SSL: str = "prefer"

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # ── JWT / Security ───────────────────────────────────────────────
    JWT_SECRET_KEY: str  # Required — no insecure default
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Derived helpers ──────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def scraper_ws_url(self) -> str:
        return self.SCRAPER_URL.replace("http://", "ws://").replace("https://", "wss://")

    @property
    def ranker_ws_url(self) -> str:
        return self.RANKER_URL.replace("http://", "ws://").replace("https://", "wss://")

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v


try:
    settings = Settings()
except Exception as exc:
    print(f"[gateway_node] FATAL — configuration error: {exc}", file=sys.stderr)
    sys.exit(1)
