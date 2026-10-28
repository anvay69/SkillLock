import { useEffect, useState } from "react";
import { request } from "../../api/client";
import { Field, Section, TextArea } from "../../components/Field";
import { profileSections } from "../auth/profileDefaults";

function SkillEditor({ selected, onChange }) {
  const [available, setAvailable] = useState([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    request("/api/skills").then(setAvailable).catch(() => {});
  }, []);

  function addSkill(value = input) {
    const skill = value.trim();
    if (skill && !selected.some((item) => item.toLowerCase() === skill.toLowerCase())) {
      onChange([...selected, skill]);
    }
    setInput("");
  }

  return (
    <Section title="Skills" hint="Add or remove skill tags.">
      <div className="skill-picker">
        {available.map((skill) => (
          <button
            type="button"
            className={`skill-option ${selected.some((item) => item.toLowerCase() === skill.toLowerCase()) ? "selected" : ""}`}
            key={skill}
            onClick={() => selected.some((item) => item.toLowerCase() === skill.toLowerCase())
              ? onChange(selected.filter((item) => item.toLowerCase() !== skill.toLowerCase()))
              : addSkill(skill)}
          >{skill}</button>
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
      {!!selected.length && (
        <div className="tags">
          {selected.map((skill) => (
            <span className="tag" key={skill}>
              {skill}
              <button
                type="button"
                aria-label={`Remove ${skill}`}
                onClick={() => onChange(selected.filter((item) => item !== skill))}
              >×</button>
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
        <div className="repeat-card" key={`${config.key}-${index}`}>
          <button
            type="button"
            className="remove-button"
            onClick={() => onChange(items.filter((_, position) => position !== index))}
          >Remove</button>
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
      >+ Add {config.addLabel}</button>
    </Section>
  );
}

export default function ProfileEditForm({ user, onSave, onCancel }) {
  const [profile, setProfile] = useState({
    ...user,
    skills: [...(user.skills || [])],
    projects: [...(user.projects || [])],
    experience: [...(user.experience || [])],
    education: [...(user.education || [])],
    certifications: [...(user.certifications || [])],
  });
  const [profilePicture, setProfilePicture] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(key, value) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("profile", JSON.stringify(profile));
      if (profilePicture) form.append("profile_picture", profilePicture);
      onSave(await request("/api/me", { method: "PUT", body: form }));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="profile-edit-form" onSubmit={submit}>
      <Section title="The basics">
        <div className="form-grid">
          <Field label="Full name" value={profile.name} onChange={(value) => set("name", value)} required />
          <Field label="Username" value={profile.username} onChange={(value) => set("username", value)} required />
        </div>
        <TextArea label="A little about you" value={profile.bio} onChange={(value) => set("bio", value)} />
        <div className="form-grid">
          <Field label="GitHub" value={profile.github_url} onChange={(value) => set("github_url", value)} placeholder="https://github.com/you" />
          <Field label="LinkedIn" value={profile.linkedin_url} onChange={(value) => set("linkedin_url", value)} placeholder="https://linkedin.com/in/you" />
        </div>
        <label className="field">
          <span>Profile picture</span>
          <input type="file" accept="image/*" onChange={(event) => setProfilePicture(event.target.files[0] || null)} />
          {profile.profile_picture && !profilePicture && <span>Current picture will be kept unless replaced.</span>}
        </label>
      </Section>
      <SkillEditor selected={profile.skills} onChange={(value) => set("skills", value)} />
      {profileSections.map((section) => (
        <RepeatableSection
          key={section.key}
          config={section}
          items={profile[section.key] || []}
          onChange={(value) => set(section.key, value)}
        />
      ))}
      {error && <p className="error">{error}</p>}
      <div className="profile-edit-actions">
        <button type="button" className="secondary-button" disabled={busy} onClick={onCancel}>Cancel</button>
        <button className="primary-button" disabled={busy}>
          {busy ? "Saving..." : "Save changes"} <span>→</span>
        </button>
      </div>
    </form>
  );
}
