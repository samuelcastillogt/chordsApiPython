from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/chordweaver"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000"

    @field_validator("access_token_expire_minutes", mode="before")
    @classmethod
    def use_default_for_empty_int(cls, value: Any) -> Any:
        if value == "":
            return 60
        return value

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
