from collections.abc import Callable
from typing import Any

from app.linkedin.images import first_resolved_image
from app.linkedin.parsers.common import (
    get_text,
    hydrate_entities,
    included_entities,
    parse_date,
    parse_period,
    section_elements,
    section_value,
)
from app.linkedin.parsers.education import parse_education
from app.linkedin.parsers.experience import parse_experience
from app.schemas.profile import (
    Certification,
    Course,
    Honor,
    Language,
    Project,
    Publication,
    Skill,
    VolunteerExperience,
)

SECTION_NAMES: dict[str, tuple[str, ...]] = {
    "experience": ("positionView", "experience", "positions", "profilePositionGroups"),
    "education": ("educationView", "education", "educations"),
    "skills": ("skillView", "skills", "skillComponents"),
    "certifications": ("certificationView", "certifications"),
    "languages": ("languageView", "languages"),
    "volunteering": ("volunteerExperienceView", "volunteering", "volunteerExperiences"),
    "projects": ("projectView", "projects"),
    "honors": ("honorView", "honors"),
    "publications": ("publicationView", "publications"),
    "courses": ("courseView", "courses"),
}

SECTION_ENTITY_TYPES: dict[str, tuple[str, ...]] = {
    "experience": ("Position", "PositionGroup"),
    "education": ("Education",),
    "skills": ("Skill",),
    "certifications": ("Certification",),
    "languages": ("Language",),
    "volunteering": ("VolunteerExperience",),
    "projects": ("Project",),
    "honors": ("Honor",),
    "publications": ("Publication",),
    "courses": ("Course",),
}


def find_section(payload: dict[str, Any], section: str) -> tuple[bool, Any]:
    found, value = section_value(payload, SECTION_NAMES[section])
    if found:
        return found, value

    entities = included_entities(payload)
    hydrated, _ = hydrate_entities(entities)
    matched = [
        entity
        for entity in hydrated
        if _entity_type(entity) in SECTION_ENTITY_TYPES[section]
    ]
    if section == "experience" and matched:
        return True, _deduplicate_grouped_positions(matched)
    return (bool(matched), matched)


def has_section(payload: dict[str, Any], section: str) -> bool:
    return find_section(payload, section)[0]


def parse_skills(value: Any) -> list[Skill]:
    result: list[Skill] = []
    for item in section_elements(value):
        name = get_text(item, "name", "skillName")
        if not name:
            continue
        count = item.get("endorsementCount")
        result.append(
            Skill(name=name, endorsement_count=count if isinstance(count, int) else None)
        )
    return result


def parse_certifications(value: Any) -> list[Certification]:
    result: list[Certification] = []
    for item in section_elements(value):
        period = item.get("timePeriod") or item.get("dateRange") or {}
        start_date, end_date = parse_period(period)
        if start_date is None:
            start_date = parse_date(item.get("issueDate"))
        if end_date is None:
            end_date = parse_date(item.get("expirationDate"))
        company = item.get("company")
        company = company if isinstance(company, dict) else {}
        result.append(
            Certification(
                name=get_text(item, "name"),
                issuing_organization=get_text(item, "authority", "issuingOrganization")
                or get_text(company, "name"),
                issue_date=start_date,
                expiry_date=end_date,
                credential_id=get_text(item, "licenseNumber", "credentialId"),
                credential_url=get_text(item, "url", "credentialUrl"),
                logo=first_resolved_image((company.get("logo"), item.get("logo"))),
            )
        )
    return result


def parse_languages(value: Any) -> list[Language]:
    result: list[Language] = []
    for item in section_elements(value):
        name = get_text(item, "name", "language")
        if name:
            result.append(Language(name=name, proficiency=get_text(item, "proficiency")))
    return result


def parse_volunteering(value: Any) -> list[VolunteerExperience]:
    result: list[VolunteerExperience] = []
    for item in section_elements(value):
        start_date, end_date = parse_period(item.get("timePeriod") or item.get("dateRange"))
        result.append(
            VolunteerExperience(
                role=get_text(item, "role", "title"),
                organization=get_text(item, "companyName", "organization"),
                cause=get_text(item, "cause"),
                description=get_text(item, "description"),
                start_date=start_date,
                end_date=end_date,
            )
        )
    return result


def parse_projects(value: Any) -> list[Project]:
    result: list[Project] = []
    for item in section_elements(value):
        start_date, end_date = parse_period(item.get("timePeriod") or item.get("dateRange"))
        result.append(
            Project(
                name=get_text(item, "title", "name"),
                description=get_text(item, "description"),
                url=get_text(item, "url"),
                start_date=start_date,
                end_date=end_date,
            )
        )
    return result


def parse_honors(value: Any) -> list[Honor]:
    return [
        Honor(
            title=get_text(item, "title"),
            issuer=get_text(item, "issuer"),
            description=get_text(item, "description"),
            issue_date=parse_date(item.get("issueDate")),
        )
        for item in section_elements(value)
    ]


def parse_publications(value: Any) -> list[Publication]:
    return [
        Publication(
            name=get_text(item, "name", "title"),
            publisher=get_text(item, "publisher"),
            description=get_text(item, "description"),
            url=get_text(item, "url"),
            published_date=parse_date(item.get("date") or item.get("publishedDate")),
        )
        for item in section_elements(value)
    ]


def parse_courses(value: Any) -> list[Course]:
    return [
        Course(name=get_text(item, "name"), number=get_text(item, "number"))
        for item in section_elements(value)
    ]


def _entity_type(entity: dict[str, Any]) -> str:
    value = entity.get("$type")
    return value.rsplit(".", 1)[-1] if isinstance(value, str) else ""


def _deduplicate_grouped_positions(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [entity for entity in entities if _entity_type(entity) == "PositionGroup"]
    if not groups:
        return entities
    grouped_urns = {
        role.get("entityUrn")
        for group in groups
        for role in _roles_from_group(group)
        if isinstance(role.get("entityUrn"), str)
    }
    ungrouped = [
        entity
        for entity in entities
        if _entity_type(entity) == "Position" and entity.get("entityUrn") not in grouped_urns
    ]
    return [*groups, *ungrouped]


def _roles_from_group(group: dict[str, Any]) -> list[dict[str, Any]]:
    value = group.get("profilePositionInPositionGroup") or group.get("positions")
    if isinstance(value, dict):
        value = value.get("elements")
    if isinstance(value, list):
        return [role for role in value if isinstance(role, dict)]
    return []


SectionParser = Callable[[Any], list[Any]]
SECTION_PARSERS: dict[str, SectionParser] = {
    "experience": parse_experience,
    "education": parse_education,
    "skills": parse_skills,
    "certifications": parse_certifications,
    "languages": parse_languages,
    "volunteering": parse_volunteering,
    "projects": parse_projects,
    "honors": parse_honors,
    "publications": parse_publications,
    "courses": parse_courses,
}
