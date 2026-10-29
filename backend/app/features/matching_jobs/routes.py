from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import SESSION_COOKIE
from app.features.matching_jobs import service
from app.schemas.matching_jobs import JobDetail, JobSummary, SavedJobResponse
from app.services.security import get_session_user


router = APIRouter(prefix="/api")


@router.get("/matched-jobs", response_model=list[JobSummary])
def matched_jobs(
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> list[JobSummary]:
    user = get_session_user(token)
    return service.list_matched_jobs(user)


@router.get("/matched-jobs/{job_id}", response_model=JobDetail)
def matched_job_detail(
    job_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> JobDetail:
    user = get_session_user(token)
    result = service.get_matched_job(user, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result


@router.get("/me/saved-jobs", response_model=list[JobSummary])
def saved_jobs(
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> list[JobSummary]:
    user = get_session_user(token)
    return service.list_saved_jobs(user)


@router.put("/matched-jobs/{job_id}/save", response_model=SavedJobResponse)
def save_job(
    job_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> SavedJobResponse:
    user = get_session_user(token)
    result = service.save_job(user, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result


@router.delete("/matched-jobs/{job_id}/save", response_model=SavedJobResponse)
def unsave_job(
    job_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> SavedJobResponse:
    user = get_session_user(token)
    return service.unsave_job(user, job_id)

