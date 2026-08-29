import asyncio
import json

import httpx

from app.linkedin.voyager_client import VoyagerClient


def test_about_component_uses_nested_client_arguments() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        arguments = payload["clientArguments"]
        assert sorted(arguments) == [
            "knownTemplateIds",
            "payload",
            "requestMetadata",
            "screenId",
            "states",
        ]
        return httpx.Response(
            200,
            headers={"content-type": "application/octet-stream"},
            content=b"0:null\n",
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            base_url="https://www.linkedin.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            content = await VoyagerClient(client).load_component(
                {
                    "newComponentId": "synthetic-component",
                    "requestedArguments": {
                        "payload": {"vanityName": "example"},
                        "requestMetadata": {
                            "$type": "proto.sdui.common.RequestMetadata"
                        },
                    },
                }
            )
            assert content == b"0:null\n"

    asyncio.run(run())
