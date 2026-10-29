import { useEffect, useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";
import ExtractionSummary from "../profile/ExtractionSummary";
import dashboardPlaceholders from "./dashboard_placeholders.json";

function getExperienceMonths(experience = []) {
  const currentDate = new Date();
  const currentMonth = currentDate.getFullYear() * 12 + currentDate.getMonth();
  const intervals = experience
    .map(({ start_date: startDate, end_date: endDate }) => {
      const startMatch = /^(\d{4})(?:-(\d{2}))?$/.exec(startDate || "");
      const endMatch = /^(\d{4})(?:-(\d{2}))?$/.exec(endDate || "");
      if (!startMatch || (endDate && !endMatch)) return null;
      if (
        (startMatch[2] && (Number(startMatch[2]) < 1 || Number(startMatch[2]) > 12))
        || (endMatch?.[2] && (Number(endMatch[2]) < 1 || Number(endMatch[2]) > 12))
      ) return null;

      const startMonth = Number(startMatch[1]) * 12
        + (startMatch[2] ? Number(startMatch[2]) - 1 : 0);
      const endMonth = endMatch
        ? Number(endMatch[1]) * 12 + (endMatch[2] ? Number(endMatch[2]) - 1 : 11)
        : currentMonth;
      if (startMonth > currentMonth || endMonth < startMonth) return null;
      return [startMonth, Math.min(endMonth, currentMonth)];
    })
    .filter(Boolean)
    .sort((left, right) => left[0] - right[0]);

  let totalMonths = 0;
  let intervalStart = null;
  let intervalEnd = null;
  for (const [startMonth, endMonth] of intervals) {
    if (intervalEnd === null || startMonth > intervalEnd + 1) {
      if (intervalStart !== null) totalMonths += intervalEnd - intervalStart + 1;
      intervalStart = startMonth;
      intervalEnd = endMonth;
    } else {
      intervalEnd = Math.max(intervalEnd, endMonth);
    }
  }
  if (intervalStart !== null) totalMonths += intervalEnd - intervalStart + 1;
  return totalMonths;
}

function formatExperience(months) {
  if (!months) return "Not specified";
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  if (!years) return `${remainingMonths} ${remainingMonths === 1 ? "month" : "months"}`;
  if (!remainingMonths) return `${years} ${years === 1 ? "year" : "years"}`;
  return `${years} yr ${remainingMonths} mo`;
}

function CandidateSnapshot({ user, onProfile }) {
  const skills = [...new Set(user.skills || [])].slice(0, 5);
  const expertise = [...new Set(
    (user.experience || []).map((item) => item.job_title?.trim()).filter(Boolean),
  )].slice(0, 3);

  return (
    <section className="candidate-snapshot" aria-labelledby="candidate-snapshot-heading">
      <div className="candidate-snapshot-heading">
        <div>
          <p className="eyebrow">YOUR PROFILE AT A GLANCE</p>
          <h2 id="candidate-snapshot-heading">Candidate snapshot</h2>
        </div>
        <button className="text-button" onClick={onProfile}>Update profile <span aria-hidden="true">→</span></button>
      </div>
      <div className="candidate-snapshot-grid">
        <div className="candidate-snapshot-item candidate-skills">
          <span className="candidate-snapshot-label">Major skills</span>
          {skills.length ? (
            <div className="candidate-skill-list">
              {skills.map((skill) => <span className="tag" key={skill}>{skill}</span>)}
              {(user.skills || []).length > skills.length && (
                <span className="candidate-more-skills">+{user.skills.length - skills.length} more</span>
              )}
            </div>
          ) : <p className="candidate-snapshot-empty">Add skills to your profile.</p>}
        </div>
        <div className="candidate-snapshot-item">
          <span className="candidate-snapshot-label">Years of experience</span>
          <strong>{formatExperience(getExperienceMonths(user.experience))}</strong>
          <span className="candidate-snapshot-hint">Based on dated roles</span>
        </div>
        <div className="candidate-snapshot-item">
          <span className="candidate-snapshot-label">Expertise</span>
          {expertise.length ? (
            <ul className="candidate-expertise-list">
              {expertise.map((role) => <li key={role}>{role}</li>)}
            </ul>
          ) : <p className="candidate-snapshot-empty">Add experience to highlight your expertise.</p>}
        </div>
      </div>
    </section>
  );
}

export default function DashboardPage({
  user,
  extractedAdded,
  onProfile,
  onLogout,
  onAssessment,
  onJobMatching,
}) {
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
          <span className="nav-link active" aria-current="page">Dashboard</span>
          <button className="nav-link" onClick={onProfile}>Profile</button>
          <a className="nav-link" href="#available-assessments">Assessments</a>
          <button className="nav-link" onClick={onJobMatching}>Job matching</button>
          <button className="logout-button" onClick={logout}>Sign out</button>
        </div>
      </BrandHeader>
      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <div>
            <p className="eyebrow">CANDIDATE DASHBOARD</p>
            <h1>Welcome back, {user.name.split(" ")[0]}.</h1>
            <p>Your profile and assessment progress, together in one place.</p>
          </div>
          <button className="primary-button" onClick={onProfile}>Review your profile <span aria-hidden="true">→</span></button>
        </section>
        <CandidateSnapshot user={user} onProfile={onProfile} />
        {error && <p className="error">{error}</p>}
        <ExtractionSummary extracted={extractedAdded} />
        <section className="dashboard-section" id="job-listings">
          <div className="dashboard-section-heading">
            <div><p className="eyebrow">OPPORTUNITIES FOR YOU</p><h2>Job Listings</h2></div>
          </div>
          <div className="opportunity-empty-state">
            {dashboardPlaceholders.jobs.map((job) => (
              <article className="opportunity-empty-item" key={job.title}>
                <span className="placeholder-label">{job.label}</span>
                <div>
                  <h3>{job.title}</h3>
                  <p>{job.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="dashboard-section" id="job-matching">
          <div className="dashboard-section-heading">
            <div><p className="eyebrow">MAKE YOUR NEXT MOVE</p><h2>Job Matching</h2></div>
          </div>
          <div className="job-matching-promo">
            <p>Compare a job description with your profile skills, see recognized requirements, and get a learning roadmap for gaps.</p>
            <button className="secondary-button" onClick={onJobMatching}>Analyze a job description <span aria-hidden="true">→</span></button>
          </div>
        </section>
        <section className="dashboard-section" id="available-assessments">
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
        <section className="dashboard-section" id="assessment-history">
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
      </div>
      <PageFooter />
    </main>
  );
}
