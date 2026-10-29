from typing import Annotated

from fastapi import APIRouter, Cookie, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import SESSION_COOKIE
from app.features.resume.service import (
    RESUME_FILE_PREFIX,
    add_extracted_profile,
    legacy_resume_path,
    remove_resume,
    resume_path,
    store_resume,
)
from app.schemas.profile import ProfileData, ProfileUpdateResponse
from app.services.security import get_session_user
from app.services.users import profile_response, update_user_profile


router = APIRouter(prefix="/api")


@router.post("/me/resume", response_model=ProfileUpdateResponse)
async def upload_resume(
    resume: Annotated[UploadFile, File()],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> ProfileUpdateResponse:
    user = get_session_user(token)
    try:
        resume_url, extracted = await store_resume(resume, user.id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    previous_resume = user.profile.get("resume", "")
    current_profile = ProfileData.model_validate(
        {
            **user.profile,
            "name": user.name,
            "username": user.username,
            "email": user.email,
        }
    )
    current_profile.resume = resume_url
    updated_profile, extracted_added = add_extracted_profile(current_profile, extracted)
    user = update_user_profile(user.id, updated_profile)
    if previous_resume and previous_resume != resume_url:
        remove_resume(previous_resume, user.id)
    return ProfileUpdateResponse(
        profile=profile_response(user),
        extracted_added=extracted_added,
    )


@router.get("/me/resume/file/{filename}")
def download_resume(
    filename: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> FileResponse:
    user = get_session_user(token)
    resume_url = user.profile.get("resume", "")
    if resume_url == f"{RESUME_FILE_PREFIX}{filename}":
        path = resume_path(user.id, filename)
    elif resume_url == f"/uploads/{filename}":
        path = legacy_resume_path(resume_url)
    else:
        path = None

    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume not found.")
    media_type = (
        "application/pdf"
        if path.suffix.casefold() == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
