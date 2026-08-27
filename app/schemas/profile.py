from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProfileResolveRequest(BaseModel):
    profile_url: str = Field(min_length=1, max_length=500)


class Image(BaseModel):
    url: str
    width: int | None = None
    height: int | None = None


class ProfileImages(BaseModel):
    profile: Image | None = None
    background: Image | None = None


class Location(BaseModel):
    display_name: str | None = None
    country_code: str | None = None


class DateParts(BaseModel):
    year: int | None = None
    month: int | None = None
    day: int | None = None


class Company(BaseModel):
    name: str | None = None
    linkedin_urn: str | None = None
    linkedin_url: str | None = None
    logo: Image | None = None


class Experience(BaseModel):
    title: str | None = None
    employment_type: str | None = None
    company: Company = Field(default_factory=Company)
    location: str | None = None
    description: str | None = None
    start_date: DateParts | None = None
    end_date: DateParts | None = None
    is_current: bool = False


class School(BaseModel):
    name: str | None = None
    linkedin_urn: str | None = None
    linkedin_url: str | None = None
    logo: Image | None = None


class Education(BaseModel):
    school: School = Field(default_factory=School)
    degree: str | None = None
    field_of_study: str | None = None
    description: str | None = None
    activities: str | None = None
    start_date: DateParts | None = None
    end_date: DateParts | None = None


class Skill(BaseModel):
    name: str
    endorsement_count: int | None = None


class Certification(BaseModel):
    name: str | None = None
    issuing_organization: str | None = None
    issue_date: DateParts | None = None
    expiry_date: DateParts | None = None
    credential_id: str | None = None
    credential_url: str | None = None
    logo: Image | None = None


class Language(BaseModel):
    name: str
    proficiency: str | None = None


class VolunteerExperience(BaseModel):
    role: str | None = None
    organization: str | None = None
    cause: str | None = None
    description: str | None = None
    start_date: DateParts | None = None
    end_date: DateParts | None = None


class Project(BaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    start_date: DateParts | None = None
    end_date: DateParts | None = None


class Honor(BaseModel):
    title: str | None = None
    issuer: str | None = None
    description: str | None = None
    issue_date: DateParts | None = None


class Publication(BaseModel):
    name: str | None = None
    publisher: str | None = None
    description: str | None = None
    url: str | None = None
    published_date: DateParts | None = None


class Course(BaseModel):
    name: str | None = None
    number: str | None = None


class Profile(BaseModel):
    profile_url: str
    public_identifier: str
    linkedin_urn: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    headline: str | None = None
    location: Location = Field(default_factory=Location)
    about: str | None = None
    industry: str | None = None
    images: ProfileImages = Field(default_factory=ProfileImages)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    volunteering: list[VolunteerExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    honors: list[Honor] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    courses: list[Course] = Field(default_factory=list)


class SectionMetadata(BaseModel):
    status: Literal["available", "empty_or_hidden", "failed"]
    count: int = 0


class ResponseMetadata(BaseModel):
    schema_version: str = "1.0"
    source: str = "linkedin_authenticated_voyager"
    fetched_at: datetime
    partial: bool = False
    sections: dict[str, SectionMetadata] = Field(default_factory=dict)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    request_id: str


class ProfileResponse(BaseModel):
    profile: Profile
    meta: ResponseMetadata
