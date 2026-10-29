from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import SESSION_COOKIE
from app.features.job_matching.gemini import (
    GeminiConfigurationError,
    JobDescriptionMismatchError,
    GeminiServiceError,
    extract_job_requirements,
)
from app.features.job_matching.listing import LinkedInFetchError, fetch_linkedin_job
from app.features.job_matching.service import (
    analyze_job_requirements,
    canonical_skill,
)
from app.schemas.job_matching import (
    JobMatchRequest,
    JobMatchResponse,
    LearningProgressResponse,
    LearningProgressUpdate,
)
from app.schemas.profile import ProfileData
from app.services.security import get_session_user
from app.services.users import list_skills, update_user_profile


router = APIRouter(prefix="/api")


@router.post("/job-matching/analyze", response_model=JobMatchResponse)
def analyze_job_match(
    request: JobMatchRequest,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> JobMatchResponse:
    user = get_session_user(token)
    listing = {}
    source_warning = ""
    if request.linkedin_url:
        try:
            listing = fetch_linkedin_job(request.linkedin_url)
        except LinkedInFetchError as error:
            if not request.job_description:
                raise HTTPException(status_code=422, detail=str(error)) from error
            source_warning = (
                f"The LinkedIn page could not be read: {error} "
                "This analysis uses the description you provided."
            )

    candidate_skills = user.profile.get("skills", [])
    known_skills = list_skills()
    job_summary = ""
    if listing or request.job_description:
        try:
            extracted = extract_job_requirements(
                listing.get("page_text", ""),
                list(dict.fromkeys([*known_skills, *candidate_skills])),
                request.job_description or "",
            )
        except JobDescriptionMismatchError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except GeminiConfigurationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except GeminiServiceError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        result = analyze_job_requirements(
            extracted.required_skills,
            extracted.preferred_skills,
            candidate_skills,
            known_skills,
            user.profile.get("learning_progress", {}),
        )
        job_title = extracted.job_title or listing.get("job_title", "")
        company = extracted.company or listing.get("company", "")
        job_summary = extracted.job_summary
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide a job description, a LinkedIn URL, or both.",
        )

    if request.job_description and listing and not source_warning:
        source = "linkedin_listing_and_description"
    elif listing:
        source = "linkedin_listing"
    else:
        source = "pasted_description"
    return JobMatchResponse(
        **result,
        job_title=job_title,
        company=company,
        job_summary=job_summary,
        source=source,
        source_warning=source_warning,
    )


@router.put(
    "/job-matching/learning-progress",
    response_model=LearningProgressResponse,
)
def update_learning_progress(
    request: LearningProgressUpdate,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> LearningProgressResponse:
    user = get_session_user(token)
    skill = canonical_skill(request.skill)
    allowed_skills = {
        canonical_skill(name)
        for name in [*list_skills(), *user.profile.get("skills", [])]
    }
    if skill not in allowed_skills:
        raise HTTPException(status_code=404, detail="Skill is not in this candidate's profile or skill catalog.")

    profile = ProfileData.model_validate(
        {
            **user.profile,
            "name": user.name,
            "username": user.username,
            "email": user.email,
        }
    )
    profile.learning_progress[skill] = request.status
    user = update_user_profile(user.id, profile)
    return LearningProgressResponse(learning_progress=user.profile["learning_progress"])
