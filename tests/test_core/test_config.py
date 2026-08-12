from app.core.config import Settings


def test_settings_uses_default_when_token_expiration_env_is_empty(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "")

    settings = Settings()

    assert settings.access_token_expire_minutes == 60
