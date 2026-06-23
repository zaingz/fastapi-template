import pytest
from pydantic import ValidationError

from app.core.config import _INSECURE_SECRET_KEY, Settings


def test_production_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(ENVIRONMENT="production", SECRET_KEY=_INSECURE_SECRET_KEY)


def test_production_accepts_overridden_secret_key():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-real-secret-value-well-over-32-characters-long",
    )
    assert settings.is_production


def test_non_production_allows_default_secret_key():
    settings = Settings(ENVIRONMENT="local")
    assert settings.SECRET_KEY.get_secret_value() == _INSECURE_SECRET_KEY
