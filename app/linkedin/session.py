import httpx

from app.config import Settings
from app.linkedin.endpoints import BASE_URL
from app.linkedin.errors import LinkedInAuthRequired

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def create_linkedin_client(settings: Settings) -> httpx.AsyncClient:
    if not settings.linkedin_configured:
        raise LinkedInAuthRequired()

    assert settings.linkedin_li_at is not None
    assert settings.linkedin_jsessionid is not None
    cookies = httpx.Cookies()
    cookies.set(
        "li_at",
        settings.linkedin_li_at.get_secret_value(),
        domain=".linkedin.com",
        path="/",
    )
    cookies.set(
        "JSESSIONID",
        settings.linkedin_jsessionid.get_secret_value(),
        domain=".linkedin.com",
        path="/",
    )
    timeout = httpx.Timeout(
        settings.linkedin_timeout_seconds,
        connect=min(10.0, settings.linkedin_timeout_seconds),
        pool=min(10.0, settings.linkedin_timeout_seconds),
    )
    return httpx.AsyncClient(
        base_url=BASE_URL,
        cookies=cookies,
        headers={
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "en-US,en;q=0.9",
            "csrf-token": settings.csrf_token,
            "user-agent": USER_AGENT,
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
        },
        follow_redirects=False,
        timeout=timeout,
    )
