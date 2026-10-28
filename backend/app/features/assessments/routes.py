from typing import Annotated

from fastapi import APIRouter, Cookie, Query

from app.core.config import SESSION_COOKIE
from app.features.assessments import service
from app.schemas.assessment import (
    AnswerRequest,
    AnswerResponse,
    AssessmentDetail,
    AssessmentHistoryItem,
    AssessmentSummary,
    AttemptQuestion,
    AttemptQuestions,
    AttemptResult,
    AttemptStart,
    EventRequest,
    EventResponse,
)
from app.services.security import get_session_user


router = APIRouter(prefix="/api")


@router.get("/assessments", response_model=list[AssessmentSummary])
def list_assessments(
    skill: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> list[dict]:
    get_session_user(token)
    return service.list_assessments(skill, topic)


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetail)
def get_assessment(
    assessment_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    get_session_user(token)
    return service.get_assessment(assessment_id)


@router.post("/assessments/{assessment_id}/attempts", response_model=AttemptStart)
def start_attempt(
    assessment_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.start_attempt(assessment_id, user.id)


@router.get(
    "/assessments/attempts/{attempt_id}/questions",
    response_model=AttemptQuestions,
)
def get_attempt_questions(
    attempt_id: int,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.get_attempt_questions(attempt_id, user.id)


@router.get(
    "/assessments/attempts/{attempt_id}/questions/{question_id}",
    response_model=AttemptQuestion,
)
def get_attempt_question(
    attempt_id: int,
    question_id: str,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.get_attempt_question(attempt_id, question_id, user.id)


@router.put(
    "/assessments/attempts/{attempt_id}/answers/{question_id}",
    response_model=AnswerResponse,
)
def save_answer(
    attempt_id: int,
    question_id: str,
    answer: AnswerRequest,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.save_answer(attempt_id, question_id, answer.selected_option, user.id)


@router.post(
    "/assessments/attempts/{attempt_id}/events",
    response_model=EventResponse,
)
def record_event(
    attempt_id: int,
    event: EventRequest,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.record_event(attempt_id, event.event_type, user.id)


@router.post(
    "/assessments/attempts/{attempt_id}/submit",
    response_model=AttemptResult,
)
def submit_attempt(
    attempt_id: int,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict:
    user = get_session_user(token)
    return service.submit_attempt(attempt_id, user.id)


@router.get("/me/assessment-history", response_model=list[AssessmentHistoryItem])
def assessment_history(
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> list[dict]:
    user = get_session_user(token)
    return service.assessment_history(user.id)
