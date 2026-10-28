from typing import Annotated

from fastapi import APIRouter, Cookie, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError

from app.core.config import SESSION_COOKIE
from app.features.resume.service import add_extracted_profile, store_resume
from app.schemas.auth import LoginRequest
from app.schemas.profile import ProfileData, ProfileResponse, ProfileUpdateResponse
from app.services.security import (
    get_session_user,
    new_session,
    password_matches,
    revoke_session,
    set_session_cookie,
)
from app.services.uploads import save_upload
from app.services.users import (
    create_user,
    find_user_by_email,
    profile_response,
)


router = APIRouter(prefix="/api")


@router.post("/signup", response_model=ProfileUpdateResponse)
async def signup(
    response: Response,
    profile: Annotated[str, Form()],
    password: Annotated[str, Form()],
    profile_picture: Annotated[UploadFile | None, File()] = None,
    resume: Annotated[UploadFile | None, File()] = None,
) -> ProfileUpdateResponse:
    try:
        data = ProfileData.model_validate_json(profile)
    except (ValueError, ValidationError) as error:
        raise HTTPException(status_code=400, detail="Please complete the required profile details.") from error
    if not data.name.strip() or not data.username.strip() or not data.email.strip() or not password:
        raise HTTPException(status_code=400, detail="Name, username, email, and password are required.")

    data.profile_picture = await save_upload(profile_picture)
    try:
        data.resume, extracted = await store_resume(resume)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    data, extracted_added = add_extracted_profile(data, extracted)
    try:
        user = create_user(data, password)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    set_session_cookie(response, new_session(user.id))
    return ProfileUpdateResponse(
        profile=profile_response(user),
        extracted_added=extracted_added,
    )


@router.post("/login", response_model=ProfileResponse)
def login(credentials: LoginRequest, response: Response) -> ProfileResponse:
    user = find_user_by_email(str(credentials.email))
    if user is None or not password_matches(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    set_session_cookie(response, new_session(user.id))
    return profile_response(user)


@router.post("/logout")
def logout(
    response: Response,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, bool]:
    revoke_session(token)
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/me", response_model=ProfileResponse)
def me(token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> ProfileResponse:
    return profile_response(get_session_user(token))
