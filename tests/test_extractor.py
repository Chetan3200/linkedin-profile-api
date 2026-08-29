import asyncio
from pathlib import Path
from typing import Any

from app.linkedin.errors import LinkedInUpstreamError
from app.linkedin.extractor import ExtractionGate, ProfileExtractor
from app.linkedin.urls import validate_profile_url

FIXTURES = Path(__file__).parent / "fixtures" / "rsc"


class FakeVoyager:
    def __init__(self, payload: dict[str, Any], failed_section: str | None = None) -> None:
        self.payload = payload
        self.failed_section = failed_section
        self.top_profile_calls = 0

    async def top_profile(self, public_identifier: str) -> dict[str, Any]:
        self.top_profile_calls += 1
        return self.payload

    async def top_card(self, member_identity: str) -> dict[str, Any]:
        return self.payload

    async def detail_section(self, public_identifier: str, section: str) -> bytes:
        if section == self.failed_section:
            raise LinkedInUpstreamError()
        return (FIXTURES / f"{section}.rsc").read_bytes()

    async def paginate_section(self, pagination_request, section: str) -> bytes:  # type: ignore[no-untyped-def]
        raise AssertionError("synthetic detail fixtures are not paginated")


def test_complete_extraction_metadata(complete_payload: dict[str, Any]) -> None:
    extractor = ProfileExtractor(
        FakeVoyager(complete_payload),  # type: ignore[arg-type]
        ExtractionGate(0),
        section_delay_seconds=0,
    )

    result = asyncio.run(
        extractor.resolve(
            validate_profile_url("https://linkedin.com/in/example-person"),
            "request-1",
        )
    )

    assert result.meta.partial is False
    assert result.meta.sections["experience"].count == 1
    assert result.meta.sections["volunteering"].status == "empty_or_hidden"
    assert len(result.profile.skills) == 1
    assert result.profile.experience[0].is_current is True


def test_failed_required_section_marks_partial(complete_payload: dict[str, Any]) -> None:
    extractor = ProfileExtractor(
        FakeVoyager(complete_payload, failed_section="skills"),  # type: ignore[arg-type]
        ExtractionGate(0),
        section_delay_seconds=0,
    )

    result = asyncio.run(
        extractor.resolve(
            validate_profile_url("https://linkedin.com/in/example-person"),
            "request-2",
        )
    )

    assert result.meta.partial is True
    assert result.meta.sections["skills"].status == "failed"
    assert "skills" in result.meta.missing_sections
    assert result.profile.skills == []


def test_cached_profile_avoids_duplicate_upstream_calls(complete_payload: dict[str, Any]) -> None:
    voyager = FakeVoyager(complete_payload)
    extractor = ProfileExtractor(  # type: ignore[arg-type]
        voyager,
        ExtractionGate(0),
        section_delay_seconds=0,
        cache_ttl_seconds=30,
    )
    target = validate_profile_url("https://linkedin.com/in/example-person")

    first = asyncio.run(extractor.resolve(target, "request-1"))
    second = asyncio.run(extractor.resolve(target, "request-2"))

    assert voyager.top_profile_calls == 1
    assert first.meta.request_id == "request-1"
    assert second.meta.request_id == "request-2"
