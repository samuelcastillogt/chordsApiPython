import os
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings

INSECURE_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./chordweaver.db"
    secret_key: str = INSECURE_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://samuelcastillogt.github.io"
    environment: str = "development"

    @field_validator("access_token_expire_minutes", mode="before")
    @classmethod
    def use_default_for_empty_int(cls, value: Any) -> Any:
        if value == "":
            return 60 * 24 * 7
        return value

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Hosted Postgres providers hand out postgres:// URLs; SQLAlchemy async needs asyncpg.
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value[len("postgres://"):]
        elif value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://"):]
        # Serverless filesystems are read-only except /tmp (data there is ephemeral).
        if value.startswith("sqlite+aiosqlite:///./") and os.environ.get("VERCEL"):
            value = "sqlite+aiosqlite:////tmp/" + value[len("sqlite+aiosqlite:///./"):]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production" or bool(os.environ.get("VERCEL"))

    @property
    def auth_enabled(self) -> bool:
        """Accounts are disabled in production until a real secret is configured."""
        return not (self.is_production and self.secret_key == INSECURE_SECRET)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
