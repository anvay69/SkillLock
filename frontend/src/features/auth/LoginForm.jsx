import { useState } from "react";
import { request } from "../../api/client";
import { Field } from "../../components/Field";

export default function LoginForm({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await request("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      onLogin(user);
    } catch (problem) {
      setError(problem.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={submit} className="login-form">
        <Field label="Email address" type="email" value={email} onChange={setEmail} placeholder="you@example.com" required />
        <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="Enter your password" required />
        {error && <p className="error">{error}</p>}
        <button className="primary-button" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"} <span>→</span>
        </button>
      </form>
      <div className="demo-hint">
        <span className="demo-mark">i</span>
        <p><strong>Just looking around?</strong><br />Try alex@example.com · SkillLockDemo2026!</p>
      </div>
    </>
  );
}
