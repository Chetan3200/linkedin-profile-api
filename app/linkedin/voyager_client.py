import asyncio
from copy import deepcopy
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

    async def top_card(self, member_identity: str) -> dict[str, Any]:
        return await self._get_json(endpoints.top_card(member_identity))

    async def detail_section(self, public_identifier: str, section: str) -> bytes:
        return await self._get_flight(endpoints.detail_section(public_identifier, section))

    async def profile_page(self, public_identifier: str) -> bytes:
        return await self._get_flight(endpoints.profile_page(public_identifier))

    async def _get_flight(self, path: str) -> bytes:
        try:
            response = await self._client.get(
                path,
                headers={"accept": "*/*", "x-li-rsc-stream": "true"},
            )
        except httpx.TimeoutException as exc:
            raise LinkedInTimeout() from exc
        except httpx.HTTPError as exc:
            raise LinkedInUpstreamError() from exc

        self._raise_for_upstream(response)
        if not response.headers.get("content-type", "").startswith("application/octet-stream"):
            raise UpstreamSchemaChanged()
        return response.content

    async def paginate_section(self, pagination_request: dict[str, Any], section: str) -> bytes:
        client_arguments = deepcopy(pagination_request["requestedArguments"])
        client_arguments["states"] = []
        client_arguments["screenId"] = endpoints.RSC_SCREEN_IDS[section]
        payload = {
            "pagerId": pagination_request["pagerId"],
            "clientArguments": client_arguments,
            "paginationRequest": pagination_request,
        }
        try:
            response = await self._client.post(
                endpoints.RSC_PAGINATION_PATH,
                headers={
                    "accept": "*/*",
                    "content-type": "application/json",
                    "x-li-rsc-stream": "true",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LinkedInTimeout() from exc
        except httpx.HTTPError as exc:
            raise LinkedInUpstreamError() from exc

        self._raise_for_upstream(response)
        if not response.headers.get("content-type", "").startswith("application/octet-stream"):
            raise UpstreamSchemaChanged()
        return response.content

    async def load_component(self, component_request: dict[str, Any]) -> bytes:
        component_id = component_request["newComponentId"]
        requested_arguments = component_request["requestedArguments"]
        payload = {
            "clientArguments": {
                "payload": requested_arguments["payload"],
                "states": [],
                "requestMetadata": requested_arguments.get(
                    "requestMetadata", {"$type": "proto.sdui.common.RequestMetadata"}
                ),
                "screenId": "com.linkedin.sdui.flagshipnav.profile.Profile",
                "knownTemplateIds": [],
            }
        }
        try:
            response = await self._client.post(
                endpoints.RSC_COMPONENT_PATH,
                params={"componentId": component_id, "sduiid": component_id},
                headers={
                    "accept": "*/*",
                    "content-type": "application/json",
                    "x-li-rsc-stream": "true",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LinkedInTimeout() from exc
        except httpx.HTTPError as exc:
            raise LinkedInUpstreamError() from exc

        self._raise_for_upstream(response)
        if not response.headers.get("content-type", "").startswith("application/octet-stream"):
            raise UpstreamSchemaChanged()
        return response.content

    async def me(self) -> dict[str, Any]:
        return await self._get_json(endpoints.ME)

    async def _get_json(self, path: str) -> dict[str, Any]:
        for attempt in range(2):
            try:
                response = await self._client.get(
                    path,
                    headers={
                        "accept": "application/vnd.linkedin.normalized+json+2.1",
                        "accept-language": "en-US,en;q=0.9",
                        "x-li-lang": "en_US",
                        "x-restli-protocol-version": "2.0.0",
                    },
                )
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
