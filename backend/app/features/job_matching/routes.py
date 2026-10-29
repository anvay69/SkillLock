from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import SESSION_COOKIE
from app.features.job_matching.service import analyze_job_match
from app.schemas.job_matching import JobMatchRequest, JobMatchResponse
from app.services.security import get_session_user


router = APIRouter(prefix="/api")


@router.post("/job-matching/analyze", response_model=JobMatchResponse)
def analyze(
    body: JobMatchRequest,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> JobMatchResponse:
    user = get_session_user(token)

    jd_text = body.job_description.strip()
    linkedin_url = body.linkedin_url.strip()

    if not jd_text and not linkedin_url:
        raise HTTPException(
            status_code=400,
            detail="Please provide a job description or a LinkedIn listing URL.",
        )

    # If only a LinkedIn URL is provided without JD text, inform the user
    if not jd_text and linkedin_url:
        raise HTTPException(
            status_code=400,
            detail="Please paste the job description text along with the URL. "
            "Automated LinkedIn content fetching is not supported.",
        )

    return analyze_job_match(user, jd_text)

