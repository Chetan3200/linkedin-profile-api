import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.linkedin import endpoints
from app.linkedin.errors import (
    LinkedInAuthRequired,
    LinkedInCheckpointRequired,
    LinkedInRateLimited,
    LinkedInTemporarilyBlocked,
    LinkedInTimeout,
    LinkedInUpstreamError,
    ProfileUnavailable,
    UpstreamSchemaChanged,
)


class VoyagerClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def top_profile(self, public_identifier: str) -> dict[str, Any]:
        return await self._get_json(endpoints.top_profile(public_identifier))

    async def full_profile(self, profile_urn: str) -> dict[str, Any]:
        return await self._get_json(endpoints.full_profile(profile_urn))

    async def skills(self, public_identifier: str) -> dict[str, Any]:
        return await self._get_json(endpoints.skills(public_identifier))

    async def me(self) -> dict[str, Any]:
        return await self._get_json(endpoints.ME)

    async def _get_json(self, path: str) -> dict[str, Any]:
        for attempt in range(2):
            try:
                response = await self._client.get(path)
            except httpx.TimeoutException as exc:
                raise LinkedInTimeout() from exc
            except httpx.HTTPError as exc:
                raise LinkedInUpstreamError() from exc

            self._raise_for_upstream(response)
            if response.status_code == 429:
                delay = _retry_after_seconds(response.headers.get("retry-after"))
                if attempt == 0 and delay is not None and delay <= 10:
                    await asyncio.sleep(delay)
                    continue
                raise LinkedInRateLimited()
            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamSchemaChanged() from exc
            if not isinstance(payload, dict):
                raise UpstreamSchemaChanged()
            return payload
        raise LinkedInRateLimited()

    @staticmethod
    def _raise_for_upstream(response: httpx.Response) -> None:
        location = response.headers.get("location", "").lower()
        request_url = str(response.url).lower()
        if "/checkpoint/" in location or "/checkpoint/" in request_url:
            raise LinkedInCheckpointRequired()
        if response.status_code == 999:
            raise LinkedInTemporarilyBlocked()
        if response.status_code in (301, 302, 303, 307, 308):
            if location.rstrip("/") == request_url.rstrip("/") or response.headers.get(
                "clear-site-data"
            ):
                raise LinkedInTemporarilyBlocked()
            if "/login" in location or "/authwall" in location:
                raise LinkedInAuthRequired()
            raise LinkedInUpstreamError()
        if response.status_code in (401, 403):
            raise LinkedInAuthRequired()
        if response.status_code == 404:
            raise ProfileUnavailable()
        if response.status_code == 429:
            return
        if response.is_error:
            raise LinkedInUpstreamError()


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            now = datetime.now(UTC)
            delay = retry_at - now
            return max(0.0, delay.total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None
