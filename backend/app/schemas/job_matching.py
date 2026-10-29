from pydantic import BaseModel, Field


class JobMatchRequest(BaseModel):
    job_description: str = ""
    linkedin_url: str = ""


class JobMatchResponse(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    readiness_percent: int = 0
    feedback: str = ""
    suggestions: list[str] = Field(default_factory=list)

