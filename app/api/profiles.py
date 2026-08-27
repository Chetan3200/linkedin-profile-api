import hashlib
import logging
from time import monotonic

from fastapi import APIRouter, Request

from app.linkedin.errors import LinkedInAuthRequired
from app.linkedin.urls import validate_profile_url
from app.schemas.errors import ErrorResponse
from app.schemas.profile import ProfileResolveRequest, ProfileResponse

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
logger = logging.getLogger(__name__)


@router.post(
    "/resolve",
    response_model=ProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def resolve_profile(body: ProfileResolveRequest, request: Request) -> ProfileResponse:
    target = validate_profile_url(body.profile_url)
    extractor = request.app.state.extractor
    if extractor is None:
        raise LinkedInAuthRequired()

    started = monotonic()
    result = await extractor.resolve(target, request.state.request_id)
    counts = {name: metadata.count for name, metadata in result.meta.sections.items()}
    identifier_hash = hashlib.sha256(target.public_identifier.encode()).hexdigest()[:12]
    logger.info(
        "request_id=%s identifier_hash=%s latency_ms=%d upstream_status=200 section_counts=%s",
        request.state.request_id,
        identifier_hash,
        int((monotonic() - started) * 1000),
        counts,
    )
    return result
