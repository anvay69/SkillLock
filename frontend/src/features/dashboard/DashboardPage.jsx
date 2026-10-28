import { useState } from "react";
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

export default function DashboardPage({ user, extractedAdded, onProfile, onLogout }) {
  const [error, setError] = useState("");

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
            <span className="section-count">02</span>
          </div>
          <PlaceholderCards items={placeholders.assessments} />
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
