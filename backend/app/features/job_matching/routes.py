from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import SESSION_COOKIE
from app.features.job_matching.service import analyze_job_description, canonical_skill
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
    if not request.job_description:
        return JobMatchResponse(
            readiness_feedback=(
                "The LinkedIn URL was accepted, but this app does not fetch "
                "LinkedIn page content. Paste the job description to analyze it."
            ),
            suggestions=[
                "Paste the job description text from the LinkedIn listing to see skill matches."
            ],
        )

    candidate_skills = user.profile.get("skills", [])
    result = analyze_job_description(
        request.job_description,
        candidate_skills,
        list_skills(),
        user.profile.get("learning_progress", {}),
    )
    if request.linkedin_url:
        result["suggestions"].insert(
            0,
            "The LinkedIn page was not fetched; results use the job description text you pasted.",
        )
    return JobMatchResponse(**result)


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
