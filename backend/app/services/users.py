import json
import sqlite3

from app.core.database import database
from app.models.user import User
from app.schemas.profile import ProfileData, ProfileResponse
from app.services.security import hash_password


def find_user_by_email(email: str) -> User | None:
    with database() as db:
        row = db.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return User.from_row(row) if row else None


def create_user(profile: ProfileData, password: str) -> User:
    data = profile.model_dump()
    try:
        with database() as db:
            cursor = db.execute(
                """INSERT INTO users (name, username, email, password_hash, profile_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (profile.name, profile.username, profile.email.lower(), hash_password(password), json.dumps(data)),
            )
            for skill in profile.skills:
                if skill.strip():
                    db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill.strip(),))
            row = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError as error:
        raise ValueError("That email or username is already in use.") from error
    return User.from_row(row)


def update_user_profile(user_id: int, profile: ProfileData) -> User:
    data = profile.model_dump()
    try:
        with database() as db:
            db.execute(
                """UPDATE users
                   SET name = ?, username = ?, email = ?, profile_json = ?
                   WHERE id = ?""",
                (profile.name, profile.username, profile.email.lower(), json.dumps(data), user_id),
            )
            db.executemany(
                "INSERT OR IGNORE INTO skills (name) VALUES (?)",
                [(skill.strip(),) for skill in profile.skills if skill.strip()],
            )
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as error:
        raise ValueError("That email or username is already in use.") from error
    return User.from_row(row)


def list_skills() -> list[str]:
    with database() as db:
        return [row["name"] for row in db.execute("SELECT name FROM skills ORDER BY name")]


def profile_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        **{key: value for key, value in user.profile.items() if key not in {"name", "username", "email"}},
    )
