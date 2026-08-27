import asyncio
from typing import Any

from app.linkedin.extractor import ExtractionGate, ProfileExtractor
from app.linkedin.urls import validate_profile_url


class FakeVoyager:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    async def top_profile(self, public_identifier: str) -> dict[str, Any]:
        return self.payload

    async def full_profile(self, profile_urn: str) -> dict[str, Any]:
        return self.payload


def test_complete_extraction_metadata(complete_payload: dict[str, Any]) -> None:
    extractor = ProfileExtractor(FakeVoyager(complete_payload), ExtractionGate(0))  # type: ignore[arg-type]

    result = asyncio.run(
        extractor.resolve(
            validate_profile_url("https://linkedin.com/in/example-person"),
            "request-1",
        )
    )

    assert result.meta.partial is False
    assert result.meta.sections["experience"].count == 2
    assert result.meta.sections["volunteering"].status == "empty_or_hidden"
    assert len(result.profile.skills) == 2


def test_failed_optional_section_marks_partial(complete_payload: dict[str, Any]) -> None:
    complete_payload["projectView"] = {"unexpected": "shape"}
    extractor = ProfileExtractor(FakeVoyager(complete_payload), ExtractionGate(0))  # type: ignore[arg-type]

    result = asyncio.run(
        extractor.resolve(
            validate_profile_url("https://linkedin.com/in/example-person"),
            "request-2",
        )
    )

    assert result.meta.partial is True
    assert result.meta.sections["projects"].status == "failed"
    assert "projects" in result.meta.missing_sections
    assert result.profile.projects == []
