// ============================================================
// components/LoginPage.jsx  (Tahap Auth 1)
// Layar login sebelum masuk dashboard.
// Kalau berhasil, memanggil onLogin(user) milik App.jsx.
// ============================================================

import { useState } from "react";
import { login } from "../services/api";

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault(); // jangan reload halaman saat submit form
    setError("");
    setLoading(true);

    try {
      const user = await login(username, password);
      onLogin(user);
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <div className="brand-logo">CV</div>
          <div>
            <div className="brand-title">ComVis Monitor</div>
            <div className="brand-sub">PUSDATIN &middot; Employee Detection</div>
          </div>
        </div>

        <label className="login-label" htmlFor="username">Username</label>
        <input
          id="username"
          className="login-input"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoFocus
        />

        <label className="login-label" htmlFor="password">Password</label>
        <input
          id="password"
          className="login-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />

        {error && <div className="login-error">{error}</div>}

        <button className="login-btn" type="submit" disabled={loading}>
          {loading ? "Checking..." : "Sign in"}
        </button>

        <div className="login-note">
          Dashboard access requires an account. Contact a super admin to register.
        </div>
      </form>
    </div>
  );
}

export default LoginPage;