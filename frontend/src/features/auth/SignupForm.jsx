import { useEffect, useState } from "react";
import { request } from "../../api/client";
import { Field, Section, TextArea } from "../../components/Field";
import { emptyProfile, profileSections } from "./profileDefaults";

function ProfileBasics({ profile, set, uploads, onUploads }) {
  return (
    <Section title="The basics" hint="Start with the details people will recognize.">
      <div className="form-grid">
        <Field label="Full name" value={profile.name} onChange={(value) => set("name", value)} placeholder="Your name" required />
        <Field label="Username" value={profile.username} onChange={(value) => set("username", value)} placeholder="yourname" required />
        <Field label="Email address" type="email" value={profile.email} onChange={(value) => set("email", value)} placeholder="you@example.com" required />
        <Field label="Password" type="password" value={profile.password} onChange={(value) => set("password", value)} placeholder="Choose a password" required minLength="8" />
      </div>
      <TextArea label="A little about you" value={profile.bio} onChange={(value) => set("bio", value)} placeholder="What are you curious about or working on?" />
      <div className="form-grid">
        <Field label="GitHub" value={profile.github_url} onChange={(value) => set("github_url", value)} placeholder="https://github.com/you" />
        <Field label="LinkedIn" value={profile.linkedin_url} onChange={(value) => set("linkedin_url", value)} placeholder="https://linkedin.com/in/you" />
      </div>
      <div className="form-grid upload-grid">
        <label className="field">
          <span>Profile picture</span>
          <input type="file" accept="image/*" onChange={(event) => onUploads({ ...uploads, profilePicture: event.target.files[0] || null })} />
        </label>
        <label className="field">
          <span>Resume</span>
          <input type="file" accept=".pdf,.docx" onChange={(event) => onUploads({ ...uploads, resume: event.target.files[0] || null })} />
        </label>
      </div>
      <p className="muted resume-privacy-note">
        Resume extraction sends only professional sections and profile details (skills, projects, experience, education, and certifications) to Gemini. Personal/contact details and profile links are excluded.
      </p>
    </Section>
  );
}

function SkillsPicker({ skills, selected, onChange }) {
  const [input, setInput] = useState("");

  function addSkill(value = input) {
    const skill = value.trim();
    if (skill && !selected.some((item) => item.toLowerCase() === skill.toLowerCase())) {
      onChange([...selected, skill]);
    }
    setInput("");
  }

  return (
    <Section title="Skills" hint="Pick from the list or add your own.">
      <div className="skill-picker">
        {skills.map((skill) => (
          <button
            type="button"
            className={`skill-option ${selected.includes(skill) ? "selected" : ""}`}
            key={skill}
            onClick={() => onChange(selected.includes(skill) ? selected.filter((item) => item !== skill) : [...selected, skill])}
          >
            {skill}
          </button>
        ))}
      </div>
      <div className="inline-input">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addSkill();
            }
          }}
          placeholder="Add another skill..."
        />
        <button type="button" className="small-button" onClick={() => addSkill()}>Add</button>
      </div>
      {selected.length > 0 && (
        <div className="tags">
          {selected.map((skill) => (
            <span className="tag" key={skill}>
              {skill}
              <button type="button" aria-label={`Remove ${skill}`} onClick={() => onChange(selected.filter((item) => item !== skill))}>×</button>
            </span>
          ))}
        </div>
      )}
    </Section>
  );
}

function RepeatableSection({ config, items, onChange }) {
  function update(index, key, value) {
    onChange(items.map((item, position) => position === index ? { ...item, [key]: value } : item));
  }

  return (
    <Section title={config.title} hint={config.hint}>
      {items.map((item, index) => (
        <div className="repeat-card" key={index}>
          <button type="button" className="remove-button" onClick={() => onChange(items.filter((_, position) => position !== index))}>Remove</button>
          <div className="form-grid">
            {config.fields.map((field) => {
              const Component = field.multiline ? TextArea : Field;
              return (
                <Component
                  key={field.key}
                  label={field.label}
                  type={field.type}
                  value={item[field.key]}
                  onChange={(value) => update(index, field.key, value)}
                  placeholder={field.placeholder}
                />
              );
            })}
          </div>
        </div>
      ))}
      <button
        type="button"
        className="add-button"
        onClick={() => onChange([...items, Object.fromEntries(config.fields.map((field) => [field.key, ""]))])}
      >
        + Add {config.addLabel}
      </button>
    </Section>
  );
}

export default function SignupForm({ onSignup }) {
  const [profile, setProfile] = useState(emptyProfile);
  const [password, setPassword] = useState("");
  const [skills, setSkills] = useState([]);
  const [uploads, setUploads] = useState({ profilePicture: null, resume: null });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    request("/api/skills").then(setSkills).catch(() => {});
  }, []);

  function set(key, value) {
    if (key === "password") {
      setPassword(value);
      return;
    }
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function setSection(key, value) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("profile", JSON.stringify(profile));
      form.append("password", password);
      if (uploads.profilePicture) form.append("profile_picture", uploads.profilePicture);
      if (uploads.resume) form.append("resume", uploads.resume);
      onSignup(await request("/api/signup", { method: "POST", body: form }));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="signup-form">
      <ProfileBasics profile={{ ...profile, password }} set={set} uploads={uploads} onUploads={setUploads} />
      <SkillsPicker skills={skills} selected={profile.skills} onChange={(value) => setSection("skills", value)} />
      {profileSections.map((section) => (
        <RepeatableSection
          key={section.key}
          config={section}
          items={profile[section.key]}
          onChange={(value) => setSection(section.key, value)}
        />
      ))}
      {error && <p className="error">{error}</p>}
      <button className="primary-button" disabled={busy}>
        {busy ? "Creating your profile..." : "Create your profile"} <span>→</span>
      </button>
    </form>
  );
}
