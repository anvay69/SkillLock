import json
import sqlite3
from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.database import database
from app.models.assessment import Assessment, AssessmentAttempt


ASSESSMENT_VIOLATION_LIMIT = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_assessment(db: sqlite3.Connection, assessment_id: str) -> Assessment:
    row = db.execute(
        """SELECT assessments.*,
                  (SELECT COUNT(*) FROM assessment_questions
                   WHERE assessment_id = assessments.id) AS question_count
           FROM assessments WHERE id = ?""",
        (assessment_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return Assessment.from_row(row)


def _get_attempt(db: sqlite3.Connection, attempt_id: int, user_id: int) -> AssessmentAttempt:
    row = db.execute(
        "SELECT * FROM assessment_attempts WHERE id = ? AND user_id = ?",
        (attempt_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment attempt not found.")
    return AssessmentAttempt.from_row(row)


def _duration_seconds(started_at: str, now: datetime | None = None) -> int:
    started = datetime.fromisoformat(started_at)
    return max(0, int(((now or _now()) - started).total_seconds()))


def _ensure_in_progress(attempt: AssessmentAttempt, time_limit_minutes: int) -> None:
    if attempt.status != "in_progress":
        raise HTTPException(status_code=409, detail="This assessment attempt has already been submitted.")
    if _duration_seconds(attempt.started_at) >= time_limit_minutes * 60:
        raise HTTPException(status_code=409, detail="The time limit has elapsed; submit your attempt.")


def _violation_count(db: sqlite3.Connection, attempt_id: int) -> int:
    events = db.execute(
        """SELECT event_type FROM assessment_events
           WHERE attempt_id = ? ORDER BY id""",
        (attempt_id,),
    ).fetchall()
    violation_count = 0
    incident_open = False
    for event in events:
        event_type = event["event_type"]
        if event_type in {"tab_hidden", "window_blur", "fullscreen_exit"}:
            if not incident_open:
                violation_count += 1
                incident_open = True
        elif event_type in {"tab_visible", "window_focus", "fullscreen_enter"}:
            incident_open = False
    return violation_count


def _finalize_attempt(
    db: sqlite3.Connection,
    attempt: AssessmentAttempt,
    time_limit_minutes: int,
) -> None:
    rows = db.execute(
        """SELECT questions.correct_answer, answers.selected_option
           FROM assessment_questions AS questions
           LEFT JOIN assessment_answers AS answers
             ON answers.attempt_id = ? AND answers.question_id = questions.id
           WHERE questions.assessment_id = ?""",
        (attempt.id, attempt.assessment_id),
    ).fetchall()
    score = sum(row["selected_option"] == row["correct_answer"] for row in rows)
    now = _now()
    duration = min(_duration_seconds(attempt.started_at, now), time_limit_minutes * 60)
    db.execute(
        """UPDATE assessment_attempts
           SET status = 'submitted', submitted_at = ?, duration_seconds = ?, score = ?
           WHERE id = ? AND user_id = ? AND status = 'in_progress'""",
        (now.isoformat(), duration, score, attempt.id, attempt.user_id),
    )


def list_assessments(skill: str | None, topic: str | None) -> list[dict]:
    query = """SELECT assessments.*,
                      (SELECT COUNT(*) FROM assessment_questions
                       WHERE assessment_id = assessments.id) AS question_count
               FROM assessments"""
    clauses = []
    parameters: list[str] = []
    if skill:
        clauses.append("skill LIKE ?")
        parameters.append(f"%{skill}%")
    if topic:
        clauses.append("topic LIKE ?")
        parameters.append(f"%{topic}%")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY title"
    with database() as db:
        return [
            Assessment.from_row(row).__dict__
            for row in db.execute(query, parameters).fetchall()
        ]


def get_assessment(assessment_id: str) -> dict:
    with database() as db:
        return _get_assessment(db, assessment_id).__dict__


def start_attempt(assessment_id: str, user_id: int) -> dict:
    now = _now()
    with database() as db:
        assessment = _get_assessment(db, assessment_id)
        if assessment.question_count == 0:
            raise HTTPException(status_code=409, detail="This assessment has no questions.")
        existing_attempt = db.execute(
            """SELECT 1 FROM assessment_attempts
               WHERE user_id = ? AND assessment_id = ? LIMIT 1""",
            (user_id, assessment_id),
        ).fetchone()
        if existing_attempt:
            raise HTTPException(status_code=409, detail="You have already started this assessment.")
        cursor = db.execute(
            """INSERT INTO assessment_attempts
               (user_id, assessment_id, status, started_at, total_questions)
               VALUES (?, ?, 'in_progress', ?, ?)""",
            (user_id, assessment_id, now.isoformat(), assessment.question_count),
        )
        return {
            "attempt_id": cursor.lastrowid,
            "assessment_id": assessment.id,
            "status": "in_progress",
            "started_at": now,
            "time_limit_seconds": assessment.time_limit_minutes * 60,
            "question_count": assessment.question_count,
            "violation_limit": ASSESSMENT_VIOLATION_LIMIT,
        }


def get_attempt_questions(attempt_id: int, user_id: int) -> dict:
    with database() as db:
        attempt = _get_attempt(db, attempt_id, user_id)
        assessment = _get_assessment(db, attempt.assessment_id)
        if (
            attempt.status == "in_progress"
            and _duration_seconds(attempt.started_at) >= assessment.time_limit_minutes * 60
        ):
            _finalize_attempt(db, attempt, assessment.time_limit_minutes)
            attempt = _get_attempt(db, attempt_id, user_id)
        rows = db.execute(
            """SELECT questions.*, answers.selected_option
               FROM assessment_questions AS questions
               LEFT JOIN assessment_answers AS answers
                 ON answers.question_id = questions.id AND answers.attempt_id = ?
               WHERE questions.assessment_id = ?
               ORDER BY questions.position""",
            (attempt_id, attempt.assessment_id),
        ).fetchall()
        violation_count = _violation_count(db, attempt_id)
    questions = []
    for index, row in enumerate(rows):
        questions.append(
            {
                "id": row["id"],
                "position": row["position"],
                "prompt": row["prompt"],
                "options": json.loads(row["options_json"]),
                "difficulty": row["difficulty"],
                "selected_option": row["selected_option"],
                "previous_question_id": rows[index - 1]["id"] if index > 0 else None,
                "next_question_id": rows[index + 1]["id"] if index + 1 < len(rows) else None,
            }
        )
    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "elapsed_seconds": (
            attempt.duration_seconds
            if attempt.duration_seconds is not None
            else _duration_seconds(attempt.started_at)
        ),
        "time_limit_seconds": assessment.time_limit_minutes * 60,
        "violation_count": violation_count,
        "questions": questions,
    }


def get_attempt_question(attempt_id: int, question_id: str, user_id: int) -> dict:
    with database() as db:
        attempt = _get_attempt(db, attempt_id, user_id)
        assessment = _get_assessment(db, attempt.assessment_id)
        if (
            attempt.status == "in_progress"
            and _duration_seconds(attempt.started_at) >= assessment.time_limit_minutes * 60
        ):
            _ensure_in_progress(attempt, assessment.time_limit_minutes)
        rows = db.execute(
            """SELECT questions.*, answers.selected_option
               FROM assessment_questions AS questions
               LEFT JOIN assessment_answers AS answers
                 ON answers.question_id = questions.id AND answers.attempt_id = ?
               WHERE questions.assessment_id = ?
               ORDER BY questions.position""",
            (attempt_id, attempt.assessment_id),
        ).fetchall()
    for index, row in enumerate(rows):
        if row["id"] == question_id:
            return {
                "id": row["id"],
                "position": row["position"],
                "prompt": row["prompt"],
                "options": json.loads(row["options_json"]),
                "difficulty": row["difficulty"],
                "selected_option": row["selected_option"],
                "previous_question_id": rows[index - 1]["id"] if index > 0 else None,
                "next_question_id": rows[index + 1]["id"] if index + 1 < len(rows) else None,
            }
    raise HTTPException(status_code=404, detail="Question not found in this attempt.")


def save_answer(attempt_id: int, question_id: str, selected_option: int, user_id: int) -> dict:
    with database() as db:
        attempt = _get_attempt(db, attempt_id, user_id)
        assessment = _get_assessment(db, attempt.assessment_id)
        if (
            attempt.status == "in_progress"
            and _duration_seconds(attempt.started_at) >= assessment.time_limit_minutes * 60
        ):
            _ensure_in_progress(attempt, assessment.time_limit_minutes)
        question = db.execute(
            """SELECT id, options_json FROM assessment_questions
               WHERE id = ? AND assessment_id = ?""",
            (question_id, attempt.assessment_id),
        ).fetchone()
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found in this attempt.")
        if selected_option < 0 or selected_option >= len(json.loads(question["options_json"])):
            raise HTTPException(status_code=400, detail="Select one of the question options.")
        _ensure_in_progress(attempt, assessment.time_limit_minutes)
        db.execute(
            """INSERT INTO assessment_answers (attempt_id, question_id, selected_option)
               VALUES (?, ?, ?)
               ON CONFLICT(attempt_id, question_id)
               DO UPDATE SET selected_option = excluded.selected_option""",
            (attempt_id, question_id, selected_option),
        )
    return {
        "attempt_id": attempt_id,
        "question_id": question_id,
        "selected_option": selected_option,
        "saved": True,
    }


def record_event(attempt_id: int, event_type: str, user_id: int) -> dict:
    recorded_at = _now()
    time_expired = False
    with database() as db:
        attempt = _get_attempt(db, attempt_id, user_id)
        if attempt.status != "in_progress":
            raise HTTPException(status_code=409, detail="This assessment attempt has already been submitted.")
        assessment = _get_assessment(db, attempt.assessment_id)
        if _duration_seconds(attempt.started_at) >= assessment.time_limit_minutes * 60:
            _finalize_attempt(db, attempt, assessment.time_limit_minutes)
            time_expired = True
        else:
            db.execute(
                """INSERT INTO assessment_events (attempt_id, event_type, recorded_at)
                   VALUES (?, ?, ?)""",
                (attempt_id, event_type, recorded_at.isoformat()),
            )
            violation_count = _violation_count(db, attempt_id)
            if violation_count >= ASSESSMENT_VIOLATION_LIMIT:
                _finalize_attempt(db, attempt, assessment.time_limit_minutes)
                attempt = _get_attempt(db, attempt_id, user_id)
        counts = db.execute(
            """SELECT COUNT(*) AS event_count,
                      SUM(CASE WHEN event_type = 'tab_hidden' THEN 1 ELSE 0 END) AS tab_switch_count,
                      SUM(CASE WHEN event_type IN ('window_blur', 'window_focus') THEN 1 ELSE 0 END) AS focus_change_count
               FROM assessment_events WHERE attempt_id = ?""",
            (attempt_id,),
        ).fetchone()
        if time_expired:
            violation_count = _violation_count(db, attempt_id)
            attempt = _get_attempt(db, attempt_id, user_id)
    if time_expired:
        raise HTTPException(status_code=409, detail="The time limit has elapsed; your attempt was submitted.")
    return {
        "attempt_id": attempt_id,
        "event_type": event_type,
        "recorded_at": recorded_at,
        "event_count": counts["event_count"],
        "tab_switch_count": counts["tab_switch_count"] or 0,
        "focus_change_count": counts["focus_change_count"] or 0,
        "violation_count": violation_count,
        "attempt_status": attempt.status,
    }


def _result(db: sqlite3.Connection, attempt_id: int, user_id: int) -> dict:
    attempt = _get_attempt(db, attempt_id, user_id)
    assessment = _get_assessment(db, attempt.assessment_id)
    if attempt.status != "submitted":
        raise HTTPException(status_code=409, detail="This assessment attempt has not been submitted.")
    rows = db.execute(
        """SELECT questions.id, questions.prompt, questions.options_json,
                  questions.correct_answer, questions.explanation, answers.selected_option
           FROM assessment_questions AS questions
           LEFT JOIN assessment_answers AS answers
             ON answers.attempt_id = ? AND answers.question_id = questions.id
           WHERE questions.assessment_id = ?
           ORDER BY questions.position""",
        (attempt_id, attempt.assessment_id),
    ).fetchall()
    answers = [
        {
            "question_id": row["id"],
            "prompt": row["prompt"],
            "options": json.loads(row["options_json"]),
            "selected_option": row["selected_option"],
            "correct_answer": row["correct_answer"],
            "is_correct": row["selected_option"] == row["correct_answer"],
            "explanation": row["explanation"],
        }
        for row in rows
    ]
    score = attempt.score or 0
    total = attempt.total_questions
    return {
        "attempt_id": attempt.id,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "status": attempt.status,
        "score": score,
        "total_questions": total,
        "percentage": round(score * 100 / total, 1) if total else 0,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "duration_seconds": attempt.duration_seconds,
        "answers": answers,
    }


def submit_attempt(attempt_id: int, user_id: int) -> dict:
    with database() as db:
        attempt = _get_attempt(db, attempt_id, user_id)
        if attempt.status == "submitted":
            return _result(db, attempt_id, user_id)
        assessment = _get_assessment(db, attempt.assessment_id)
        _finalize_attempt(db, attempt, assessment.time_limit_minutes)
        return _result(db, attempt_id, user_id)


def assessment_history(user_id: int) -> list[dict]:
    with database() as db:
        rows = db.execute(
            """SELECT attempts.id AS attempt_id, assessments.id AS assessment_id,
                      assessments.title AS assessment_title, assessments.skill,
                      assessments.topic, attempts.status, attempts.score,
                      attempts.total_questions, attempts.started_at, attempts.submitted_at,
                      attempts.duration_seconds
               FROM assessment_attempts AS attempts
               JOIN assessments ON assessments.id = attempts.assessment_id
               WHERE attempts.user_id = ?
               ORDER BY attempts.started_at DESC""",
            (user_id,),
        ).fetchall()
    return [
        {
            **dict(row),
            "percentage": (
                round(row["score"] * 100 / row["total_questions"], 1)
                if row["score"] is not None and row["total_questions"]
                else None
            ),
        }
        for row in rows
    ]
