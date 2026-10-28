from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, skills
from app.core.config import UPLOADS
from app.core.database import initialize_database
from app.features.resume.routes import router as resume_router


app = FastAPI(title="SkillLock API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOADS.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(resume_router)


@app.on_event("startup")
def startup() -> None:
    initialize_database()
