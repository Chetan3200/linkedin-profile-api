from pathlib import Path

from app.linkedin.parsers.rsc_sections import parse_rsc_section
from app.linkedin.rsc import FlightDocument

FIXTURES = Path(__file__).parent / "fixtures" / "rsc"


def parse(section: str):  # type: ignore[no-untyped-def]
    document = FlightDocument.parse((FIXTURES / f"{section}.rsc").read_bytes())
    return parse_rsc_section(section, [document])


def test_parses_experience_flight() -> None:
    result = parse("experience")

    assert result[0].title == "Senior Engineer"
    assert result[0].company.name == "Example Systems"
    assert result[0].employment_type == "Full-time"
    assert result[0].start_date.year == 2024
    assert result[0].is_current is True


def test_parses_education_flight() -> None:
    result = parse("education")

    assert result[0].school.name == "Example University"
    assert result[0].degree == "Bachelor of Engineering"
    assert result[0].end_date.year == 2022


def test_parses_skill_flight() -> None:
    result = parse("skills")

    assert result[0].name == "Python"
    assert result[0].endorsement_count is None


def test_parses_certification_flight() -> None:
    result = parse("certifications")

    assert result[0].name == "Synthetic Certificate"
    assert result[0].issuing_organization == "Example Institute"
    assert result[0].issue_date.year == 2025
    assert result[0].credential_id == "SYNTHETIC-1"


def test_parses_language_flight() -> None:
    result = parse("languages")

    assert result[0].name == "Example Language"
    assert result[0].proficiency == "Professional proficiency"
