import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

function ResultView({ result, onDashboard }) {
  return (
    <main className="assessment-page">
      <BrandHeader>
        <button className="profile-link" onClick={onDashboard}>Dashboard</button>
      </BrandHeader>
      <div className="assessment-wrap">
        <p className="eyebrow">ASSESSMENT COMPLETE</p>
        <h1>{result.assessment_title}</h1>
        <section className="assessment-result">
          <strong>{result.score}<span> / {result.total_questions}</span></strong>
          <p>{result.percentage}% · completed in {formatTime(result.duration_seconds)}</p>
        </section>
        <section className="result-review">
          <h2>Answer review</h2>
          {result.answers.map((answer, index) => (
            <article className="review-question" key={answer.question_id}>
              <p className="review-number">QUESTION {index + 1} · {answer.is_correct ? "CORRECT" : "REVIEW"}</p>
              <h3>{answer.prompt}</h3>
              <p><strong>Your answer:</strong> {answer.selected_option === null ? "Not answered" : answer.options[answer.selected_option]}</p>
              <p><strong>Correct answer:</strong> {answer.options[answer.correct_answer]}</p>
              <p className="review-explanation">{answer.explanation}</p>
            </article>
          ))}
        </section>
        <button className="primary-button assessment-action" onClick={onDashboard}>Back to dashboard <span>→</span></button>
      </div>
      <PageFooter />
    </main>
  );
}

