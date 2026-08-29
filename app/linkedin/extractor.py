import asyncio
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from app.linkedin import endpoints
from app.linkedin.errors import LinkedInError
from app.linkedin.parsers import find_profile_urn, parse_profile
from app.linkedin.parsers.rsc_profile import merge_profiles, parse_rsc_profile
from app.linkedin.parsers.rsc_sections import parse_rsc_section
from app.linkedin.rsc import FlightDocument
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


REQUIRED_SECTIONS = ("experience", "education", "skills", "certifications", "languages")
OPTIONAL_SECTIONS = ("volunteering", "projects", "honors", "publications", "courses")


class ProfileExtractor:
    def __init__(
        self,
        voyager: VoyagerClient,
        gate: ExtractionGate,
        section_delay_seconds: float = 1.5,
        cache_ttl_seconds: float = 30.0,
    ) -> None:
        self._voyager = voyager
        self._gate = gate
        self._section_delay = section_delay_seconds
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, ProfileResponse]] = {}

    async def resolve(self, target: ProfileTarget, request_id: str) -> ProfileResponse:
        async with self._gate:
            cached = self._cache.get(target.public_identifier)
            if cached and monotonic() - cached[0] < self._cache_ttl:
                result = cached[1].model_copy(deep=True)
                result.meta.request_id = request_id
                return result

            top_payload = await self._voyager.top_profile(target.public_identifier)
            profile_urn = find_profile_urn(top_payload)
            if not profile_urn:
                profile = parse_profile(top_payload, target)
            else:
                member_identity = profile_urn.rsplit(":", 1)[-1]
                await asyncio.sleep(self._section_delay)
                graphql_payload = await self._voyager.top_card(member_identity)
                await asyncio.sleep(self._section_delay)
                main_document = FlightDocument.parse(
                    await self._voyager.profile_page(target.public_identifier)
                )
                rsc_profile = parse_rsc_profile(main_document, target, profile_urn)
                try:
                    structured = parse_profile(
                        _merge_payloads(top_payload, graphql_payload), target
                    )
                except LinkedInError:
                    profile = rsc_profile
                else:
                    profile = merge_profiles(structured, rsc_profile)

            sections: dict[str, SectionMetadata] = {}
            missing: list[str] = []
            warnings: list[str] = []
            for name in REQUIRED_SECTIONS:
                try:
                    await asyncio.sleep(self._section_delay)
                    documents = await self._section_documents(target.public_identifier, name)
                    parsed = parse_rsc_section(name, documents)
                except (KeyError, TypeError, ValueError, LinkedInError):
                    _mark_failed(name, sections, missing, warnings)
                    continue
                setattr(profile, name, parsed)
                sections[name] = SectionMetadata(
                    status="available" if parsed else "empty_or_hidden",
                    count=len(parsed),
                )

            for name in OPTIONAL_SECTIONS:
                sections[name] = SectionMetadata(status="empty_or_hidden", count=0)

            if not profile.about:
                _mark_failed("about", sections, missing, warnings)

            result = ProfileResponse(
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
            self._cache[target.public_identifier] = (monotonic(), result.model_copy(deep=True))
            return result

    async def _section_documents(
        self, public_identifier: str, section: str
    ) -> list[FlightDocument]:
        detail = FlightDocument.parse(
            await self._voyager.detail_section(public_identifier, section)
        )
        documents = [detail]
        pager_id = endpoints.RSC_PAGER_IDS.get(section)
        if not pager_id:
            return documents

        filter_name = "ProfileSkillCategory_ALL" if section == "skills" else None
        pagination = detail.pagination_request(pager_id, filter_name=filter_name)
        for _ in range(10):
            if pagination is None:
                break
            await asyncio.sleep(self._section_delay)
            page = FlightDocument.parse(await self._voyager.paginate_section(pagination, section))
            documents.append(page)
            pagination = page.pagination_request(pager_id)
        return documents


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
