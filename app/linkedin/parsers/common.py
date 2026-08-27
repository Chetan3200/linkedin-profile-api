from collections.abc import Iterable
from typing import Any

from app.schemas.profile import DateParts


def root_documents(payload: dict[str, Any]) -> list[dict[str, Any]]:
    roots = [payload]
    data = payload.get("data")
    if isinstance(data, dict):
        roots.insert(0, data)
    return roots


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def get_text(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        result = value.get(key)
        if isinstance(result, str) and result.strip():
            return result.strip()
        if isinstance(result, dict):
            text = result.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def parse_date(value: Any) -> DateParts | None:
    if not isinstance(value, dict):
        return None
    year = _int_or_none(value.get("year"))
    month = _int_or_none(value.get("month"))
    day = _int_or_none(value.get("day"))
    if year is None and month is None and day is None:
        return None
    return DateParts(year=year, month=month, day=day)


def parse_period(value: Any) -> tuple[DateParts | None, DateParts | None]:
    if not isinstance(value, dict):
        return None, None
    return (
        parse_date(value.get("startDate") or value.get("start")),
        parse_date(value.get("endDate") or value.get("end")),
    )


def section_value(payload: dict[str, Any], names: tuple[str, ...]) -> tuple[bool, Any]:
    normalized = {name.lower() for name in names}
    for root in root_documents(payload):
        for key, value in root.items():
            if key.lower() in normalized:
                return True, value
    return False, None


def section_elements(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError("section items are not objects")
        return value
    if not isinstance(value, dict):
        raise ValueError("section is not an object")
    for key in ("elements", "items", "components", "*elements"):
        items = value.get(key)
        if isinstance(items, list):
            if not all(isinstance(item, dict) for item in items):
                raise ValueError("section items are not objects")
            return items
    if not value:
        return []
    if any(key in value for key in ("name", "title", "schoolName", "companyName")):
        return [value]
    raise ValueError("section elements are missing")


def included_entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    included = payload.get("included")
    if not isinstance(included, list):
        return []
    return [item for item in included if isinstance(item, dict)]


def hydrate_entities(
    entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    entity_map: dict[str, dict[str, Any]] = {}
    for entity in entities:
        for key in ("entityUrn", "dashEntityUrn", "trackingUrn"):
            urn = entity.get(key)
            if isinstance(urn, str):
                entity_map[urn] = entity

    return ([_hydrate(entity, entity_map, 0, set()) for entity in entities], entity_map)


def _hydrate(
    value: Any,
    entity_map: dict[str, dict[str, Any]],
    depth: int,
    seen: set[str],
) -> Any:
    if depth >= 5:
        return value
    if isinstance(value, list):
        return [_hydrate(item, entity_map, depth + 1, seen) for item in value]
    if not isinstance(value, dict):
        return value

    hydrated: dict[str, Any] = {}
    for key, child in value.items():
        output_key = key.removeprefix("*")
        if key.startswith("*"):
            hydrated[output_key] = _resolve_reference(child, entity_map, depth + 1, seen)
        else:
            hydrated[output_key] = _hydrate(child, entity_map, depth + 1, seen)
    return hydrated


def _resolve_reference(
    value: Any,
    entity_map: dict[str, dict[str, Any]],
    depth: int,
    seen: set[str],
) -> Any:
    if isinstance(value, str) and value in entity_map:
        if value in seen:
            return entity_map[value]
        return _hydrate(entity_map[value], entity_map, depth, seen | {value})
    if isinstance(value, list):
        return [_resolve_reference(item, entity_map, depth, seen) for item in value]
    return _hydrate(value, entity_map, depth, seen)


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
