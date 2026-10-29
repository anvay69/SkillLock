import { useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";

function RequirementList({ title, requirements }) {
  return (
    <section className="jd-analysis-group">
      <h3>{title}</h3>
      {requirements.length ? (
        <ul>{requirements.map((item) => <li key={item}>{item}</li>)}</ul>
      ) : <p className="muted">No {title.toLowerCase()} identified.</p>}
    </section>
  );
}

export default function JDAnalysisPage({
  onDashboard,
  onProfile,
  onJobMatching,
  onLogout,
}) {
  const [jobDescription, setJobDescription] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

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
    setResult(null);
    setAnalyzing(true);
    try {
      const analysis = await request("/api/jd-analysis/analyze", {
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

  return (
    <main className="dashboard-page jd-analysis-page">
      <BrandHeader>
        <div className="dashboard-nav">
          <button className="nav-link" onClick={onDashboard}>Dashboard</button>
          <button className="nav-link" onClick={onProfile}>Profile</button>
          <button className="nav-link" onClick={onJobMatching}>Job matching</button>
          <span className="nav-link active" aria-current="page">JD analysis</span>
          <button className="logout-button" onClick={logout}>Sign out</button>
        </div>
      </BrandHeader>
      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <div>
            <p className="eyebrow">UNDERSTAND THE ROLE</p>
            <h1>Job description analysis</h1>
            <p>Get a clear breakdown of role requirements and practical preparation suggestions.</p>
          </div>
          <button className="secondary-button" onClick={onJobMatching}>Compare with my profile</button>
        </section>

        <section className="job-match-form-section" aria-labelledby="jd-analysis-form-heading">
          <div className="job-match-section-heading">
            <h2 id="jd-analysis-form-heading">Add a job description</h2>
            <p>Paste the JD, provide a public LinkedIn job or post URL, or use both.</p>
          </div>
          <form className="job-match-form" onSubmit={analyze}>
            <label className="field">
              <span>Job description <span className="field-optional">(optional)</span></span>
              <textarea
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                maxLength={20000}
                rows={8}
                placeholder="Paste the role description, including responsibilities and qualifications."
              />
            </label>
            <label className="field">
              <span>LinkedIn public job or post URL <span className="field-optional">(optional)</span></span>
              <input
                type="url"
                value={linkedinUrl}
                onChange={(event) => setLinkedinUrl(event.target.value)}
                maxLength={2048}
                placeholder="https://www.linkedin.com/jobs/view/..."
              />
            </label>
            <p className="job-match-note">
              LinkedIn content must be publicly available. When both sources are provided, they are combined if they share meaningful job-related terms.
            </p>
            {error && <p className="error" role="alert">{error}</p>}
            <button
              className="primary-button"
              disabled={analyzing || (!jobDescription.trim() && !linkedinUrl.trim())}
            >
              {analyzing ? "Analyzing..." : "Analyze job description"} <span aria-hidden="true">→</span>
            </button>
          </form>
        </section>

        {result && (
          <section className="jd-analysis-results" aria-live="polite">
            <div className="job-match-section-heading">
              <p className="eyebrow">YOUR ANALYSIS</p>
              <h2>{result.job_title || "Role requirements"}</h2>
              {result.company && <p>{result.company}</p>}
            </div>
            <p className="job-match-source">
              {result.source === "linkedin_listing"
                ? "Analysis based on the public LinkedIn listing."
                : result.source === "linkedin_listing_and_description"
                  ? "Analysis combines the public LinkedIn listing and pasted description."
                  : "Analysis based on the description you provided."}
            </p>
            {result.source_warning && <p className="job-match-warning">{result.source_warning}</p>}
            {result.job_summary && <p className="job-summary">{result.job_summary}</p>}

            <div className="jd-analysis-requirements">
              <RequirementList title="Required skills" requirements={result.required_skills} />
              <RequirementList title="Preferred skills" requirements={result.preferred_skills} />
            </div>

            <section className="job-suggestions jd-analysis-suggestions">
              <h3>Preparation suggestions</h3>
              {result.suggestions.length ? (
                <ul>{result.suggestions.map((suggestion) => <li key={suggestion}>{suggestion}</li>)}</ul>
              ) : <p className="muted">No suggestions were returned.</p>}
            </section>
          </section>
        )}
      </div>
      <PageFooter />
    </main>
  );
}
