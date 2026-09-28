import React, { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/client";
import { T, serif } from "../styles/theme";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
    } finally {
      // Always show the same confirmation, whether or not the email is
      // registered — the backend deliberately doesn't reveal that either.
      setSubmitted(true);
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: T.paper }}>
      <div style={{ background: "#fff", border: `1px solid ${T.line}`, padding: "32px 36px", width: 380, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: serif, fontSize: 24, fontWeight: 600, color: T.ink }}>StatScholar</div>

        {submitted ? (
          <>
            <div style={{ fontSize: 13.5, lineHeight: 1.6 }}>
              If <strong>{email}</strong> is registered, a password reset link has been sent. Check your inbox
              (and check your backend terminal if SMTP isn't configured yet — the link is logged there in dev mode).
            </div>
            <Link to="/login" style={{ color: T.teal, fontSize: 13 }}>Back to sign in</Link>
          </>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ fontSize: 13.5, color: T.slate }}>Enter your email and we'll send you a reset link.</div>
            <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 5 }}>
              Email
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                style={{ padding: "8px 10px", border: `1px solid ${T.line}`, fontSize: 13.5 }}
              />
            </label>
            <button
              type="submit" disabled={loading}
              style={{ background: T.ink, color: "#fff", border: "none", padding: "10px 0", fontSize: 13.5 }}
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>
            <div style={{ fontSize: 13, color: T.slate, textAlign: "center" }}>
              <Link to="/login" style={{ color: T.teal }}>Back to sign in</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
