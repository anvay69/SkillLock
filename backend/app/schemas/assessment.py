from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssessmentSummary(BaseModel):
    id: str
    title: str
    description: str
    skill: str
    topic: str
    time_limit_minutes: int
    question_count: int


class AssessmentDetail(AssessmentSummary):
    instructions: str


class AttemptStart(BaseModel):
    attempt_id: int
    assessment_id: str
    status: str
    started_at: datetime
    time_limit_seconds: int
    question_count: int


class AttemptQuestion(BaseModel):
    id: str
    position: int
    prompt: str
    options: list[str]
    difficulty: str
    selected_option: int | None = None
    previous_question_id: str | None = None
    next_question_id: str | None = None


class AttemptQuestions(BaseModel):
    attempt_id: int
    status: str
    started_at: datetime
    elapsed_seconds: int
    time_limit_seconds: int
    questions: list[AttemptQuestion]


class AnswerRequest(BaseModel):
    selected_option: int


class AnswerResponse(BaseModel):
    attempt_id: int
    question_id: str
    selected_option: int
    saved: bool


class EventRequest(BaseModel):
    event_type: Literal["tab_hidden", "tab_visible", "window_blur", "window_focus"]


class EventResponse(BaseModel):
    attempt_id: int
    event_type: str
    recorded_at: datetime
    event_count: int
    tab_switch_count: int
    focus_change_count: int


class SubmittedAnswer(BaseModel):
    question_id: str
    prompt: str
    options: list[str]
    selected_option: int | None
    correct_answer: int
    is_correct: bool
    explanation: str


class AttemptResult(BaseModel):
    attempt_id: int
    assessment_id: str
    assessment_title: str
    status: str
    score: int
    total_questions: int
    percentage: float
    started_at: datetime
    submitted_at: datetime
    duration_seconds: int
    answers: list[SubmittedAnswer] = Field(default_factory=list)


class AssessmentHistoryItem(BaseModel):
    attempt_id: int
    assessment_id: str
    assessment_title: str
    skill: str
    topic: str
    status: str
    score: int | None
    total_questions: int
    percentage: float | None
    started_at: datetime
    submitted_at: datetime | None
    duration_seconds: int | None
