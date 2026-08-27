from app.linkedin.parsers.profile import parse_profile
from app.linkedin.parsers.sections import find_section, parse_experience, parse_skills
from app.linkedin.urls import validate_profile_url


def test_parses_normalized_entities_and_hydrates_group_roles() -> None:
    profile_urn = "urn:li:fsd_profile:synthetic"
    role_urn = "urn:li:fsd_profilePosition:role1"
    payload = {
        "data": {"*identityDashProfilesByMemberIdentity": profile_urn},
        "included": [
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
                "entityUrn": profile_urn,
                "publicIdentifier": "normalized-person",
                "firstName": "Normalized",
                "lastName": "Person",
                "headline": "Engineer",
                "geoLocation": {
                    "geo": {"defaultLocalizedName": "Test City", "countryCode": "xy"}
                },
                "industry": {"name": "Technology"},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.PositionGroup",
                "entityUrn": "urn:li:fsd_profilePositionGroup:group1",
                "name": "Synthetic Co",
                "*profilePositionInPositionGroup": [role_urn],
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Position",
                "entityUrn": role_urn,
                "title": "Backend Engineer",
                "timePeriod": {"startDate": {"year": 2023}},
            },
            {
                "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
                "entityUrn": "urn:li:fsd_skill:skill1",
                "name": "Python",
            },
        ],
    }

    profile = parse_profile(
        payload, validate_profile_url("https://linkedin.com/in/normalized-person")
    )
    found_experience, experience_value = find_section(payload, "experience")
    found_skills, skills_value = find_section(payload, "skills")
    experience = parse_experience(experience_value)
    skills = parse_skills(skills_value)

    assert profile.full_name == "Normalized Person"
    assert profile.location.display_name == "Test City"
    assert profile.industry == "Technology"
    assert found_experience is True
    assert len(experience) == 1
    assert experience[0].title == "Backend Engineer"
    assert experience[0].company.name == "Synthetic Co"
    assert found_skills is True
    assert skills[0].name == "Python"
