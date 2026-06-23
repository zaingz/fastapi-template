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


@pytest.mark.parametrize("raw", ["none", "None", " self ", "self"])
def test_csp_bare_keyword_is_normalized_to_quoted_form(raw):
    # A bare CSP keyword (as produced when dotenv strips quotes from .env) must be
    # re-quoted, else browsers treat `none`/`self` as a host source and ignore the directive.
    expected = f"'{raw.strip().lower()}'"
    settings = Settings(CSP_FRAME_ANCESTORS=raw)
    assert expected == settings.CSP_FRAME_ANCESTORS


def test_csp_already_quoted_value_is_preserved():
    settings = Settings(CSP_FRAME_ANCESTORS="'self'")
    assert settings.CSP_FRAME_ANCESTORS == "'self'"
