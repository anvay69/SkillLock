from typing import Annotated

from fastapi import APIRouter, Cookie, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError

from app.core.config import SESSION_COOKIE
from app.features.resume.service import (
    add_extracted_profile,
    promote_staged_resume,
    remove_resume,
    store_resume,
)
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
    update_user_profile,
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
        data.resume, extracted = await store_resume(resume, owner_id=0)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    data, extracted_added = add_extracted_profile(data, extracted)
    try:
        user = create_user(data, password)
    except ValueError as error:
        remove_resume(data.resume, owner_id=0)
        raise HTTPException(status_code=409, detail=str(error)) from error
    if data.resume:
        try:
            data.resume = promote_staged_resume(data.resume, user.id)
            user = update_user_profile(user.id, data)
        except OSError as error:
            raise HTTPException(
                status_code=500,
                detail="Your account was created, but the resume could not be finalized. Sign in and upload it again.",
            ) from error
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


@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    profile: Annotated[str, Form()],
    profile_picture: Annotated[UploadFile | None, File()] = None,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> ProfileResponse:
    user = get_session_user(token)
    try:
        data = ProfileData.model_validate_json(profile)
    except (ValueError, ValidationError) as error:
        raise HTTPException(status_code=400, detail="Please review your profile details.") from error
    if not data.name.strip() or not data.username.strip():
        raise HTTPException(status_code=400, detail="Name and username are required.")

    data.resume = user.profile.get("resume", "")
    if profile_picture and profile_picture.filename:
        data.profile_picture = await save_upload(profile_picture)
    try:
        user = update_user_profile(user.id, data)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return profile_response(user)
