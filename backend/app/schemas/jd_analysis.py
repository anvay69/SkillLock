from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.job_matching import JobMatchRequest


class JDAnalysisResponse(BaseModel):
    job_title: str = ""
    company: str = ""
    job_summary: str = ""
    source: Literal[
        "pasted_description",
        "linkedin_listing",
        "linkedin_listing_and_description",
    ]
    source_warning: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


JDAnalysisRequest = JobMatchRequest
