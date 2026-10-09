"""Application settings, read from environment variables (and `.env` in development)."""

import os
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,https://samuelcastillogt.github.io"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Firebase Authentication: the project whose ID tokens the API accepts.
    # Empty disables accounts (analysis endpoints keep working).
    firebase_project_id: str = ""
    # Firestore credentials: a service account key, as JSON or base64-encoded JSON. Empty uses
    # Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS, Google Cloud) or the
    # emulator when FIRESTORE_EMULATOR_HOST is set.
    firebase_service_account: str = ""
    firestore_database: str = "(default)"
    # Prefix of this app's collections, so it can share a Firebase project with other apps.
    firestore_collection_prefix: str = "chordweaver_"
    # host:port of the Firebase Auth emulator (e.g. 127.0.0.1:9099). Its tokens are unsigned,
    # so it is honoured only outside production.
    firebase_auth_emulator_host: str = ""

    cors_origins: str = DEFAULT_CORS_ORIGINS

    # Payment processor behind /api/v1/billing. "mock" activates plans without charging anything.
    billing_provider: Literal["mock"] = "mock"

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        # "Production", "prod" or "dev" in a hosting dashboard must not crash the app on startup.
        aliases = {"prod": "production", "dev": "development", "local": "development"}
        if isinstance(value, str):
            text = value.strip().lower()
            return aliases.get(text, text)
        return value

    @field_validator("log_level", mode="after")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        return level if level in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"} else "INFO"

    @field_validator("firebase_project_id", mode="after")
    @classmethod
    def strip_project_id(cls, value: str) -> str:
        return value.strip()

    @property
    def is_production(self) -> bool:
        return self.environment == "production" or bool(os.environ.get("VERCEL"))

    @property
    def auth_enabled(self) -> bool:
        """Accounts need a Firebase project to verify sign-in tokens against."""
        return bool(self.firebase_project_id)

    @property
    def uses_auth_emulator(self) -> bool:
        return bool(self.firebase_auth_emulator_host) and not self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
