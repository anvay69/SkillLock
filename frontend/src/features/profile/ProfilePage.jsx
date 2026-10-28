import { useState } from "react";
import { request } from "../../api/client";
import { BrandHeader, PageFooter } from "../../components/SiteChrome";
import ExtractionSummary from "./ExtractionSummary";
import ProfileEditForm from "./ProfileEditForm";
import ProfileSection from "./ProfileSection";

function ListSection({ title, items, render }) {
  if (!items?.length) return null;
  return (
    <ProfileSection title={title}>
      <div className="profile-items">
        {items.map((item, index) => (
          <article className="profile-item" key={`${title}-${index}`}>{render(item)}</article>
        ))}
      </div>
    </ProfileSection>
  );
}

export default function ProfilePage({
  user,
  extractedAdded,
  onProfileUpdate,
  onNavigateDashboard,
  onLogout,
}) {
  const [error, setError] = useState("");
  const [resume, setResume] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resumeExtraction, setResumeExtraction] = useState(null);
  const [editing, setEditing] = useState(false);

  async function logout() {
    try {
      await request("/api/logout", { method: "POST" });
      onLogout();
    } catch (problem) {
      setError(problem.message);
    }
  }

  async function uploadResume(event) {
    event.preventDefault();
    if (!resume) return;
    const formElement = event.currentTarget;
    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("resume", resume);
      const result = await request("/api/me/resume", { method: "POST", body: form });
      setResumeExtraction(result.extracted_added);
      onProfileUpdate(result.profile, result.extracted_added);
      setResume(null);
      formElement.reset();
    } catch (problem) {
      setError(problem.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="profile-page">
      <BrandHeader>
        <div className="dashboard-nav">
          <button className="profile-link" onClick={onNavigateDashboard}>Dashboard</button>
          <button className="logout-button" onClick={logout}>Sign out <span>↗</span></button>
        </div>
      </BrandHeader>
      <div className="profile-wrap">
        <div className="profile-cover">
          <span>YOUR PROFESSIONAL STORY</span>
          <div className="cover-mark">S.</div>
        </div>
        <section className="profile-hero">
          {user.profile_picture
            ? <img className="avatar" src={user.profile_picture} alt="" />
            : <div className="avatar avatar-placeholder">{user.name?.slice(0, 1)}</div>}
          <div className="profile-identity">
            <p className="eyebrow">@{user.username}</p>
            <h1>{user.name}</h1>
            <p>{user.email}</p>
          </div>
          <span className="profile-status"><i /> PROFILE</span>
        </section>
        {!editing && (
          <div className="profile-edit-toggle">
            <button className="secondary-button" onClick={() => setEditing(true)}>Edit profile</button>
          </div>
        )}
        {editing && (
          <ProfileEditForm
            user={user}
            onCancel={() => setEditing(false)}
            onSave={(profile) => {
              onProfileUpdate(profile, null);
              setEditing(false);
            }}
          />
        )}
        <div className="profile-content">
          {!editing && user.bio && (
            <ProfileSection title="About">
              <p>{user.bio}</p>
              <div className="profile-links">
                {user.github_url && <a href={user.github_url} target="_blank" rel="noreferrer">GitHub ↗</a>}
                {user.linkedin_url && <a href={user.linkedin_url} target="_blank" rel="noreferrer">LinkedIn ↗</a>}
              </div>
            </ProfileSection>
          )}
          {!editing && <ListSection title="Skills" items={user.skills} render={(skill) => <span className="tag">{skill}</span>} />}
          {!editing && <ListSection title="Projects" items={user.projects} render={(project) => (
            <>
              <h3>{project.title}</h3>
              {project.description && <p>{project.description}</p>}
              {project.tech_stack && <p className="muted">Stack · {project.tech_stack}</p>}
              <div className="profile-links">
                {project.repository_url && <a href={project.repository_url} target="_blank" rel="noreferrer">Repository ↗</a>}
                {project.live_url && <a href={project.live_url} target="_blank" rel="noreferrer">Live project ↗</a>}
              </div>
            </>
          )} />}
          {!editing && <ListSection title="Experience" items={user.experience} render={(item) => (
            <>
              <h3>{item.job_title}{item.company && <span> · {item.company}</span>}</h3>
              <p className="muted">{[item.start_date, item.end_date || (item.start_date && "Present")].filter(Boolean).join(" — ")}</p>
              {item.description && <p>{item.description}</p>}
            </>
          )} />}
          {!editing && <ListSection title="Education" items={user.education} render={(item) => (
            <>
              <h3>{item.degree} · {item.institution}</h3>
              <p>{[item.field_of_study, item.graduation_year, item.grade].filter(Boolean).join(" · ")}</p>
            </>
          )} />}
          {!editing && <ListSection title="Certifications" items={user.certifications} render={(item) => (
            <>
              <h3>{item.name}</h3>
              {item.issuing_organization && <p>{item.issuing_organization}</p>}
              {item.credential_url && <a href={item.credential_url} target="_blank" rel="noreferrer">View credential ↗</a>}
            </>
          )} />}
          {!editing && (
          <ProfileSection title="Resume">
            {user.resume && <a href={user.resume} target="_blank" rel="noreferrer" className="resume-link">View uploaded resume ↗</a>}
            <form className="resume-upload" onSubmit={uploadResume}>
              <label className="field">
                <span>{user.resume ? "Replace resume" : "Upload a resume"}</span>
                <input
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={(event) => setResume(event.target.files[0] || null)}
                />
              </label>
              <button className="primary-button" disabled={!resume || uploading}>
                {uploading ? "Reading resume..." : "Upload and update profile"} <span>→</span>
              </button>
            </form>
          </ProfileSection>
          )}
          {!editing && <ExtractionSummary extracted={resumeExtraction || extractedAdded} />}
          {!editing && !user.bio && !user.skills?.length && !user.projects?.length && (
            <p className="muted">Your profile is ready. Add details to tell your story.</p>
          )}
        </div>
        {!editing && <div className="profile-note"><span>✳</span> Keep your professional story up to date.</div>}
        {error && <p className="error">{error}</p>}
      </div>
      <PageFooter />
    </main>
  );
}
