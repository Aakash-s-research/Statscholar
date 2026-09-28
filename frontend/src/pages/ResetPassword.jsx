import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api/client";
import { T, serif } from "../styles/theme";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "Reset failed — the link may be invalid or expired.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: T.paper }}>
      <div style={{ background: "#fff", border: `1px solid ${T.line}`, padding: "32px 36px", width: 380, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: serif, fontSize: 24, fontWeight: 600, color: T.ink }}>StatScholar</div>

        {!token ? (
          <div style={{ color: T.amber, fontSize: 13.5 }}>
            This link is missing its reset token. Use the link from your email, or{" "}
            <Link to="/forgot-password" style={{ color: T.teal }}>request a new one</Link>.
          </div>
        ) : done ? (
          <>
            <div style={{ fontSize: 13.5 }}>Your password has been reset.</div>
            <button
              onClick={() => navigate("/login")}
              style={{ background: T.ink, color: "#fff", border: "none", padding: "10px 0", fontSize: 13.5 }}
            >
              Sign in
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ fontSize: 13.5, color: T.slate }}>Choose a new password.</div>
            <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 5 }}>
              New password
              <input
                type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
                style={{ padding: "8px 10px", border: `1px solid ${T.line}`, fontSize: 13.5 }}
              />
              <span style={{ fontSize: 11.5, color: T.slate }}>At least 8 characters</span>
            </label>
            {error && <div style={{ color: T.amber, fontSize: 13 }}>{error}</div>}
            <button
              type="submit" disabled={loading}
              style={{ background: T.ink, color: "#fff", border: "none", padding: "10px 0", fontSize: 13.5 }}
            >
              {loading ? "Resetting…" : "Reset password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
