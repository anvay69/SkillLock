import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

DATABASE = Path(os.getenv("SKILLLOCK_DATABASE", BACKEND_DIR / "skilllock.db"))
UPLOADS = Path(os.getenv("SKILLLOCK_UPLOADS", BACKEND_DIR / "uploads"))
PRIVATE_RESUMES = Path(os.getenv("SKILLLOCK_PRIVATE_RESUMES", BACKEND_DIR / "private_resumes"))
SEED_FILE = BACKEND_DIR / "seed_data.json"
SESSION_COOKIE = "skilllock_session"
SESSION_DAYS = 14
PASSWORD_ROUNDS = 310_000
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    os.getenv(
        "SKILLLOCK_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ),
)
CORS_ORIGINS = [
    origin.strip()
    for origin in _cors_origins.split(",")
    if origin.strip()
]
