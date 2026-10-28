import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE = Path(os.getenv("SKILLLOCK_DATABASE", BACKEND_DIR / "skilllock.db"))
UPLOADS = Path(os.getenv("SKILLLOCK_UPLOADS", BACKEND_DIR / "uploads"))
SEED_FILE = BACKEND_DIR / "seed_data.json"
SESSION_COOKIE = "skilllock_session"
SESSION_DAYS = 14
PASSWORD_ROUNDS = 310_000
