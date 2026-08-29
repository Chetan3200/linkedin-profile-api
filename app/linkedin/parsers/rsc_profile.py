from typing import Any

from app.linkedin.images import resolve_rsc_image
from app.linkedin.rsc import FlightDocument
from app.linkedin.urls import ProfileTarget
from app.schemas.profile import Location, Profile, ProfileImages

TOP_CARD_MARKER = "com.linkedin.sdui.impl.profile.components.topCard"
MEMBER_PHOTO_VIEW = "profile-top-card-member-photo"
ABOUT_MARKER = "com.linkedin.sdui.impl.profile.components.aboutSection"


def parse_rsc_profile(
    document: FlightDocument, target: ProfileTarget, linkedin_urn: str | None
) -> Profile:
    top_card = next(
        (
            value
            for value in document.root_objects()
            if value.get("observabilityIdentifier") == TOP_CARD_MARKER
        ),
        None,
    )
    if top_card is None:
        raise ValueError("RSC top card is missing")

    identity = _identity_container(top_card)
    full_name = _first_element_text(identity, "h2")
    paragraphs = _element_texts(identity, "p")
    headline = max(paragraphs, key=len) if paragraphs else None
    location_values = _design_texts(identity)
    location = max(location_values, key=len) if location_values else None

    profile_image = _tracked_image(top_card, MEMBER_PHOTO_VIEW)
    all_images = _images(top_card)
    background = max(all_images, key=_aspect_ratio, default=None)
    if background == profile_image:
        background = None

    return Profile(
        profile_url=target.normalized_url,
        public_identifier=target.public_identifier,
        linkedin_urn=linkedin_urn,
        full_name=full_name,
        headline=headline,
        location=Location(display_name=location),
        images=ProfileImages(profile=profile_image, background=background),
    )


def merge_profiles(primary: Profile, fallback: Profile) -> Profile:
    data = fallback.model_dump()
    for field in (
        "linkedin_urn",
        "first_name",
        "last_name",
        "full_name",
        "headline",
        "about",
        "industry",
    ):
        value = getattr(primary, field)
        if value:
            data[field] = value
    if primary.location.display_name:
        data["location"] = primary.location.model_dump()
    if primary.images.profile:
        data["images"]["profile"] = primary.images.profile.model_dump()
    if primary.images.background:
        data["images"]["background"] = primary.images.background.model_dump()
    return Profile.model_validate(data)


def parse_rsc_about(document: FlightDocument) -> str | None:
    section = next(
        (
            value
            for value in document.root_objects()
            if value.get("observabilityIdentifier") == ABOUT_MARKER
        ),
        None,
    )
    if section is None:
        return None

    candidates: list[str] = []
    for value in _walk(section):
        if not isinstance(value, dict) or not isinstance(value.get("textProps"), dict):
            continue
        text = _rendered_content(value["textProps"].get("children"))
        text = _normalize_rendered_text(text)
        if text:
            candidates.append(text)
    return max(candidates, key=len, default=None)


def _identity_container(top_card: dict[str, Any]) -> Any:
    candidates: list[tuple[int, Any]] = []
    for value in _walk(top_card):
        if not _is_element(value):
            continue
        elements = [item for item in _walk(value) if _is_element(item)]
        headings = [item for item in elements if item[1] == "h2" and _node_text(item)]
        paragraphs = [item for item in elements if item[1] == "p" and _node_text(item)]
        design_text = [
            item
            for item in _walk(value)
            if isinstance(item, dict)
            and isinstance(item.get("textProps"), dict)
            and _strings(item["textProps"].get("children"))
        ]
        if len(headings) == 1 and paragraphs and design_text:
            candidates.append((len(elements), value))
    if not candidates:
        return top_card
    return min(candidates, key=lambda item: item[0])[1]


def _first_element_text(value: Any, tag: str) -> str | None:
    values = _element_texts(value, tag)
    return values[0] if values else None


def _element_texts(value: Any, tag: str) -> list[str]:
    result: list[str] = []
    for item in _walk(value):
        if _is_element(item) and item[1] == tag:
            text = _node_text(item)
            if text and text not in result:
                result.append(text)
    return result


def _node_text(element: list[Any]) -> str | None:
    props = element[3]
    if not isinstance(props, dict):
        return None
    values = _strings(props.get("children"))
    return values[0] if values else None


def _design_texts(value: Any) -> list[str]:
    result: list[str] = []
    for item in _walk(value):
        if not isinstance(item, dict) or not isinstance(item.get("textProps"), dict):
            continue
        for text in _strings(item["textProps"].get("children")):
            if text not in result and len(text) > 1:
                result.append(text)
    return result


def _strings(value: Any) -> list[str]:
    result: list[str] = []
    for item in _walk(value):
        if isinstance(item, str) and item.strip() and not item.startswith("$"):
            result.append(item.strip())
    return result


def _tracked_image(value: Any, view_name: str):
    for item in _walk(value):
        if not isinstance(item, dict):
            continue
        tracking = item.get("viewTrackingSpecs")
        if not isinstance(tracking, dict) or tracking.get("viewName") != view_name:
            continue
        images = _images(item)
        if images:
            return images[0]
    return None


def _images(value: Any):
    result = []
    seen: set[str] = set()
    for item in _walk(value):
        if not isinstance(item, dict):
            continue
        image = resolve_rsc_image(item.get("renderPayload"))
        if image and image.url not in seen:
            seen.add(image.url)
            result.append(image)
    return result


def _aspect_ratio(image) -> float:
    if not image.width or not image.height:
        return 0
    return image.width / image.height


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _is_element(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and value[0] == "$"


def _rendered_content(value: Any) -> str:
    if isinstance(value, str):
        return "" if value.startswith("$") else value
    if _is_element(value):
        if value[1] == "br":
            return "\n"
        props = value[3]
        return _rendered_content(props.get("children")) if isinstance(props, dict) else ""
    if isinstance(value, list):
        return "".join(_rendered_content(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("textProps"), dict):
            return _rendered_content(value["textProps"].get("children"))
        return _rendered_content(value.get("children"))
    return ""


def _normalize_rendered_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.replace("\u00a0", " ").splitlines()]
    return "\n".join(line for line in lines if line).strip()
