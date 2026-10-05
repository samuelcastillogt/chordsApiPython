from app.core.config import INSECURE_SECRET, Settings


def test_settings_uses_default_when_token_expiration_env_is_empty(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "")

    settings = Settings()

    assert settings.access_token_expire_minutes == 60 * 24 * 7


def test_postgres_urls_use_asyncpg_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@db.example.com/chordweaver")

    assert Settings().database_url == "postgresql+asyncpg://user:pass@db.example.com/chordweaver"


def test_sqlite_moves_to_tmp_on_vercel(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./chordweaver.db")
    monkeypatch.setenv("VERCEL", "1")

    assert Settings().database_url == "sqlite+aiosqlite:////tmp/chordweaver.db"


def test_accounts_disabled_in_production_with_default_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", INSECURE_SECRET)
    monkeypatch.setenv("VERCEL", "1")

    assert Settings().auth_enabled is False
