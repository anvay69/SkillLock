import { useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";

const detailSections = [
  ["projects", "Projects"],
  ["experience", "Experience"],
  ["education", "Education"],
  ["certifications", "Certifications"],
];

function DetailList({ title, items, render }) {
  return (
    <section className="resume-parser-detail">
      <h3>{title}</h3>
      {items.length ? (
        <div className="resume-parser-items">
          {items.map((item, index) => (
            <article key={`${title}-${index}`}>{render(item)}</article>
          ))}
        </div>
      ) : <p className="muted">No {title.toLowerCase()} found.</p>}
    </section>
  );
}

export default function ResumeParserPage({
  onDashboard,
  onProfile,
  onJobMatching,
  onJDAnalysis,
  onLogout,
}) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [parsing, setParsing] = useState(false);

  async function logout() {
    setError("");
    try {
      await request("/api/logout", { method: "POST" });
      onLogout();
    } catch (problem) {
      setError(problem.message);
    }
  }

  async function parseResume(event) {
    event.preventDefault();
    if (!file) return;
    setError("");
    setResult(null);
    setParsing(true);
    try {
      const form = new FormData();
      form.append("resume", file);
      setResult(await request("/api/resume-parser/parse", { method: "POST", body: form }));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setParsing(false);
    }
  }

  function exportJson() {
    const blob = new Blob([`${JSON.stringify(result, null, 2)}\n`], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const basename = (file?.name || "resume").replace(/\.[^.]+$/, "").replace(/[^a-z0-9_-]+/gi, "-");
    anchor.href = url;
    anchor.download = `${basename || "resume"}-details.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <main className="dashboard-page resume-parser-page">
      <BrandHeader>
        <div className="dashboard-nav">
          <button className="nav-link" onClick={onDashboard}>Dashboard</button>
          <button className="nav-link" onClick={onProfile}>Profile</button>
          <button className="nav-link" onClick={onJobMatching}>Job matching</button>
          <button className="nav-link" onClick={onJDAnalysis}>JD analysis</button>
          <span className="nav-link active" aria-current="page">Resume parser</span>
          <button className="logout-button" onClick={logout}>Sign out</button>
        </div>
      </BrandHeader>
      <div className="dashboard-content">
        <section className="dashboard-welcome">
          <div>
            <p className="eyebrow">STRUCTURED RESUME DETAILS</p>
            <h1>Resume parser</h1>
            <p>Upload a resume to extract skills, projects, experience, education, and certifications.</p>
          </div>
        </section>

        <section className="job-match-form-section" aria-labelledby="resume-parser-heading">
          <div className="job-match-section-heading">
            <h2 id="resume-parser-heading">Upload a resume</h2>
            <p>PDF or DOCX, up to 5 MB. This tool shows results without changing your profile.</p>
          </div>
          <form className="resume-parser-form" onSubmit={parseResume}>
            <label className="field">
              <span>Resume file</span>
              <input
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  setResult(null);
                  setError("");
                }}
              />
            </label>
            <p className="job-match-note">
              Professional sections are extracted; personal/contact sections are excluded.
            </p>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary-button" disabled={!file || parsing}>
              {parsing ? "Parsing resume..." : "Extract details"} <span aria-hidden="true">→</span>
            </button>
          </form>
        </section>

        {result && (
          <section className="job-match-results resume-parser-results" aria-live="polite">
            <div className="job-match-section-heading">
              <p className="eyebrow">EXTRACTED DETAILS</p>
              <h2>Resume results</h2>
            </div>
            <DetailList title="Skills" items={result.skills} render={(skill) => <p>{skill}</p>} />
            {detailSections.map(([key, title]) => (
              <DetailList
                key={key}
                title={title}
                items={result[key]}
                render={(item) => {
                  if (key === "projects") return (
                    <>
                      <h4>{item.title || "Project"}</h4>
                      {item.description && <p>{item.description}</p>}
                      {item.tech_stack && <p className="muted">{item.tech_stack}</p>}
                    </>
                  );
                  if (key === "experience") return (
                    <>
                      <h4>{item.job_title || "Experience"}{item.company && ` · ${item.company}`}</h4>
                      {(item.start_date || item.end_date) && (
                        <p className="muted">{[item.start_date, item.end_date || "Present"].filter(Boolean).join(" — ")}</p>
                      )}
                      {item.description && <p>{item.description}</p>}
                    </>
                  );
                  if (key === "education") return (
                    <>
                      <h4>{[item.degree, item.field_of_study].filter(Boolean).join(" · ") || "Education"}</h4>
                      <p>{[item.institution, item.graduation_year, item.grade].filter(Boolean).join(" · ")}</p>
                    </>
                  );
                  return (
                    <>
                      <h4>{item.name || "Certification"}</h4>
                      {item.issuing_organization && <p>{item.issuing_organization}</p>}
                    </>
                  );
                }}
              />
            ))}
            <button className="secondary-button resume-parser-export" onClick={exportJson}>
              Export details as JSON
            </button>
          </section>
        )}
      </div>
      <PageFooter />
    </main>
  );
}
