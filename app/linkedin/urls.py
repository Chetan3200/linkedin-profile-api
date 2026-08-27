import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from app.linkedin.errors import InvalidProfileURL

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")


@dataclass(frozen=True)
class ProfileTarget:
    public_identifier: str
    normalized_url: str


def validate_profile_url(value: str) -> ProfileTarget:
    if not value or len(value) > 500:
        raise InvalidProfileURL()

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise InvalidProfileURL() from exc

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or parsed.username or parsed.password:
        raise InvalidProfileURL()
    if hostname != "linkedin.com" and not hostname.endswith(".linkedin.com"):
        raise InvalidProfileURL("The URL host must be linkedin.com.")
    if port not in (None, 443):
        raise InvalidProfileURL()

    parts = parsed.path.split("/")
    if len(parts) not in (3, 4) or parts[0] or parts[1] != "in" or (len(parts) == 4 and parts[3]):
        raise InvalidProfileURL("The URL must identify one LinkedIn member profile.")

    raw_identifier = parts[2]
    identifier = unquote(raw_identifier)
    if identifier != raw_identifier or not IDENTIFIER_RE.fullmatch(identifier):
        raise InvalidProfileURL("The LinkedIn public identifier is malformed.")

    return ProfileTarget(
        public_identifier=identifier,
        normalized_url=f"https://www.linkedin.com/in/{identifier}/",
    )
