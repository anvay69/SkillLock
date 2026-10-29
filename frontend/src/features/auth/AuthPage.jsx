import { BrandHeader, PageFooter } from "../../components/SiteChrome";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";

export default function AuthPage({ mode, onModeChange, onLogin }) {
  const isSignup = mode === "signup";

  return (
    <main className="page-shell">
      <BrandHeader>
        <span className="top-note">A clearer picture of your potential</span>
      </BrandHeader>
      <div className={`auth-layout ${isSignup ? "signup-layout" : ""}`}>
        <aside className="intro">
          <div className="eyebrow"><span className="eyebrow-dot" /> YOUR CAREER, IN FOCUS</div>
          <h1>Make your skills<br />speak for <em>you.</em></h1>
          <p>One place for the work, experience, and details that make your professional story yours.</p>
          <ul className="intro-features">
            <li>Bring your experience and skills into one profile.</li>
            <li>Practice with focused, timed assessments.</li>
            <li>Keep your progress and professional details together.</li>
          </ul>
        </aside>
        <section className="auth-card">
          <div className="auth-card-heading">
            <p className="eyebrow">{isSignup ? "A GOOD PLACE TO START" : "WELCOME BACK"}</p>
            <h2>{isSignup ? "Create your profile" : "Pick up where you left off"}</h2>
            <p>{isSignup
              ? "A few details now. The rest of your story, whenever you're ready."
              : "Your professional story is right where you left it."}</p>
          </div>
          {isSignup
            ? <SignupForm onSignup={(result) => onLogin(result.profile, result.extracted_added)} />
            : <LoginForm onLogin={onLogin} />}
          <div className="mode-toggle">
            {isSignup ? "Already have an account? " : "New to SkillLock? "}
            <button onClick={() => onModeChange(isSignup ? "login" : "signup")}>
              {isSignup ? "Sign in" : "Create an account"} <span>→</span>
            </button>
          </div>
        </section>
      </div>
      <PageFooter />
    </main>
  );
}
