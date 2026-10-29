import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class JobMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str | None = Field(default=None, max_length=20_000)
    linkedin_url: str | None = Field(default=None, max_length=2_048)

    @field_validator("job_description")
    @classmethod
    def clean_job_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned_value = value.strip()
        return cleaned_value or None

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned_value = value.strip()
        if not cleaned_value:
            return None
        if any(
            ord(character) < 33
            or ord(character) == 127
            or character == "\\"
            for character in cleaned_value
        ):
            raise ValueError("Enter a valid LinkedIn URL.")
        try:
            parsed = urlsplit(cleaned_value)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as error:
            raise ValueError("Enter a valid LinkedIn URL.") from error
        hostname = hostname.casefold() if hostname is not None else None
        is_linkedin_page = hostname in {"linkedin.com", "www.linkedin.com"} and (
            re.fullmatch(r"/jobs/view/[A-Za-z0-9%._~-]+/?", parsed.path)
            or re.fullmatch(r"/posts/[A-Za-z0-9%._~-]+/?", parsed.path)
        )
        is_short_post_link = hostname == "lnkd.in" and re.fullmatch(
            r"/p/[A-Za-z0-9_-]+/?", parsed.path
        )
        if (
            parsed.scheme.casefold() != "https"
            or hostname is None
            or hostname not in {"linkedin.com", "www.linkedin.com", "lnkd.in"}
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
            or not (is_linkedin_page or is_short_post_link)
        ):
            raise ValueError("Enter a public LinkedIn job or post URL, or an lnkd.in/p/... link.")
        return cleaned_value

    @model_validator(mode="after")
    def require_job_description_or_linkedin_url(self) -> "JobMatchRequest":
        if not self.job_description and not self.linkedin_url:
            raise ValueError("Provide a job description, a LinkedIn URL, or both.")
        return self


class LearningRoadmapItem(BaseModel):
    skill: str
    priority: Literal["required", "preferred"]
    status: Literal["not_started", "learning", "completed"]
    steps: list[str]
    practice_task: str
    project_idea: str


class JobMatchResponse(BaseModel):
    job_title: str = ""
    company: str = ""
    job_summary: str = ""
    source: Literal["pasted_description", "linkedin_listing", "linkedin_listing_and_description"] = (
        "pasted_description"
    )
    source_warning: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    readiness_feedback: str
    suggestions: list[str] = Field(default_factory=list)
    learning_roadmap: list[LearningRoadmapItem] = Field(default_factory=list)


class LearningProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1)
    status: Literal["not_started", "learning", "completed"]

    @field_validator("skill")
    @classmethod
    def skill_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Skill cannot be blank.")
        return cleaned_value


class LearningProgressResponse(BaseModel):
    learning_progress: dict[str, Literal["not_started", "learning", "completed"]]
