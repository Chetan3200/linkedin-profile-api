# LinkedIn Profile API

An unofficial, low-volume hiring-challenge proof of concept that resolves a LinkedIn profile URL through an authenticated LinkedIn session and returns application-owned structured JSON. It has no frontend, database, background worker, browser runtime, or third-party scraping service.

> This project is not affiliated with or endorsed by LinkedIn. See [Legal and Responsible Use](#legal-and-responsible-use) before using it.

## Features

- Strict LinkedIn profile URL validation and SSRF prevention
- Direct authenticated Voyager and RSC Flight client built with `httpx.AsyncClient`
- Stable Pydantic v2 response models instead of raw upstream responses
- Name, headline, location, About, images, experience, education, skills, certifications, languages, and optional profile sections
- Grouped experience flattened into ordered individual roles
- Vector image resolution with the largest artifact selected
- Current SDUI/RSC detail routes with direct pagination action support
- Short-lived response cache to prevent duplicate Swagger requests
- Partial-result metadata for unavailable or failed sections
- Typed errors for authentication, checkpoints, rate limits, blocks, timeouts, and schema changes
- One upstream extraction at a time with a configurable minimum interval
- Process-local per-IP and global request ceilings
- Synthetic tests with an explicitly opt-in live test

## Architecture

```text
Client
  -> FastAPI route and URL validator
  -> process-local rate limit and extraction gate
  -> authenticated Voyager/RSC client
  -> public identifier to profile URN resolver
  -> literal Rest.li GraphQL identity/version request
  -> main profile and detail RSC Flight streams
  -> RSC pagination and normalized section parsers
  -> stable Pydantic response
```

The main components are:

- `app/main.py`: application lifecycle, health routes, request IDs, and error handling
- `app/api/profiles.py`: profile resolution route
- `app/linkedin/session.py`: cookies, CSRF, headers, and timeouts
- `app/linkedin/voyager_client.py`: upstream requests and status mapping
- `app/linkedin/extractor.py`: two-step request flow and partial-result metadata
- `app/linkedin/parsers/`: normalization for profiles and sections
- `app/middleware/rate_limit.py`: best-effort process-local request limiting
- `app/schemas/`: stable public API models

## Request Flow

1. Validate the submitted URL and extract only its public identifier.
2. Construct all upstream URLs from the fixed `https://www.linkedin.com` base.
3. Resolve the profile URN through `identity/dash/profiles`.
4. Call the current identity/version GraphQL query with literal Rest.li punctuation.
5. Fetch the main profile and required `/details/{section}/` RSC Flight streams.
6. Follow each stream's direct RSC pagination metadata with conservative pacing.
7. Decode Flight references and normalize components into stable models.
8. Return stable JSON with section status, warnings, and a request ID.

The user-provided URL is never fetched directly.

## Why Voyager

LinkedIn's official APIs do not generally expose arbitrary member profile data to ordinary applications. LinkedIn's web application uses internal Voyager REST and registered GraphQL endpoints for data the authenticated account may view. This project calls those internal structured endpoints directly rather than parsing visible profile HTML or wrapping an existing scraping library.

Voyager is undocumented and unsupported. Its decorations, GraphQL query IDs, and response schemas can change without notice.

## Local Setup

Requirements:

- `uv`
- Python 3.12, automatically provisioned by `uv` when needed
- A LinkedIn session you are authorized to use

```bash
uv sync
cp .env.example .env
uv run fastapi dev
```

The configured entrypoint is `app.main:app`, so no file path is needed. The API starts at `http://127.0.0.1:8000` and Swagger is at `http://127.0.0.1:8000/docs`.

## Environment Variables

Required for profile extraction:

```dotenv
LINKEDIN_LI_AT=
LINKEDIN_JSESSIONID=
```

Optional:

```dotenv
LINKEDIN_CSRF_TOKEN=
LINKEDIN_TIMEOUT_SECONDS=20
LINKEDIN_MIN_INTERVAL_SECONDS=2
LINKEDIN_SECTION_DELAY_SECONDS=1.5
PROFILE_CACHE_TTL_SECONDS=30
RATE_LIMIT_PER_IP=10
RATE_LIMIT_GLOBAL=60
RATE_LIMIT_WINDOW_SECONDS=60
```

`LINKEDIN_CSRF_TOKEN` defaults to the JSESSIONID value with surrounding quotes removed. The JSESSIONID cookie itself is preserved exactly in the cookie jar.

The application starts without credentials so `/`, `/healthz`, `/docs`, and `/openapi.json` remain available. `/readyz` returns `503`, and extraction returns `LINKEDIN_AUTH_REQUIRED`, until both required session variables are configured.

## Secret Handling

- Keep local credentials only in `.env`, which is ignored by Git and FastAPI Cloud uploads.
- Put placeholders only in `.env.example`.
- Configure cloud values as encrypted secrets in the FastAPI Cloud dashboard.
- Never commit cookies, browser storage, HAR files, copied browser requests, or raw LinkedIn responses.
- Cookies are never logged, returned, or included in exception messages.

## API

### Resolve Profile

`POST /v1/profiles/resolve`

```bash
curl --request POST 'http://127.0.0.1:8000/v1/profiles/resolve' \
  --header 'Content-Type: application/json' \
  --data '{"profile_url":"https://www.linkedin.com/in/example/"}'
```

Representative sanitized response:

```json
{
  "profile": {
    "profile_url": "https://www.linkedin.com/in/example/",
    "public_identifier": "example",
    "linkedin_urn": "urn:li:fsd_profile:synthetic",
    "first_name": "Example",
    "last_name": "Person",
    "full_name": "Example Person",
    "headline": "Backend Engineer",
    "location": {
      "display_name": "Example City",
      "country_code": "xy"
    },
    "about": "Builds reliable systems.",
    "industry": "Software Development",
    "images": {
      "profile": {
        "url": "https://media.example.invalid/profile.jpg",
        "width": 800,
        "height": 800
      },
      "background": null
    },
    "experience": [],
    "education": [],
    "skills": [],
    "certifications": [],
    "languages": [],
    "volunteering": [],
    "projects": [],
    "honors": [],
    "publications": [],
    "courses": []
  },
  "meta": {
    "schema_version": "1.0",
    "source": "linkedin_authenticated_voyager",
    "fetched_at": "2026-01-01T00:00:00Z",
    "partial": false,
    "sections": {},
    "missing_sections": [],
    "warnings": [],
    "request_id": "00000000-0000-0000-0000-000000000000"
  }
}
```

Every response includes `Cache-Control: no-store` and `X-Request-ID`.

### Service Routes

- `GET /`: service information and route links
- `GET /healthz`: process health without contacting LinkedIn
- `GET /readyz`: whether LinkedIn session variables are configured
- `GET /docs`: Swagger UI
- `GET /openapi.json`: OpenAPI schema

## Errors

Errors use a stable envelope with `code`, `message`, `request_id`, and `retryable`.

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_PROFILE_URL` | The input is not a supported LinkedIn member URL |
| 404 | `PROFILE_UNAVAILABLE` | The profile is missing or unavailable |
| 429 | `SERVICE_RATE_LIMITED` | A local request ceiling was reached |
| 429 | `LINKEDIN_RATE_LIMITED` | LinkedIn returned HTTP 429 |
| 502 | `UPSTREAM_SCHEMA_CHANGED` | A required upstream shape is unsupported |
| 502 | `LINKEDIN_UPSTREAM_ERROR` | LinkedIn returned another upstream failure |
| 503 | `LINKEDIN_AUTH_REQUIRED` | Session credentials are missing or expired |
| 503 | `LINKEDIN_CHECKPOINT_REQUIRED` | LinkedIn requires an interactive checkpoint |
| 503 | `LINKEDIN_TEMPORARILY_BLOCKED` | LinkedIn returned HTTP 999 or a clearing self-redirect |
| 504 | `LINKEDIN_TIMEOUT` | The upstream request timed out |

If the primary profile succeeds while a section fails, the API returns HTTP 200 with `meta.partial=true`, a failed section status, and a sanitized warning.

## Testing

```bash
uv run ruff check .
uv run pytest
```

Normal tests mock all LinkedIn calls and use synthetic fixtures. The live test is skipped unless credentials exist and explicit opt-in is enabled:

```bash
RUN_LIVE_LINKEDIN_TESTS=1 uv run pytest -m live tests/test_live.py
```

The live test does not print returned profile data and is not run by public CI.

## FastAPI Cloud Deployment

1. Push the project to a GitHub repository.
2. Run `uv run fastapi deploy` and complete browser login if prompted.
3. In FastAPI Cloud, open **Application > Environment Variables**.
4. Add `LINKEDIN_LI_AT`, `LINKEDIN_JSESSIONID`, and optionally `LINKEDIN_CSRF_TOKEN` as encrypted secrets.
5. Redeploy after changing session values.
6. Set maximum replicas to one if the Hobby configuration exposes that option.

Public deployment URL: https://linkedin-profile-api.fastapicloud.dev

Swagger documentation: https://linkedin-profile-api.fastapicloud.dev/docs

The service, health, readiness, docs, OpenAPI, validation, and live profile routes are verified publicly. The deployed hybrid Voyager/RSC flow returned profile identity, images, experience, education, skills, and certifications from FastAPI Cloud. Fields unavailable from the current RSC responses, including the state-bound About card, are reported honestly through `meta.partial`, section status, and warnings.

The process-local lock and rate limiter apply independently to each replica. A single replica is preferred for this low-traffic demonstration; no database or Redis is added solely for distributed limiting.

## Reverse Engineering

The implementation was verified against two live profiles while retaining only synthetic fixtures in Git. REST resolves the public identifier, a current registered GraphQL query provides identity/version metadata, and LinkedIn's SDUI/RSC Flight routes provide top-card and detail-section data. Pagination requests are reconstructed from metadata returned in each detail stream. Query IDs, RSC component IDs, pager IDs, and screen IDs are centralized in `app/linkedin/endpoints.py`.

See [`docs/reverse-engineering.md`](docs/reverse-engineering.md) for the update procedure and endpoint mapping.

## Security Decisions

- Strict host and path validation rejects lookalike domains and non-profile routes.
- Upstream requests always use a fixed LinkedIn base URL, preventing SSRF.
- One extraction runs at a time per process.
- A minimum interval is enforced between extraction starts.
- Request ceilings are best-effort and process-local.
- Profile data and images are not persisted, downloaded, cached, or rehosted.
- Logs contain request ID, a truncated identifier hash, latency, upstream status, and section counts only.
- Contact information is deliberately excluded.
- Upstream bodies and credentials never appear in public errors.

## Known Limitations

- Results depend on what the authenticated account is allowed to view.
- Private or hidden sections cannot be returned.
- LinkedIn sessions can expire or be invalidated.
- Voyager endpoints, decorations, GraphQL query IDs, and response schemas can change.
- RSC component, pager, and Flight response structures can change without notice.
- About is deferred through a state-bound component action and may be reported as partial.
- Cloud IP addresses may be blocked or challenged even when local requests work.
- LinkedIn CDN image URLs may expire.
- Direct Voyager requests generally do not open a profile page, but LinkedIn controls server-side profile-view tracking.
- In-memory locking and limiting are per process and per replica.
- Section completeness varies by profile visibility and LinkedIn experiments.

## Legal and Responsible Use

This is an unofficial, low-volume hiring-challenge proof of concept. It is not affiliated with or endorsed by LinkedIn.

Automated scraping may violate LinkedIn's terms. Users are responsible for using this project lawfully and complying with applicable terms, privacy requirements, access restrictions, and data-protection obligations. Do not use it for bulk collection, contact-data extraction, surveillance, spam, or access to information you are not authorized to view.
