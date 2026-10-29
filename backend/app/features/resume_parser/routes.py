import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, File, HTTPException, UploadFile

from app.core.config import SESSION_COOKIE
from app.features.resume.gemini import (
    ResumeGeminiConfigurationError,
    ResumeGeminiServiceError,
)
from app.features.resume.service import MAX_RESUME_BYTES, extract_resume
from app.schemas.profile import ProfileData
from app.schemas.resume_parser import ResumeParseResponse
from app.services.security import get_session_user


router = APIRouter(prefix="/api")
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/resume-parser/parse", response_model=ResumeParseResponse)
async def parse_resume(
    resume: Annotated[UploadFile, File()],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> ResumeParseResponse:
    get_session_user(token)
    extension = Path(resume.filename or "").suffix.casefold()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Resume must be a PDF or DOCX file.")

    try:
        with tempfile.TemporaryDirectory(prefix="skilllock-resume-parser-") as directory:
            path = Path(directory) / f"resume{extension}"
            total_size = 0
            with path.open("xb") as temporary_file:
                while chunk := await resume.read(64 * 1024):
                    total_size += len(chunk)
                    if total_size > MAX_RESUME_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail="Resume must be 5 MB or smaller.",
                        )
                    temporary_file.write(chunk)
            profile = ProfileData(name="", username="", email="")
            extracted = extract_resume(path, profile)
            return ResumeParseResponse.model_validate(extracted.model_dump())
    except ResumeGeminiConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ResumeGeminiServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
