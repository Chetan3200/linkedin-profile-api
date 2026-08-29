from urllib.parse import quote

BASE_URL = "https://www.linkedin.com"
TOP_CARD_DECORATION = "com.linkedin.voyager.dash.deco.identity.profile.TopCardSupplementary-166"

# Query IDs and RSC component names are captured from the current web application.
GRAPHQL_QUERY_IDS = {
    "top_card": "voyagerIdentityDashProfiles.b5c27c04968c409fc0ed3546575b9b7a",
}
RSC_COMPONENT_IDS = {
    "experience": "com.linkedin.sdui.generated.profile.dsl.impl.profileCardsExperienceOnly",
    "below_activity_1": (
        "com.linkedin.sdui.generated.profile.dsl.impl.profileCardsBelowActivityPart1WithoutExp"
    ),
    **{
        f"below_activity_{index}": (
            "com.linkedin.sdui.generated.profile.dsl.impl."
            f"profileCardsBelowActivityPart{index}"
        )
        for index in range(2, 8)
    },
}
RSC_DETAIL_SECTIONS = {
    "experience",
    "education",
    "skills",
    "certifications",
    "languages",
}
RSC_COMPONENT_PATH = "/flagship-web/rsc-action/actions/component"
RSC_PAGINATION_PATH = "/flagship-web/rsc-action/actions/pagination"
RSC_PAGER_IDS = {
    section: f"com.linkedin.sdui.pagers.profile.details.{section}"
    for section in ("education", "skills", "certifications", "languages")
}
RSC_SCREEN_IDS = {
    "education": "com.linkedin.sdui.flagshipnav.profile.ProfileEducationDetails",
    "skills": "com.linkedin.sdui.flagshipnav.profile.ProfileSkillDetails",
    "certifications": "com.linkedin.sdui.flagshipnav.profile.ProfileCertificationDetails",
    "languages": "com.linkedin.sdui.flagshipnav.profile.ProfileLanguageDetails",
}


def top_profile(public_identifier: str) -> str:
    identifier = quote(public_identifier, safe="")
    return (
        "/voyager/api/identity/dash/profiles"
        f"?q=memberIdentity&memberIdentity={identifier}&decorationId={TOP_CARD_DECORATION}"
    )


def top_card(member_identity: str) -> str:
    identity = quote(member_identity, safe="_-")
    query_id = GRAPHQL_QUERY_IDS["top_card"]
    # Rest.li tuple punctuation must remain literal; using httpx params changes semantics.
    return (
        "/voyager/api/graphql?includeWebMetadata=true"
        f"&variables=(memberIdentity:{identity})&queryId={query_id}"
    )


def detail_section(public_identifier: str, section: str) -> str:
    if section not in RSC_DETAIL_SECTIONS:
        raise ValueError(f"Unsupported RSC detail section: {section}")
    identifier = quote(public_identifier, safe="")
    return f"/in/{identifier}/details/{section}/"


def profile_page(public_identifier: str) -> str:
    identifier = quote(public_identifier, safe="")
    return f"/in/{identifier}/"


ME = "/voyager/api/me"
