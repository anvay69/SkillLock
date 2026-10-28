import { useEffect, useState } from "react";
import { request } from "./api/client";
import AuthPage from "./features/auth/AuthPage";
import AssessmentPage from "./features/assessments/AssessmentPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import ProfilePage from "./features/profile/ProfilePage";

export default function App() {
  const [user, setUser] = useState(null);
  const [mode, setMode] = useState("login");
  const [page, setPage] = useState("dashboard");
  const [assessmentId, setAssessmentId] = useState(null);
  const [extractedAdded, setExtractedAdded] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    request("/api/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function signIn(candidate, extracted = null) {
    setUser(candidate);
    setExtractedAdded(extracted);
    setPage("dashboard");
  }

  function signOut() {
    setUser(null);
    setExtractedAdded(null);
    setMode("login");
    setPage("dashboard");
    setAssessmentId(null);
  }

  if (loading) return <main className="loading-page">Loading SkillLock...</main>;
  if (!user) return <AuthPage mode={mode} onModeChange={setMode} onLogin={signIn} />;
  if (page === "profile") {
    return (
      <ProfilePage
        user={user}
        extractedAdded={extractedAdded}
        onProfileUpdate={(candidate, extracted) => {
          setUser(candidate);
          setExtractedAdded(extracted);
        }}
        onNavigateDashboard={() => setPage("dashboard")}
        onLogout={signOut}
      />
    );
  }
  if (page === "assessment" && assessmentId) {
    return <AssessmentPage assessmentId={assessmentId} onDashboard={() => setPage("dashboard")} />;
  }
  return (
    <DashboardPage
      user={user}
      extractedAdded={extractedAdded}
      onProfile={() => setPage("profile")}
      onAssessment={(id) => {
        setAssessmentId(id);
        setPage("assessment");
      }}
      onLogout={signOut}
    />
  );
}
