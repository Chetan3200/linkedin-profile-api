import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.profiles import router as profiles_router
from app.config import get_settings
from app.linkedin.errors import LinkedInError
from app.linkedin.extractor import ExtractionGate, ProfileExtractor
from app.linkedin.session import create_linkedin_client
from app.linkedin.voyager_client import VoyagerClient
from app.middleware.rate_limit import RateLimitMiddleware
from app.schemas.errors import APIError, ErrorResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.extractor = None
    client = None
    if settings.linkedin_configured:
        client = create_linkedin_client(settings)
        application.state.extractor = ProfileExtractor(
            VoyagerClient(client),
            ExtractionGate(settings.linkedin_min_interval_seconds),
        )
    yield
    if client:
        await client.aclose()


app = FastAPI(
    title="LinkedIn Profile API",
    version="1.0.0",
    description="Unofficial low-volume authenticated LinkedIn profile extraction proof of concept.",
    lifespan=lifespan,
)
app.add_middleware(
    RateLimitMiddleware,
    per_ip=settings.rate_limit_per_ip,
    global_limit=settings.rate_limit_global,
    window_seconds=settings.rate_limit_window_seconds,
)
app.include_router(profiles_router)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(LinkedInError)
async def linkedin_error_handler(request: Request, exc: LinkedInError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body = ErrorResponse(
        error=APIError(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            retryable=exc.retryable,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.get("/", tags=["service"])
async def service_info() -> dict[str, str]:
    return {
        "name": "LinkedIn Profile API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz",
        "readiness": "/readyz",
    }


@app.get("/healthz", tags=["service"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["service"])
async def readiness() -> JSONResponse:
    configured = settings.linkedin_configured
    return JSONResponse(
        status_code=200 if configured else 503,
        content={
            "status": "ready" if configured else "not_ready",
            "linkedin_auth_configured": configured,
        },
    )
