from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class Assessment:
    id: str
    title: str
    description: str
    skill: str
    topic: str
    instructions: str
    time_limit_minutes: int
    question_count: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Assessment":
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            skill=row["skill"],
            topic=row["topic"],
            instructions=row["instructions"],
            time_limit_minutes=row["time_limit_minutes"],
            question_count=row["question_count"],
        )


@dataclass(frozen=True)
class AssessmentAttempt:
    id: int
    user_id: int
    assessment_id: str
    status: str
    started_at: str
    submitted_at: str | None
    duration_seconds: int | None
    score: int | None
    total_questions: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AssessmentAttempt":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            assessment_id=row["assessment_id"],
            status=row["status"],
            started_at=row["started_at"],
            submitted_at=row["submitted_at"],
            duration_seconds=row["duration_seconds"],
            score=row["score"],
            total_questions=row["total_questions"],
        )
