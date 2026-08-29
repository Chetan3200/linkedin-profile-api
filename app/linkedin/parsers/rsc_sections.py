import json
import re
from collections.abc import Iterable
from typing import Any

from app.linkedin.rsc import FlightDocument
from app.schemas.profile import (
    Certification,
    DateParts,
    Education,
    Experience,
    Language,
    School,
    Skill,
)

MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ),
        start=1,
    )
}
ITEM_PREFIX = "entity-collection-item-"


def parse_rsc_section(section: str, documents: list[FlightDocument]) -> list[Any]:
    if section == "skills":
        return _parse_skills(documents)

    elements = _semantic_elements(documents)
    if section == "experience":
        return [_experience(element) for element in elements if _rendered_text(element)]
    if section == "education":
        return [_education(element) for element in elements if _rendered_text(element)]
    if section == "certifications":
        return [_certification(element) for element in elements if _rendered_text(element)]
    if section == "languages":
        return [_language(element) for element in elements if _rendered_text(element)]
    raise ValueError(f"Unsupported RSC parser section: {section}")


def _semantic_elements(documents: list[FlightDocument]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for document in documents:
        root = document.root()
        if isinstance(root, list) and len(root) > 2 and isinstance(root[2], list):
            for record in root[2]:
                if not isinstance(record, list) or len(record) != 2:
                    continue
                metadata = _metadata(record[0])
                semantic_id = metadata.get("semanticId")
                if _is_item_id(semantic_id) and semantic_id not in seen:
                    seen.add(semantic_id)
                    result.append(document.resolve(record[1]))
        for value in document.root_objects():
            semantic_id = value.get("semanticId")
            item = value.get("item")
            if _is_item_id(semantic_id) and item is not None and semantic_id not in seen:
                seen.add(semantic_id)
                result.append(document.resolve(item))
    return result


def _parse_skills(documents: list[FlightDocument]) -> list[Skill]:
    names: list[str] = []
    for element in _semantic_elements(documents):
        semantic_name = None
        for value in _walk(element):
            if not isinstance(value, dict):
                continue
            payload = value.get("payload")
            name = payload.get("skillName") if isinstance(payload, dict) else None
            if isinstance(name, str) and name.strip():
                semantic_name = name.strip()
                break
        rendered = _rendered_text(element)
        name = semantic_name or _at(rendered, 0)
        if name and name not in names:
            names.append(name)
    return [Skill(name=name) for name in names]


def _experience(element: Any) -> Experience:
    texts = _rendered_text(element)
    title = _at(texts, 0)
    company_line = _at(texts, 1)
    date_line = _at(texts, 2)
    company, employment_type = _split_company(company_line)
    start_date, end_date, current = _parse_range(date_line)
    return Experience(
        title=title,
        employment_type=employment_type,
        company={"name": company},
        start_date=start_date,
        end_date=end_date,
        is_current=current,
    )


def _education(element: Any) -> Education:
    texts = _rendered_text(element)
    start_date, end_date, _ = _parse_range(_at(texts, 2))
    return Education(
        school=School(name=_at(texts, 0)),
        degree=_at(texts, 1),
        start_date=start_date,
        end_date=end_date,
    )


def _certification(element: Any) -> Certification:
    texts = _rendered_text(element)
    issue_date, expiry_date = _parse_certification_dates(_at(texts, 2))
    credential = _at(texts, 3)
    if credential and ":" in credential:
        credential = credential.split(":", 1)[1].strip()
    return Certification(
        name=_at(texts, 0),
        issuing_organization=_at(texts, 1),
        issue_date=issue_date,
        expiry_date=expiry_date,
        credential_id=credential,
        credential_url=_first_external_url(element),
    )


def _language(element: Any) -> Language:
    texts = _rendered_text(element)
    return Language(name=_at(texts, 0) or "Unknown", proficiency=_at(texts, 1))


def _rendered_text(value: Any) -> list[str]:
    output: list[str] = []

    def collect(node: Any) -> None:
        if isinstance(node, str):
            text = node.strip()
            if text and not text.startswith("$") and text not in output:
                output.append(text)
            return
        if _is_element(node):
            props = node[3]
            if isinstance(props, dict):
                if isinstance(props.get("textProps"), dict):
                    collect(props["textProps"].get("children"))
                else:
                    for key in ("children", "initialContent"):
                        if key in props:
                            collect(props[key])
            return
        if isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, dict):
            if isinstance(node.get("textProps"), dict):
                collect(node["textProps"].get("children"))
            else:
                for key in ("children", "initialContent"):
                    if key in node:
                        collect(node[key])

    collect(value)
    return output


def _first_external_url(value: Any) -> str | None:
    for item in _walk(value):
        if not isinstance(item, dict):
            continue
        candidate = item.get("url")
        if isinstance(candidate, str) and candidate.startswith("http"):
            return candidate
        url_value = item.get("urlValue")
        if isinstance(url_value, dict):
            candidate = url_value.get("url")
            if isinstance(candidate, str) and candidate.startswith("http"):
                return candidate
    return None


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        result = json.loads(value)
    except ValueError:
        return {}
    return result if isinstance(result, dict) else {}


def _is_item_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(ITEM_PREFIX)


def _is_element(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and value[0] == "$"


def _at(values: list[str], index: int) -> str | None:
    return values[index] if index < len(values) else None


def _split_company(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = [part.strip() for part in value.split(" · ", 1)]
    return parts[0], parts[1] if len(parts) == 2 else None


def _parse_range(value: str | None) -> tuple[DateParts | None, DateParts | None, bool]:
    if not value:
        return None, None, False
    value = value.split(" · ", 1)[0].strip()
    parts = re.split(r"\s+[–-]\s+", value, maxsplit=1)
    start = _parse_display_date(parts[0])
    current = len(parts) == 2 and parts[1].strip().lower() == "present"
    end = None if current or len(parts) < 2 else _parse_display_date(parts[1])
    return start, end, current


def _parse_certification_dates(value: str | None) -> tuple[DateParts | None, DateParts | None]:
    if not value:
        return None, None
    issued = re.search(r"Issued\s+([A-Z][a-z]{2}\s+\d{4}|\d{4})", value)
    expires = re.search(r"Expires\s+([A-Z][a-z]{2}\s+\d{4}|\d{4})", value)
    return (
        _parse_display_date(issued.group(1)) if issued else None,
        _parse_display_date(expires.group(1)) if expires else None,
    )


def _parse_display_date(value: str) -> DateParts | None:
    match = re.fullmatch(r"(?:(?P<month>[A-Z][a-z]{2})\s+)?(?P<year>\d{4})", value.strip())
    if not match:
        return None
    return DateParts(
        year=int(match.group("year")),
        month=MONTHS.get(match.group("month")) if match.group("month") else None,
    )
