const sections = [
  ["skills", "Skills"],
  ["projects", "Projects"],
  ["experience", "Experience"],
  ["education", "Education"],
  ["certifications", "Certifications"],
];

export default function ExtractionSummary({ extracted, title = "Added from your resume" }) {
  const hasItems = sections.some(([key]) => extracted?.[key]?.length);
  if (!hasItems) return null;

  return (
    <section className="extraction-summary">
      <h2>{title}</h2>
      <p>These details were added to your profile:</p>
      {sections.map(([key, label]) => extracted[key]?.length > 0 && (
        <div className="extracted-row" key={key}>
          <strong>{label}</strong>
          <span>{extracted[key].map((item) => typeof item === "string"
            ? item
            : item.title || item.job_title || item.degree || item.name).join(", ")}</span>
        </div>
      ))}
    </section>
  );
}
