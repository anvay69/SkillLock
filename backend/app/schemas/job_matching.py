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
        hostname_labels = hostname.casefold().split(".") if hostname else []
        is_linkedin_host = (
            len(hostname_labels) >= 2
            and hostname_labels[-2:] == ["linkedin", "com"]
            and all(hostname_labels)
        )
        if (
            parsed.scheme.casefold() != "https"
            or not is_linkedin_host
            or parsed.username is not None
            or parsed.password is not None
            or port not in (None, 443)
        ):
            raise ValueError("Enter a valid HTTPS URL on linkedin.com.")
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
