import asyncio
import os

import pytest

from app.config import Settings
from app.linkedin.parsers.common import walk_dicts
from app.linkedin.parsers.profile import parse_profile
from app.linkedin.rsc import FlightDocument
from app.linkedin.session import create_linkedin_client
from app.linkedin.urls import ProfileTarget
from app.linkedin.voyager_client import VoyagerClient


@pytest.mark.live
def test_authenticated_own_profile_request() -> None:
    settings = Settings()
    enabled = os.getenv("RUN_LIVE_LINKEDIN_TESTS") == "1"
    if not enabled or not settings.linkedin_configured:
        pytest.skip("live LinkedIn tests require explicit opt-in and session variables")

    async def run() -> None:
        async with create_linkedin_client(settings) as client:
            voyager = VoyagerClient(client)
            me = await voyager.me()
            identifier = next(
                (
                    item["publicIdentifier"]
                    for item in walk_dicts(me)
                    if isinstance(item.get("publicIdentifier"), str)
                ),
                None,
            )
            assert identifier
            payload = await voyager.top_profile(identifier)
            profile = parse_profile(
                payload,
                ProfileTarget(
                    public_identifier=identifier,
                    normalized_url=f"https://www.linkedin.com/in/{identifier}/",
                ),
            )
            assert profile.linkedin_urn
            assert profile.full_name
            member_identity = profile.linkedin_urn.rsplit(":", 1)[-1]
            top_card = await voyager.top_card(member_identity)
            assert isinstance(top_card, dict)
            experience = FlightDocument.parse(
                await voyager.detail_section(identifier, "experience")
            )
            assert experience.frames

    asyncio.run(run())
