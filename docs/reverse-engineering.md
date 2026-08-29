# Reverse-Engineering Notes

This document describes the sanitized process used to identify LinkedIn's current authenticated profile requests. It intentionally excludes cookies, personal data, HAR content, complete browser headers, and raw upstream responses.

## Identifying Requests

Start from an authenticated profile page and inspect Fetch/XHR traffic in browser developer tools. Filter requests using:

- `voyager/api`
- `graphql`
- `identity/dash/profiles`
- `rsc-action`

Interactions that commonly trigger structured requests are opening a member profile and selecting **Show all** for experience, education, skills, certifications, or languages. Record only endpoint patterns, parameter names, decoration names, GraphQL operation names, pagination behavior, and sanitized response types.

For this MVP, the live sequence was established without committing browser captures:

1. Voyager REST resolves a public identifier to a profile entity and URN.
2. Registered GraphQL returns current identity/version metadata.
3. The main profile and `/details/{section}/` routes return RSC Flight streams.
4. `POST /flagship-web/rsc-action/actions/pagination` returns section records.
5. Historical `profileView` and `FullProfile` flows are not used.

## Minimum Headers

Verified request names are:

- `accept: application/vnd.linkedin.normalized+json+2.1`
- `accept-language`
- `csrf-token`
- `user-agent`
- `x-li-lang: en_US`
- `x-restli-protocol-version: 2.0.0`
- `x-li-rsc-stream: true` for Flight responses

The authenticated cookie jar contains `li_at` and `JSESSIONID`. Browser telemetry and unrelated application cookies are not stored or replayed by the application.

The JSESSIONID cookie commonly includes surrounding quotes. Preserve the cookie value in the jar, but remove surrounding quotes when deriving `csrf-token`. An explicit `LINKEDIN_CSRF_TOKEN` can override derivation when required.

## Candidate Endpoint Patterns

Current request patterns:

```text
GET /voyager/api/me
GET /voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={identifier}&decorationId={top-card-decoration}
GET /voyager/api/graphql?includeWebMetadata=true&variables=(memberIdentity:{id})&queryId={registered-query-id}
GET /in/{identifier}/
GET /in/{identifier}/details/{section}/
POST /flagship-web/rsc-action/actions/component
POST /flagship-web/rsc-action/actions/pagination
```

GraphQL variables use Rest.li tuple syntax rather than JSON. Parentheses and colons must remain literal; standard query-parameter encoding returns HTTP 400. Query IDs must be verified against current network traffic.

Flight responses contain hexadecimal chunk labels, JSON model chunks, `I` import chunks, and cross-chunk references such as `$L`, `$Q`, and path references. The parser resolves references before locating semantic collection items. Only synthetic Flight fixtures are committed.

## Public Schema Mapping

LinkedIn normalized responses commonly contain a primary object plus `included` entities. References beginning with `*` are hydrated from entity URNs before parsing.

| Upstream concept | Public schema |
| --- | --- |
| Voyager profile entity | profile URN and structured fields when present |
| RSC top-card and above-activity components | identity, About, location, images |
| Experience detail records | `Experience` |
| Education pager records | `Education` and `School` |
| Skills pager action/text | `Skill` |
| Certification pager records | `Certification` |
| Language pager records | `Language` |

Structured date objects are mapped to nullable year, month, and day fields. Display strings are not parsed when structured dates are available.

## Query ID Rotation

GraphQL hashes and RSC component/pager names can rotate with LinkedIn deployments. All verified identifiers belong in `app/linkedin/endpoints.py`, never in parsers.

To update the registry:

1. Reproduce the relevant profile-page interaction.
2. Find the successful GraphQL or RSC request in Network traffic.
3. Record only operation/component names, variable keys, and pagination behavior.
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
