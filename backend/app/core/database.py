import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import DATABASE, SEED_FILE


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    with connect() as connection:
        yield connection


def initialize_database() -> None:
    seed = json.loads(SEED_FILE.read_text())
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                profile_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY COLLATE NOCASE
            );
            """
        )
        db.executemany(
            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
            [(name.strip(),) for name in seed["skills"] if name.strip()],
        )
        candidate = seed["candidate"]
        from app.services.security import hash_password

        db.execute(
            """INSERT OR IGNORE INTO users
               (name, username, email, password_hash, profile_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                candidate["name"],
                candidate["username"],
                candidate["email"].lower(),
                hash_password(candidate["password"]),
                json.dumps(candidate["profile"]),
            ),
        )
