from pydantic import BaseModel, ConfigDict, Field


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""
    tech_stack: str = ""
    repository_url: str = ""
    live_url: str = ""


class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_title: str = ""
    company: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""


class Education(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    graduation_year: str = ""
    grade: str = ""


class Certification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    issuing_organization: str = ""
    credential_url: str = ""


class ProfileData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    username: str
    email: str
    bio: str = ""
    github_url: str = ""
    linkedin_url: str = ""
    profile_picture: str = ""
    resume: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


class ProfileResponse(ProfileData):
    id: int


class ExtractedProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


class ProfileUpdateResponse(BaseModel):
    profile: ProfileResponse
    extracted_added: ExtractedProfile
