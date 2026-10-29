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
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                skill TEXT NOT NULL,
                topic TEXT NOT NULL,
                instructions TEXT NOT NULL,
                time_limit_minutes INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assessment_questions (
                id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL REFERENCES assessments(id),
                position INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                options_json TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                UNIQUE (assessment_id, position)
            );
            CREATE TABLE IF NOT EXISTS assessment_attempts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                assessment_id TEXT NOT NULL REFERENCES assessments(id),
                status TEXT NOT NULL DEFAULT 'in_progress',
                started_at TEXT NOT NULL,
                submitted_at TEXT,
                duration_seconds INTEGER,
                score INTEGER,
                total_questions INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assessment_answers (
                attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
                question_id TEXT NOT NULL REFERENCES assessment_questions(id),
                selected_option INTEGER NOT NULL,
                PRIMARY KEY (attempt_id, question_id)
            );
            CREATE TABLE IF NOT EXISTS assessment_events (
                id INTEGER PRIMARY KEY,
                attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id),
                event_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )
        db.executemany(
            "INSERT OR IGNORE INTO skills (name) VALUES (?)",
            [(name.strip(),) for name in seed["skills"] if name.strip()],
        )
        from app.services.security import hash_password

        for candidate in [seed["candidate"], *seed.get("demo_candidates", [])]:
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
        for assessment in seed.get("assessments", []):
            db.execute(
                """INSERT OR IGNORE INTO assessments
                   (id, title, description, skill, topic, instructions, time_limit_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    assessment["id"],
                    assessment["title"],
                    assessment["description"],
                    assessment["skill"],
                    assessment.get("topic", assessment["skill"]),
                    assessment["instructions"],
                    assessment["time_limit_minutes"],
                ),
            )
            db.executemany(
                """INSERT OR IGNORE INTO assessment_questions
                   (id, assessment_id, position, prompt, options_json, correct_answer, explanation, difficulty)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        question["id"],
                        assessment["id"],
                        position,
                        question["prompt"],
                        json.dumps(question["options"]),
                        question["correct_answer"],
                        question["explanation"],
                        question.get("difficulty", "beginner"),
                    )
                    for position, question in enumerate(assessment["questions"])
                ],
            )
