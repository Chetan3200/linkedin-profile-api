import pytest

from app.linkedin.errors import InvalidProfileURL
from app.linkedin.urls import validate_profile_url


@pytest.mark.parametrize(
    ("url", "identifier"),
    [
        ("https://www.linkedin.com/in/example/", "example"),
        ("https://linkedin.com/in/example", "example"),
        (
            "https://www.linkedin.com/in/example/?originalSubdomain=in#fragment",
            "example",
        ),
        ("https://uk.linkedin.com/in/example-person/", "example-person"),
    ],
)
def test_accepts_and_normalizes_profile_urls(url: str, identifier: str) -> None:
    target = validate_profile_url(url)

    assert target.public_identifier == identifier
    assert target.normalized_url == f"https://www.linkedin.com/in/{identifier}/"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com.evil.com/in/example/",
        "https://www.linkedin.com/in/",
        "https://www.linkedin.com/company/example/",
        "https://www.linkedin.com/jobs/",
        "http://www.linkedin.com/in/example/",
        "https://www.linkedin.com/in/example/details/",
        "https://www.linkedin.com/in/example%2Fadmin/",
    ],
)
def test_rejects_non_profile_and_malicious_urls(url: str) -> None:
    with pytest.raises(InvalidProfileURL):
        validate_profile_url(url)
