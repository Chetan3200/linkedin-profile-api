from typing import Any

from app.linkedin.images import first_resolved_image
from app.linkedin.parsers.common import get_text, parse_period, section_elements
from app.schemas.profile import Education, School


def parse_education(value: Any) -> list[Education]:
    result: list[Education] = []
    for item in section_elements(value):
        school_value = item.get("school")
        school = school_value if isinstance(school_value, dict) else {}
        mini = school.get("miniSchool")
        if isinstance(mini, dict):
            school = mini
        start_date, end_date = parse_period(item.get("timePeriod") or item.get("dateRange"))
        result.append(
            Education(
                school=School(
                    name=get_text(school, "name") or get_text(item, "schoolName"),
                    linkedin_urn=get_text(school, "entityUrn", "schoolUrn")
                    or get_text(item, "schoolUrn"),
                    linkedin_url=get_text(school, "url", "schoolUrl"),
                    logo=first_resolved_image((school.get("logo"), item.get("schoolLogo"))),
                ),
                degree=get_text(item, "degreeName", "degree"),
                field_of_study=get_text(item, "fieldOfStudy", "fieldOfStudyName"),
                description=get_text(item, "description", "notes"),
                activities=get_text(item, "activities"),
                start_date=start_date,
                end_date=end_date,
            )
        )
    return result