export default function AssessmentPage({ assessmentId, onDashboard }) {
  const [assessment, setAssessment] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [result, setResult] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submissionStarted = useRef(false);

  useEffect(() => {
    request(`/api/assessments/${encodeURIComponent(assessmentId)}`)
      .then(setAssessment)
      .catch((problem) => setError(problem.message))
      .finally(() => setLoading(false));
  }, [assessmentId]);

  const submitAssessment = useCallback(async () => {
    if (!attempt || submissionStarted.current) return;
    submissionStarted.current = true;
    setBusy(true);
    setError("");
    try {
      setResult(await request(`/api/assessments/attempts/${attempt.attempt_id}/submit`, { method: "POST" }));
    } catch (problem) {
      submissionStarted.current = false;
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }, [attempt]);

  async function startAssessment() {
    setBusy(true);
    setError("");
    try {
      const started = await request(`/api/assessments/${encodeURIComponent(assessmentId)}/attempts`, { method: "POST" });
      setAttempt(started);
      const attemptQuestions = await request(`/api/assessments/attempts/${started.attempt_id}/questions`);
      setQuestions(attemptQuestions.questions);
      setCurrentQuestion(attemptQuestions.questions[0] || null);
      const deadline = Date.parse(started.started_at) + started.time_limit_seconds * 1000;
      setRemainingSeconds(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!attempt || result) return undefined;
    const timer = window.setInterval(() => {
      const deadline = Date.parse(attempt.started_at) + attempt.time_limit_seconds * 1000;
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemainingSeconds(remaining);
      if (remaining === 0) submitAssessment();
    }, 500);
    return () => window.clearInterval(timer);
  }, [attempt, result, submitAssessment]);

  useEffect(() => {
    if (!attempt || result) return undefined;
    const report = (eventType) => {
      request(`/api/assessments/attempts/${attempt.attempt_id}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_type: eventType }),
      }).catch((problem) => setError(problem.message));
    };
    const visibilityChanged = () => report(document.hidden ? "tab_hidden" : "tab_visible");
    const blurred = () => report("window_blur");
    const focused = () => report("window_focus");
    document.addEventListener("visibilitychange", visibilityChanged);
    window.addEventListener("blur", blurred);
    window.addEventListener("focus", focused);
    return () => {
      document.removeEventListener("visibilitychange", visibilityChanged);
      window.removeEventListener("blur", blurred);
      window.removeEventListener("focus", focused);
    };
  }, [attempt, result]);

  async function navigateTo(questionId) {
    if (!attempt || !questionId) return;
    setError("");
    try {
      setCurrentQuestion(await request(
        `/api/assessments/attempts/${attempt.attempt_id}/questions/${encodeURIComponent(questionId)}`,
      ));
    } catch (problem) {
      setError(problem.message);
    }
  }

  async function selectAnswer(optionIndex) {
    if (!attempt || !currentQuestion || saving || result) return;
    setSaving(true);
    setError("");
    try {
      await request(
        `/api/assessments/attempts/${attempt.attempt_id}/answers/${encodeURIComponent(currentQuestion.id)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ selected_option: optionIndex }),
        },
      );
      setCurrentQuestion((question) => ({ ...question, selected_option: optionIndex }));
      setQuestions((items) => items.map((question) => question.id === currentQuestion.id
        ? { ...question, selected_option: optionIndex }
        : question));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setSaving(false);
    }
  }

  if (result) return <ResultView result={result} onDashboard={onDashboard} />;

  return (
    <main className="assessment-page">
      <BrandHeader>
        {attempt
          ? <span className={`assessment-timer ${remainingSeconds < 60 ? "urgent" : ""}`}>{formatTime(remainingSeconds ?? 0)}</span>
          : <button className="profile-link" onClick={onDashboard}>Dashboard</button>}
      </BrandHeader>
      <div className="assessment-wrap">
        {loading && <p className="muted">Loading assessment...</p>}
        {!loading && assessment && !attempt && (
          <section className="assessment-intro">
            <p className="eyebrow">{assessment.skill} · {assessment.topic}</p>
            <h1>{assessment.title}</h1>
            <p className="assessment-description">{assessment.description}</p>
            <div className="assessment-facts">
              <span>{assessment.time_limit_minutes} minutes</span>
              <span>{assessment.question_count} questions</span>
            </div>
            <div className="assessment-instructions">
              <h2>Instructions</h2>
              <p>{assessment.instructions}</p>
              <p>Choose one answer for each question. You may change your answers before submitting.</p>
            </div>
            <button className="primary-button assessment-action" onClick={startAssessment} disabled={busy}>
              {busy ? "Starting..." : "Start assessment"} <span>→</span>
            </button>
          </section>
        )}
        {attempt && currentQuestion && (
          <section className="question-panel">
            <p className="eyebrow">{assessment?.title} · QUESTION {currentQuestion.position + 1} OF {questions.length}</p>
            <div className="question-progress">
              {questions.map((question, index) => (
                <button
                  type="button"
                  key={question.id}
                  className={`${question.id === currentQuestion.id ? "current" : ""} ${question.selected_option !== null ? "answered" : ""}`}
                  aria-label={`Go to question ${index + 1}`}
                  disabled={saving || busy}
                  onClick={() => navigateTo(question.id)}
                >{index + 1}</button>
              ))}
            </div>
            <h1>{currentQuestion.prompt}</h1>
            <div className="answer-options">
              {currentQuestion.options.map((option, index) => (
                <button
                  type="button"
                  key={option}
                  className={`answer-option ${currentQuestion.selected_option === index ? "selected" : ""}`}
                  aria-pressed={currentQuestion.selected_option === index}
                  disabled={saving || busy}
                  onClick={() => selectAnswer(index)}
                >
                  <span className="option-letter">{String.fromCharCode(65 + index)}</span>
                  <span>{option}</span>
                </button>
              ))}
            </div>
            {saving && <p className="muted save-status">Saving answer...</p>}
            <div className="question-actions">
              <button
                type="button"
                className="secondary-button"
                disabled={!currentQuestion.previous_question_id || saving || busy}
                onClick={() => navigateTo(currentQuestion.previous_question_id)}
              >← Previous</button>
              <button
                type="button"
                className="secondary-button"
                disabled={!currentQuestion.next_question_id || saving || busy}
                onClick={() => navigateTo(currentQuestion.next_question_id)}
              >Next →</button>
            </div>
            <button className="primary-button assessment-action" onClick={submitAssessment} disabled={busy || saving}>
              {busy ? "Submitting..." : "Submit assessment"} <span>→</span>
            </button>
          </section>
        )}
        {attempt && !currentQuestion && !busy && <p className="muted">No questions are available for this attempt.</p>}
        {error && <p className="error">{error}</p>}
      </div>
      <PageFooter />
    </main>
  );
}
