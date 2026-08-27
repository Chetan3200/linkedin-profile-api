from collections.abc import Iterable
from typing import Any

from app.schemas.profile import Image


def resolve_vector_image(value: Any) -> Image | None:
    vector = _find_vector(value)
    if vector is None:
        return None

    root = vector.get("rootUrl") or vector.get("root_url")
    artifacts = vector.get("artifacts")
    if not isinstance(root, str) or not isinstance(artifacts, list):
        return None

    valid = [artifact for artifact in artifacts if isinstance(artifact, dict)]
    if not valid:
        return None
    artifact = max(valid, key=_image_area)
    segment = artifact.get("fileIdentifyingUrlPathSegment") or artifact.get("pathSegment")
    if not isinstance(segment, str):
        return None
    return Image(
        url=f"{root}{segment}",
        width=_as_int(artifact.get("width")),
        height=_as_int(artifact.get("height")),
    )


def _find_vector(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("rootUrl"), str) and isinstance(value.get("artifacts"), list):
        return value

    preferred = (
        "vectorImage",
        "com.linkedin.common.VectorImage",
        "displayImageReference",
        "displayImage",
        "picture",
        "logo",
    )
    for key in preferred:
        nested = value.get(key)
        found = _find_vector(nested)
        if found:
            return found
    for nested in value.values():
        found = _find_vector(nested)
        if found:
            return found
    return None


def first_resolved_image(values: Iterable[Any]) -> Image | None:
    for value in values:
        image = resolve_vector_image(value)
        if image:
            return image
    return None


def _image_area(artifact: dict[str, Any]) -> int:
    return (_as_int(artifact.get("width")) or 0) * (_as_int(artifact.get("height")) or 0)


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
