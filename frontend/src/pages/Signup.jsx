import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register, setStoredToken } from "../api/client";
import AuthBrandPanel from "../components/AuthBrandPanel";
import { T, serif } from "../styles/theme";

export default function Signup({ onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await register(email, password);
      setStoredToken(data.access_token);
      onAuthenticated(data.user);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Sign up failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex" }}>
      <AuthBrandPanel />

      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: T.paper }}>
        <form onSubmit={handleSubmit} style={{ width: 360, display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <div style={{ fontFamily: serif, fontSize: 24, fontWeight: 600, color: T.ink }}>Create your account</div>
            <div style={{ fontSize: 13.5, color: T.slate, marginTop: 4 }}>Start analyzing your data in minutes</div>
          </div>

          <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 5 }}>
            Email
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              style={{ padding: "9px 11px", border: `1px solid ${T.line}`, fontSize: 13.5, borderRadius: 4 }}
            />
          </label>
          <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 5 }}>
            Password
            <input
              type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
              style={{ padding: "9px 11px", border: `1px solid ${T.line}`, fontSize: 13.5, borderRadius: 4 }}
            />
            <span style={{ fontSize: 11.5, color: T.slate }}>At least 8 characters</span>
          </label>

          {error && (
            <div style={{ background: T.amberSoft, borderLeft: `3px solid ${T.amber}`, padding: "8px 12px", fontSize: 13, color: "#7A4C1D" }}>
              {error}
            </div>
          )}

          <button
            type="submit" disabled={loading}
            style={{ background: T.teal, color: "#fff", border: "none", padding: "11px 0", fontSize: 13.5, fontWeight: 500, borderRadius: 4, marginTop: 4 }}
          >
            {loading ? "Creating account…" : "Create account"}
          </button>

          <div style={{ fontSize: 13, color: T.slate, textAlign: "center" }}>
            Already have an account? <Link to="/login" style={{ color: T.teal, fontWeight: 500 }}>Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
