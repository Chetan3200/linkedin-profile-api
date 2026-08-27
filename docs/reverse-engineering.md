# Reverse-Engineering Notes

This document describes the sanitized process used to identify LinkedIn's current authenticated profile requests. It intentionally excludes cookies, personal data, HAR content, complete browser headers, and raw upstream responses.

## Identifying Requests

Start from an authenticated profile page and inspect Fetch/XHR traffic in browser developer tools. Filter requests using:

- `voyager/api`
- `graphql`
- `identity/dash/profiles`
- `profileComponents`

Interactions that commonly trigger structured requests are opening a member profile and selecting **Show all** for experience, education, skills, certifications, or languages. Record only endpoint patterns, parameter names, decoration names, GraphQL operation names, pagination behavior, and sanitized response types.

For this MVP, the live sequence was established without retaining browser captures:

1. A top-card request resolves a public identifier to a profile entity and profile URN.
2. A URN-based full-profile request returns normalized profile entities and sections.
3. The historic `identity/profiles/{identifier}/profileView` endpoint returned HTTP 410 and is not used.

## Minimum Headers

Verified request names are:

- `accept: application/vnd.linkedin.normalized+json+2.1`
- `accept-language`
- `csrf-token`
- `user-agent`
- `x-li-lang: en_US`
- `x-restli-protocol-version: 2.0.0`

The authenticated cookie jar contains `li_at` and `JSESSIONID`. Browser telemetry and unrelated application cookies are not stored or replayed by the application.

The JSESSIONID cookie commonly includes surrounding quotes. Preserve the cookie value in the jar, but remove surrounding quotes when deriving `csrf-token`. An explicit `LINKEDIN_CSRF_TOKEN` can override derivation when required.

## Candidate Endpoint Patterns

Current REST patterns:

```text
GET /voyager/api/me
GET /voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={identifier}&decorationId={top-card-decoration}
GET /voyager/api/identity/dash/profiles/{encoded-profile-urn}?decorationId={full-profile-decoration}
```

Fallback GraphQL pattern:

```text
GET /voyager/api/graphql?variables=(profileUrn:...,sectionType:...)&queryId={registered-query-id}
```

GraphQL variables use Rest.li tuple syntax rather than JSON. Query IDs must be verified against current LinkedIn web bundles or browser network traffic before use.

## Public Schema Mapping

LinkedIn normalized responses commonly contain a primary object plus `included` entities. References beginning with `*` are hydrated from entity URNs before parsing.

| Upstream concept | Public schema |
| --- | --- |
| Profile entity | names, headline, About, industry, location, URN |
| VectorImage | profile/background `Image` |
| Position and PositionGroup | flattened `Experience` entries |
| Education and school references | `Education` and `School` |
| Skill | `Skill` |
| Certification | `Certification` |
| Language | `Language` |
| Other supported profile entities | volunteering, projects, honors, publications, courses |

Structured date objects are mapped to nullable year, month, and day fields. Display strings are not parsed when structured dates are available.

## Query ID Rotation

GraphQL query hashes rotate with LinkedIn deployments. Stable operation names and currently verified IDs belong in `app/linkedin/endpoints.py`, never in section parsers.

To update the registry:

1. Reproduce the relevant profile-page interaction.
2. Find the successful GraphQL request in Fetch/XHR traffic.
3. Record the operation name, full query ID, variables, and pagination behavior.
4. Update the central registry.
5. Add a synthetic fixture for the response shape.
6. Run parser and API tests before enabling the ID.

Do not guess query IDs or commit captured network files.

## Failure Classification

- HTTP 401/403 or login/authwall redirect: authentication required
- Checkpoint redirect: interactive checkpoint required
- HTTP 404 or unavailable-profile result: profile unavailable
- HTTP 429: one conservative retry only when `Retry-After` is short
- HTTP 999 or a self-redirect with site-data clearing: temporarily blocked
- HTTP 410 on a historical endpoint: endpoint removed; use the current registry
- Missing required response shape: upstream schema changed
- Individual section parser failure: partial HTTP 200 with a sanitized warning

## Sensitive Files

Never commit:

- `.env` or secret variants
- Cookie exports
- Browser storage state
- HAR files
- Complete copied browser requests
- Screenshots containing personal information
- Raw profile responses
- Logs containing credentials or profile content

Only synthetic or thoroughly sanitized fixtures belong in `tests/fixtures/`.
