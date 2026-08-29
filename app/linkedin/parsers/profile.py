from typing import Any

from app.linkedin.errors import UpstreamSchemaChanged
from app.linkedin.images import first_resolved_image
from app.linkedin.parsers.common import get_text, root_documents, walk_dicts
from app.linkedin.urls import ProfileTarget
from app.schemas.profile import Location, Profile, ProfileImages


def parse_profile(payload: dict[str, Any], target: ProfileTarget) -> Profile:
    source = _find_profile(payload, target.public_identifier)
    if source is None:
        raise UpstreamSchemaChanged()

    first_name = get_text(source, "firstName", "first_name")
    last_name = get_text(source, "lastName", "last_name")
    full_name = get_text(source, "fullName", "full_name")
    if not full_name:
        full_name = " ".join(value for value in (first_name, last_name) if value) or None

    location, country_code = _location(source)
    profile_image = first_resolved_image(
        source.get(key)
        for key in ("profilePicture", "miniProfile", "pictureInfo", "picture", "displayPicture")
    )
    background_image = first_resolved_image(
        source.get(key) for key in ("backgroundPicture", "backgroundImage", "backgroundPictureInfo")
    )

    return Profile(
        profile_url=target.normalized_url,
        public_identifier=target.public_identifier,
        linkedin_urn=get_text(source, "entityUrn", "profileUrn", "urn"),
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        headline=get_text(source, "headline"),
        location=Location(display_name=location, country_code=country_code),
        about=get_text(source, "summary", "about", "description"),
        industry=_industry(source),
        images=ProfileImages(profile=profile_image, background=background_image),
    )


def find_profile_urn(payload: dict[str, Any]) -> str | None:
    for value in walk_dicts(payload):
        entity_type = value.get("$type")
        urn = get_text(value, "entityUrn", "profileUrn", "urn")
        if isinstance(entity_type, str) and entity_type.endswith(".Profile") and urn:
            return urn
    return None


def _find_profile(payload: dict[str, Any], identifier: str) -> dict[str, Any] | None:
    for root in root_documents(payload):
        direct = root.get("profile")
        if isinstance(direct, dict):
            return direct
        if _looks_like_profile(root):
            return root

    candidates = [item for item in walk_dicts(payload) if _looks_like_profile(item)]
    for item in candidates:
        if get_text(item, "publicIdentifier") == identifier:
            return item
    return candidates[0] if candidates else None


def _looks_like_profile(value: dict[str, Any]) -> bool:
    return bool(
        ("firstName" in value or "lastName" in value)
        and ("headline" in value or "publicIdentifier" in value or "entityUrn" in value)
    )


def _location(source: dict[str, Any]) -> tuple[str | None, str | None]:
    display_name = get_text(source, "geoLocationName", "locationName", "location")
    country_code = get_text(source, "geoCountryUrn", "countryCode", "country_code")
    geo_location = source.get("geoLocation")
    if isinstance(geo_location, dict):
        geo = geo_location.get("geo")
        if isinstance(geo, dict):
            display_name = display_name or get_text(
                geo, "defaultLocalizedName", "defaultLocalizedCountryName"
            )
            country_code = country_code or get_text(geo, "countryCode")
    if country_code and country_code.startswith("urn:"):
        country_code = country_code.rsplit(":", 1)[-1]
    return display_name, country_code


def _industry(source: dict[str, Any]) -> str | None:
    industry = get_text(source, "industryName", "industry")
    if industry:
        return industry
    value = source.get("industry")
    return get_text(value, "name", "localizedName")
