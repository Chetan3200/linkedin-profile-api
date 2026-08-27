from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.profile import Profile, ProfileResponse, ResponseMetadata


class FakeExtractor:
    async def resolve(self, target, request_id: str) -> ProfileResponse:  # type: ignore[no-untyped-def]
        return ProfileResponse(
            profile=Profile(
                profile_url=target.normalized_url,
                public_identifier=target.public_identifier,
                first_name="Example",
                full_name="Example Person",
            ),
            meta=ResponseMetadata(fetched_at=datetime.now(UTC), request_id=request_id),
        )


def test_service_health_and_docs() -> None:
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_invalid_profile_url_returns_typed_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/profiles/resolve",
            json={"profile_url": "https://linkedin.com/company/example"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PROFILE_URL"
    assert response.headers["cache-control"] == "no-store"


def test_endpoint_response_validates() -> None:
    with TestClient(app) as client:
        app.state.extractor = FakeExtractor()
        response = client.post(
            "/v1/profiles/resolve",
            json={"profile_url": "https://linkedin.com/in/example-person"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["public_identifier"] == "example-person"
    assert body["profile"]["experience"] == []
    assert body["meta"]["schema_version"] == "1.0"
    assert body["meta"]["request_id"] == response.headers["x-request-id"]


def test_missing_authentication_returns_typed_error() -> None:
    with TestClient(app) as client:
        app.state.extractor = None
        response = client.post(
            "/v1/profiles/resolve",
            json={"profile_url": "https://linkedin.com/in/example-person"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LINKEDIN_AUTH_REQUIRED"
