from pydantic import BaseModel, Field


class MatchedSkillInfo(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    match_percent: int = 0


class JobSummary(BaseModel):
    id: str
    title: str
    company: str
    location: str
    job_type: str = ""
    match: MatchedSkillInfo = Field(default_factory=MatchedSkillInfo)


class JobDetail(BaseModel):
    id: str
    title: str
    company: str
    location: str
    job_type: str = ""
    description: str = ""
    required_skills: list[str] = Field(default_factory=list)
    match: MatchedSkillInfo = Field(default_factory=MatchedSkillInfo)
    explanation: str = ""
    is_saved: bool = False


class SavedJobResponse(BaseModel):
    ok: bool
    job_id: str
    saved: bool

