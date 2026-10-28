from typing import Annotated

from fastapi import APIRouter, Cookie, File, HTTPException, UploadFile

from app.core.config import SESSION_COOKIE
from app.features.resume.service import add_extracted_profile, store_resume
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
        resume_url, extracted = await store_resume(resume)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

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
    return ProfileUpdateResponse(
        profile=profile_response(user),
        extracted_added=extracted_added,
    )
