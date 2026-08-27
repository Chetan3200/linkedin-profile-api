from typing import Any

from app.linkedin.images import first_resolved_image
from app.linkedin.parsers.common import get_text, parse_period, section_elements
from app.schemas.profile import Company, Experience


def parse_experience(value: Any) -> list[Experience]:
    result: list[Experience] = []
    for item in section_elements(value):
        roles = _grouped_roles(item)
        if roles is not None:
            shared = _company_from(item)
            for role in roles:
                result.append(_parse_role(role, shared))
        else:
            result.append(_parse_role(item))
    return result


def _grouped_roles(item: dict[str, Any]) -> list[dict[str, Any]] | None:
    for key in (
        "profilePositionInPositionGroup",
        "positions",
        "roles",
        "positionGroup",
    ):
        value = item.get(key)
        if isinstance(value, dict):
            try:
                return section_elements(value)
            except ValueError:
                continue
        if isinstance(value, list) and all(isinstance(role, dict) for role in value):
            return value
    return None


def _parse_role(item: dict[str, Any], inherited: Company | None = None) -> Experience:
    start_date, end_date = parse_period(item.get("timePeriod") or item.get("dateRange"))
    company = _company_from(item)
    if inherited:
        company = Company(
            name=company.name or inherited.name,
            linkedin_urn=company.linkedin_urn or inherited.linkedin_urn,
            linkedin_url=company.linkedin_url or inherited.linkedin_url,
            logo=company.logo or inherited.logo,
        )
    current = bool(item.get("isCurrent")) or (start_date is not None and end_date is None)
    return Experience(
        title=get_text(item, "title", "role"),
        employment_type=get_text(item, "employmentType", "employmentTypeName"),
        company=company,
        location=get_text(item, "locationName", "location"),
        description=get_text(item, "description"),
        start_date=start_date,
        end_date=None if current else end_date,
        is_current=current,
    )


def _company_from(item: dict[str, Any]) -> Company:
    company_value = item.get("company")
    company = company_value if isinstance(company_value, dict) else {}
    mini = company.get("miniCompany")
    if isinstance(mini, dict):
        company = mini
    urn = get_text(company, "entityUrn", "companyUrn") or get_text(item, "companyUrn")
    return Company(
        name=get_text(company, "name") or get_text(item, "companyName", "name"),
        linkedin_urn=urn,
        linkedin_url=get_text(company, "url", "companyUrl"),
        logo=first_resolved_image((company.get("logo"), item.get("companyLogo"))),
    )
