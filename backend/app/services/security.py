import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response

from app.core.config import PASSWORD_ROUNDS, SESSION_COOKIE, SESSION_DAYS
from app.core.database import database
from app.models.user import User


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
    return f"{salt.hex()}:{hashed.hex()}"


def password_matches(password: str, stored_hash: str) -> bool:
    salt_hex, expected = stored_hash.split(":", 1)
    actual = hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return hmac.compare_digest(actual, expected)


def new_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with database() as db:
        db.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                user_id,
                (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat(),
            ),
        )
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SKILLLOCK_SECURE_COOKIE") == "1",
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )


def revoke_session(token: str | None) -> None:
    if token:
        with database() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))


def get_session_user(token: str | None) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Please log in.")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with database() as db:
        row = db.execute(
            """SELECT users.*
               FROM sessions JOIN users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
            (token_hash, now),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return User.from_row(row)
