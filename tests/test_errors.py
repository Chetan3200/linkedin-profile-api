import asyncio

import httpx
import pytest

from app.linkedin.errors import (
    LinkedInAuthRequired,
    LinkedInCheckpointRequired,
    LinkedInRateLimited,
    LinkedInTemporarilyBlocked,
    UpstreamSchemaChanged,
)
from app.linkedin.voyager_client import VoyagerClient


def run_response(status: int, *, headers: dict[str, str] | None = None, json=None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if json is None:
            return httpx.Response(status, headers=headers, text="not-json")
        return httpx.Response(status, headers=headers, json=json)

    async def request() -> None:
        async with httpx.AsyncClient(
            base_url="https://www.linkedin.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            await VoyagerClient(client).top_profile("example")

    asyncio.run(request())


def test_authentication_expired_mapping() -> None:
    with pytest.raises(LinkedInAuthRequired):
        run_response(401)


def test_checkpoint_redirect_mapping() -> None:
    with pytest.raises(LinkedInCheckpointRequired):
        run_response(302, headers={"location": "/checkpoint/challenge/"})


def test_rate_limit_mapping() -> None:
    with pytest.raises(LinkedInRateLimited):
        run_response(429)


def test_http_999_mapping() -> None:
    with pytest.raises(LinkedInTemporarilyBlocked):
        run_response(999)


def test_unexpected_json_shape_mapping() -> None:
    with pytest.raises(UpstreamSchemaChanged):
        run_response(200, json=[])
