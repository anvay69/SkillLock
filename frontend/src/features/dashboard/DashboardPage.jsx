import { useEffect, useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";
import ExtractionSummary from "../profile/ExtractionSummary";
import placeholders from "./dashboard_placeholders.json";

function PlaceholderCards({ items }) {
  return (
    <div className="dashboard-cards">
      {items.map((item) => (
        <article className="dashboard-card" key={item.title}>
          <span className="placeholder-label">{item.label}</span>
          <h3>{item.title}</h3>
          <p>{item.description}</p>
          <span className="placeholder-link">More details soon</span>
        </article>
      ))}
    </div>
  );
}

export default function DashboardPage({ user, extractedAdded, onProfile, onLogout, onAssessment }) {
  const [error, setError] = useState("");
  const [assessments, setAssessments] = useState([]);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    Promise.all([
      request("/api/assessments"),
      request("/api/me/assessment-history"),
    ])
      .then(([available, attempts]) => {
        setAssessments(available);
        setHistory(attempts);
      })
      .catch((problem) => setError(problem.message));
  }, []);

  async function logout() {
    setError("");
    try {
      await request("/api/logout", { method: "POST" });
      onLogout();
    } catch (problem) {
      setError(problem.message);
    }
  }

  return (
    <main className="dashboard-page">
      <BrandHeader>
        <div className="dashboard-nav">
          <button className="profile-link" onClick={onProfile}>View my profile <span>↗</span></button>
          <button className="logout-button" onClick={logout}>Sign out</button>
        </div>
      </BrandHeader>
      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <p className="eyebrow">YOUR SKILLLOCK DASHBOARD</p>
          <h1>Welcome, <em>{user.name.split(" ")[0]}</em>.</h1>
          <p>Your professional story, and what comes next, all in one place.</p>
          <button className="profile-link welcome-profile-link" onClick={onProfile}>View your candidate profile <span>→</span></button>
        </section>
        {error && <p className="error">{error}</p>}
        <ExtractionSummary extracted={extractedAdded} />
        <section className="dashboard-section">
          <div className="dashboard-section-heading">
            <div><p className="eyebrow">BUILD YOUR NEXT CHAPTER</p><h2>Available Assessments</h2></div>
            <span className="section-count">{String(assessments.length).padStart(2, "0")}</span>
          </div>
          {assessments.length ? (
            <div className="dashboard-cards">
              {assessments.map((assessment) => (
                <article className="dashboard-card assessment-card" key={assessment.id}>
                  <span className="placeholder-label">{assessment.skill} · {assessment.topic}</span>
                  <h3>{assessment.title}</h3>
                  <p>{assessment.description}</p>
                  <p className="assessment-meta">{assessment.time_limit_minutes} min <span>·</span> {assessment.question_count} questions</p>
                  <button className="primary-button" onClick={() => onAssessment(assessment.id)}>
                    Start assessment <span>→</span>
                  </button>
                </article>
              ))}
            </div>
          ) : !error ? <p className="muted">Loading assessments...</p> : null}
        </section>
        <section className="dashboard-section">
          <div className="dashboard-section-heading">
            <div><p className="eyebrow">YOUR PROGRESS</p><h2>Assessment History</h2></div>
            <span className="section-count">{String(history.length).padStart(2, "0")}</span>
          </div>
          {history.length ? (
            <div className="history-list">
              {history.map((attempt) => (
                <article className="history-row" key={attempt.attempt_id}>
                  <div>
                    <h3>{attempt.assessment_title}</h3>
                    <p>{new Date(attempt.started_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}</p>
                  </div>
                  <span className={`history-status ${attempt.status}`}>{attempt.status.replace("_", " ")}</span>
                  <strong>{attempt.score === null ? "—" : `${attempt.score}/${attempt.total_questions}`}</strong>
                </article>
              ))}
            </div>
          ) : <p className="muted">Your assessment attempts will appear here.</p>}
        </section>
        <section className="dashboard-section">
          <div className="dashboard-section-heading">
            <div><p className="eyebrow">OPPORTUNITIES FOR YOU</p><h2>Jobs Matched to You</h2></div>
            <span className="section-count">—</span>
          </div>
          <PlaceholderCards items={placeholders.jobs} />
        </section>
      </div>
      <PageFooter />
    </main>
  );
}
