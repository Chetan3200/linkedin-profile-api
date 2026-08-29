from pathlib import Path

from app.linkedin.parsers.rsc_profile import parse_rsc_profile
from app.linkedin.rsc import FlightDocument
from app.linkedin.urls import validate_profile_url


def test_parses_rsc_top_card() -> None:
    content = (Path(__file__).parent / "fixtures" / "rsc" / "profile.rsc").read_bytes()
    document = FlightDocument.parse(content)
    target = validate_profile_url("https://linkedin.com/in/example-person")

    profile = parse_rsc_profile(document, target, "urn:li:fsd_profile:synthetic")

    assert profile.full_name == "Example Person"
    assert profile.headline == "Backend Engineer"
    assert profile.location.display_name == "Example City"
    assert profile.images.profile is not None
    assert profile.images.profile.width == 800
    assert profile.images.background is not None
    assert profile.images.background.width == 1200
