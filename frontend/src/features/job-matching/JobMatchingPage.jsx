import { useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";

const progressLabels = {
  not_started: "Not started",
  learning: "Learning",
  completed: "Completed",
};

function SkillList({ title, skills, variant }) {
  return (
    <section className={`job-skill-group ${variant}`}>
      <h3>{title} <span>{skills.length}</span></h3>
      {skills.length ? (
        <div className="job-skill-list">
          {skills.map((skill) => <span className="tag" key={skill}>{skill}</span>)}
        </div>
      ) : <p className="muted">No skills in this group.</p>}
    </section>
  );
}

export default function JobMatchingPage({ onDashboard, onProfile, onLogout }) {
  const [jobDescription, setJobDescription] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [progressError, setProgressError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [savingSkills, setSavingSkills] = useState([]);

  async function logout() {
    setError("");
    try {
      await request("/api/logout", { method: "POST" });
      onLogout();
    } catch (problem) {
      setError(problem.message);
    }
  }

  async function analyze(event) {
    event.preventDefault();
    setError("");
    setProgressError("");
    setResult(null);
    setAnalyzing(true);
    try {
      const analysis = await request("/api/job-matching/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDescription,
          linkedin_url: linkedinUrl,
        }),
      });
      setResult(analysis);
    } catch (problem) {
      setError(problem.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function updateProgress(skill, status) {
    setProgressError("");
    setSavingSkills((current) => [...current, skill]);
    try {
      const response = await request("/api/job-matching/learning-progress", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill, status }),
      });
      setResult((current) => current && ({
        ...current,
        learning_roadmap: current.learning_roadmap.map((item) => ({
          ...item,
          status: response.learning_progress[item.skill] || item.status,
        })),
      }));
    } catch (problem) {
      setProgressError(problem.message);
    } finally {
      setSavingSkills((current) => current.filter((item) => item !== skill));
    }
  }

  return (
    <main className="dashboard-page job-matching-page">
      <BrandHeader>
        <div className="dashboard-nav">
          <button className="nav-link" onClick={onDashboard}>Dashboard</button>
          <button className="nav-link" onClick={onProfile}>Profile</button>
          <span className="nav-link active" aria-current="page">Job matching</span>
          <button className="logout-button" onClick={logout}>Sign out</button>
        </div>
      </BrandHeader>
      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <div>
            <p className="eyebrow">ROLE FIT</p>
            <h1>Explore your skill match</h1>
            <p>Compare a job description with the skills in your profile.</p>
          </div>
          <button className="secondary-button" onClick={onProfile}>Update your profile</button>
        </section>

        <section className="job-match-form-section" aria-labelledby="job-match-form-heading">
          <div className="job-match-section-heading">
            <h2 id="job-match-form-heading">Analyze a LinkedIn job</h2>
            <p>Use a public listing URL, paste the job description, or provide both.</p>
          </div>
          <form className="job-match-form" onSubmit={analyze}>
            <label className="field">
              <span>Job description <span className="field-optional">(optional)</span></span>
              <textarea
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                maxLength={20000}
                rows={8}
                placeholder="Paste the role description here, including skills and qualifications."
              />
            </label>
            <label className="field">
              <span>LinkedIn public job URL <span className="field-optional">(optional)</span></span>
              <input
                type="url"
                value={linkedinUrl}
                onChange={(event) => setLinkedinUrl(event.target.value)}
                maxLength={2048}
                placeholder="https://www.linkedin.com/jobs/view/..."
              />
            </label>
            <p className="job-match-note">
              Public LinkedIn job pages are retrieved without signing in. If LinkedIn limits access or the listing is no longer public, paste its description instead.
            </p>
            {error && <p className="error" role="alert">{error}</p>}
            <button
              className="primary-button"
              disabled={analyzing || (!jobDescription.trim() && !linkedinUrl.trim())}
            >
              {analyzing ? "Analyzing..." : "Analyze job match"} <span aria-hidden="true">→</span>
            </button>
          </form>
        </section>

        {result && (
          <section className="job-match-results" aria-live="polite">
            <div className="job-match-section-heading">
              <p className="eyebrow">YOUR ANALYSIS</p>
              <h2>{result.job_title || "Skill match results"}</h2>
              {result.company && <p>{result.company}</p>}
            </div>
            <p className="job-match-source">
              {result.source === "linkedin_listing"
                ? "Gemini extracted job requirements from the public listing; profile comparison was performed in SkillLock."
                : result.source === "linkedin_listing_and_description"
                  ? "Gemini analyzed the public listing and your additional description; profile comparison was performed in SkillLock."
                  : "Gemini analyzed the job description; profile comparison was performed in SkillLock."}
            </p>
            {result.source_warning && <p className="job-match-warning">{result.source_warning}</p>}
            {result.job_summary && <p className="job-summary">{result.job_summary}</p>}
            <p className="readiness-feedback">{result.readiness_feedback}</p>
            <div className="job-skill-columns">
              <SkillList title="Matched skills" skills={result.matched_skills} variant="matched" />
              <SkillList title="Skills to develop" skills={result.missing_skills} variant="missing" />
            </div>
            <div className="job-priority-summary">
              <span><strong>Required:</strong> {result.required_skills.join(", ") || "None recognized"}</span>
              <span><strong>Preferred:</strong> {result.preferred_skills.join(", ") || "None recognized"}</span>
            </div>

            {result.suggestions.length > 0 && (
              <section className="job-suggestions">
                <h3>Suggestions</h3>
                <ul>{result.suggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}</ul>
              </section>
            )}

            {result.learning_roadmap.length > 0 && (
              <section className="job-roadmap">
                <h3>Learning roadmap</h3>
                <div className="job-roadmap-list">
                  {result.learning_roadmap.map((item) => (
                    <article className="job-roadmap-item" key={item.skill}>
                      <div className="job-roadmap-heading">
                        <div>
                          <span className={`priority-label ${item.priority}`}>{item.priority}</span>
                          <h4>{item.skill}</h4>
                        </div>
                        <label className="progress-control">
                          <span className="visually-hidden">Learning progress for {item.skill}</span>
                          <select
                            value={item.status}
                            disabled={savingSkills.includes(item.skill)}
                            onChange={(event) => updateProgress(item.skill, event.target.value)}
                          >
                            {Object.entries(progressLabels).map(([value, label]) => (
                              <option key={value} value={value}>{label}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <ul>{item.steps.map((step) => <li key={step}>{step}</li>)}</ul>
                      <p><strong>Practice:</strong> {item.practice_task}</p>
                      <p><strong>Project idea:</strong> {item.project_idea}</p>
                    </article>
                  ))}
                </div>
                {progressError && <p className="error" role="alert">{progressError}</p>}
              </section>
            )}
          </section>
        )}
      </div>
      <PageFooter />
    </main>
  );
}
