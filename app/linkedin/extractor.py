import asyncio
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from app.linkedin.errors import LinkedInError
from app.linkedin.parsers import SECTION_PARSERS, parse_profile
from app.linkedin.parsers.sections import find_section
from app.linkedin.urls import ProfileTarget
from app.linkedin.voyager_client import VoyagerClient
from app.schemas.profile import ProfileResponse, ResponseMetadata, SectionMetadata


class ExtractionGate:
    def __init__(self, minimum_interval_seconds: float) -> None:
        self._lock = asyncio.Lock()
        self._minimum_interval = minimum_interval_seconds
        self._last_started = 0.0

    async def __aenter__(self) -> None:
        await self._lock.acquire()
        delay = self._minimum_interval - (monotonic() - self._last_started)
        if delay > 0:
            await asyncio.sleep(delay)
        self._last_started = monotonic()

    async def __aexit__(self, *_: object) -> None:
        self._lock.release()


class ProfileExtractor:
    def __init__(self, voyager: VoyagerClient, gate: ExtractionGate) -> None:
        self._voyager = voyager
        self._gate = gate

    async def resolve(self, target: ProfileTarget, request_id: str) -> ProfileResponse:
        async with self._gate:
            top_payload = await self._voyager.top_profile(target.public_identifier)
            profile = parse_profile(top_payload, target)
            payload = top_payload
            full_profile_failed = False
            if profile.linkedin_urn:
                try:
                    full_payload = await self._voyager.full_profile(profile.linkedin_urn)
                    payload = _merge_payloads(top_payload, full_payload)
                    profile = parse_profile(payload, target)
                except LinkedInError:
                    full_profile_failed = True
            else:
                full_profile_failed = True

            sections: dict[str, SectionMetadata] = {}
            missing: list[str] = []
            warnings: list[str] = []
            for name, parser in SECTION_PARSERS.items():
                found, value = find_section(payload, name)
                if not found:
                    if full_profile_failed:
                        _mark_failed(name, sections, missing, warnings)
                        continue
                    sections[name] = SectionMetadata(status="empty_or_hidden", count=0)
                    continue
                try:
                    parsed = parser(value)
                except (KeyError, TypeError, ValueError):
                    _mark_failed(name, sections, missing, warnings)
                    continue
                setattr(profile, name, parsed)
                sections[name] = SectionMetadata(
                    status="available" if parsed else "empty_or_hidden",
                    count=len(parsed),
                )

            return ProfileResponse(
                profile=profile,
                meta=ResponseMetadata(
                    fetched_at=datetime.now(UTC),
                    partial=bool(missing),
                    sections=sections,
                    missing_sections=missing,
                    warnings=warnings,
                    request_id=request_id,
                ),
            )


def _merge_payloads(primary: dict[str, Any], full: dict[str, Any]) -> dict[str, Any]:
    included: list[Any] = []
    for payload in (primary, full):
        value = payload.get("included")
        if isinstance(value, list):
            included.extend(value)
    merged = {**primary, **full}
    if included:
        merged["included"] = included
    return merged


def _mark_failed(
    name: str,
    sections: dict[str, SectionMetadata],
    missing: list[str],
    warnings: list[str],
) -> None:
    sections[name] = SectionMetadata(status="failed", count=0)
    missing.append(name)
    warnings.append(f"The {name} section could not be extracted.")
