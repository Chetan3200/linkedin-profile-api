from typing import Any

from app.linkedin.parsers.education import parse_education
from app.linkedin.parsers.experience import parse_experience
from app.linkedin.parsers.sections import parse_skills


def test_flattens_grouped_experience_and_inherits_company(
    complete_payload: dict[str, Any],
) -> None:
    experience = parse_experience(complete_payload["positionView"])

    assert [role.title for role in experience] == [
        "Senior Backend Engineer",
        "Backend Engineer",
    ]
    assert all(role.company.name == "Example Systems" for role in experience)
    assert experience[0].is_current is True
    assert experience[0].end_date is None
    assert experience[1].start_date is not None
    assert experience[1].start_date.month is None


def test_parses_education_and_incomplete_dates(complete_payload: dict[str, Any]) -> None:
    education = parse_education(complete_payload["educationView"])

    assert education[0].school.name == "Example University"
    assert education[0].degree == "Bachelor of Engineering"
    assert education[0].start_date is not None
    assert education[0].start_date.month is None


def test_empty_section_returns_empty_list() -> None:
    assert parse_skills({"elements": []}) == []
