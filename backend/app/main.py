import mimetypes
from pathlib import Path
import re
from typing import Annotated

from fastapi import Cookie, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import auth, skills
from app.core.config import SESSION_COOKIE, UPLOADS
from app.core.database import initialize_database
from app.features.assessments.routes import router as assessments_router
from app.features.job_matching.routes import router as job_matching_router
from app.features.resume.routes import router as resume_router
from app.features.resume_parser.routes import router as resume_parser_router
from app.features.jd_analysis.routes import router as jd_analysis_router
from app.services.security import get_session_user


app = FastAPI(title="SkillLock API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOADS.mkdir(exist_ok=True)
app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(resume_router)
app.include_router(assessments_router)
app.include_router(job_matching_router)
app.include_router(jd_analysis_router)
app.include_router(resume_parser_router)


@app.get("/uploads/{filename}")
def get_uploaded_file(
    filename: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{32}(?:\.[a-z0-9]{1,12})?", filename, re.IGNORECASE):
        raise HTTPException(status_code=404, detail="File not found.")

    path = UPLOADS / filename
    resolved_uploads = UPLOADS.resolve()
    if not path.is_file() or path.resolve().parent != resolved_uploads:
        raise HTTPException(status_code=404, detail="File not found.")

    suffix = path.suffix.casefold()
    if suffix in {".pdf", ".docx"}:
        user = get_session_user(token)
        if user.profile.get("resume") != f"/uploads/{filename}":
            raise HTTPException(status_code=404, detail="File not found.")
        media_type = (
            "application/pdf"
            if suffix == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    else:
        media_type, _ = mimetypes.guess_type(filename)
        if media_type is None or not media_type.startswith("image/"):
            raise HTTPException(status_code=404, detail="File not found.")
        headers = {"X-Content-Type-Options": "nosniff"}

    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
        headers=headers,
    )


@app.on_event("startup")
def startup() -> None:
    initialize_database()
