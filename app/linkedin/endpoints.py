from urllib.parse import quote

BASE_URL = "https://www.linkedin.com"
TOP_CARD_DECORATION = "com.linkedin.voyager.dash.deco.identity.profile.TopCardSupplementary-166"
FULL_PROFILE_DECORATION = "com.linkedin.voyager.dash.deco.identity.profile.FullProfile-76"

# GraphQL query IDs rotate frequently. Add verified IDs here rather than scattering them
# through parsers. The current MVP uses the REST top-card and full-profile decorations.
GRAPHQL_QUERY_IDS: dict[str, str] = {}


def top_profile(public_identifier: str) -> str:
    identifier = quote(public_identifier, safe="")
    return (
        "/voyager/api/identity/dash/profiles"
        f"?q=memberIdentity&memberIdentity={identifier}&decorationId={TOP_CARD_DECORATION}"
    )


def full_profile(profile_urn: str) -> str:
    urn = quote(profile_urn, safe="")
    return (
        f"/voyager/api/identity/dash/profiles/{urn}"
        f"?decorationId={FULL_PROFILE_DECORATION}"
    )


def skills(public_identifier: str) -> str:
    identifier = quote(public_identifier, safe="")
    return f"/voyager/api/identity/profiles/{identifier}/skills?start=0&count=100"


ME = "/voyager/api/me"
