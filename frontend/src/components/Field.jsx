export function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  required = false,
  ...props
}) {
  return (
    <label className="field">
      <span>{label}{required && <b> *</b>}</span>
      <input
        type={type}
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        {...props}
      />
    </label>
  );
}

export function TextArea({ label, value, onChange, placeholder = "" }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        value={value || ""}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows="3"
      />
    </label>
  );
}

export function Section({ title, hint, children }) {
  return (
    <section className="form-section">
      <div className="section-heading">
        <h2>{title}</h2>
        {hint && <p>{hint}</p>}
      </div>
      {children}
    </section>
  );
}
