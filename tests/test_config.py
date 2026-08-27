from pydantic import SecretStr

from app.config import Settings


def test_csrf_token_defaults_to_unquoted_jsessionid() -> None:
    settings = Settings(
        _env_file=None,
        LINKEDIN_LI_AT="test-li-at",
        LINKEDIN_JSESSIONID='"ajax:test-session"',
    )

    assert settings.csrf_token == "ajax:test-session"


def test_explicit_csrf_token_takes_precedence() -> None:
    settings = Settings(
        _env_file=None,
        LINKEDIN_LI_AT="test-li-at",
        LINKEDIN_JSESSIONID='"ajax:test-session"',
        LINKEDIN_CSRF_TOKEN=SecretStr("explicit-token"),
    )

    assert settings.csrf_token == "explicit-token"
