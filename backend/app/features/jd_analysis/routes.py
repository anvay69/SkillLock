from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import SESSION_COOKIE
from app.features.job_matching.gemini import (
    GeminiConfigurationError,
    GeminiServiceError,
    JobDescriptionMismatchError,
    extract_job_requirements,
)
from app.features.job_matching.listing import LinkedInFetchError, fetch_linkedin_job
from app.schemas.jd_analysis import JDAnalysisRequest, JDAnalysisResponse
from app.services.security import get_session_user
from app.services.users import list_skills


router = APIRouter(prefix="/api")


@router.post("/jd-analysis/analyze", response_model=JDAnalysisResponse)
def analyze_job_description(
    request: JDAnalysisRequest,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> JDAnalysisResponse:
    get_session_user(token)
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

    try:
        extracted = extract_job_requirements(
            listing.get("page_text", ""),
            list_skills(),
            request.job_description or "",
        )
    except JobDescriptionMismatchError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except GeminiConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GeminiServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if request.job_description and listing and not source_warning:
        source = "linkedin_listing_and_description"
    elif listing:
        source = "linkedin_listing"
    else:
        source = "pasted_description"
    return JDAnalysisResponse(
        job_title=extracted.job_title or listing.get("job_title", ""),
        company=extracted.company or listing.get("company", ""),
        job_summary=extracted.job_summary,
        source=source,
        source_warning=source_warning,
        required_skills=extracted.required_skills,
        preferred_skills=extracted.preferred_skills,
        suggestions=extracted.suggestions,
    )
