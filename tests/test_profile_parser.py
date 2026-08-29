from typing import Any

import pytest

from app.linkedin.errors import UpstreamSchemaChanged
from app.linkedin.parsers.profile import find_profile_urn, parse_profile
from app.linkedin.urls import validate_profile_url


def test_parses_complete_profile(complete_payload: dict[str, Any]) -> None:
    target = validate_profile_url("https://linkedin.com/in/example-person")

    profile = parse_profile(complete_payload, target)

    assert profile.full_name == "Example Person"
    assert profile.headline == "Backend Engineer"
    assert profile.about == "Builds reliable systems."
    assert profile.location.display_name == "Bengaluru, Karnataka, India"
    assert profile.location.country_code == "in"
    assert profile.images.profile is not None
    assert profile.images.profile.width == 800
    assert profile.images.background is not None


def test_parses_sparse_profile() -> None:
    payload = {
        "data": {
            "firstName": "Sparse",
            "publicIdentifier": "sparse",
            "headline": "Engineer",
        }
    }

    profile = parse_profile(payload, validate_profile_url("https://linkedin.com/in/sparse"))

    assert profile.first_name == "Sparse"
    assert profile.last_name is None
    assert profile.full_name == "Sparse"
    assert profile.about is None
    assert profile.experience == []


def test_unexpected_schema_raises_typed_error() -> None:
    with pytest.raises(UpstreamSchemaChanged):
        parse_profile({}, validate_profile_url("https://linkedin.com/in/example"))


def test_finds_profile_urn_without_top_card_fields() -> None:
    payload = {
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": "urn:li:fsd_profile:synthetic",
            }
        ]
    }

    assert find_profile_urn(payload) == "urn:li:fsd_profile:synthetic"
