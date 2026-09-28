import React, { useState } from "react";
import { fetchCurrentUser, resendVerification } from "../api/client";
import { T, serif } from "../styles/theme";

export default function VerifyPending({ user, onUserUpdated, onLogout }) {
  const [resendStatus, setResendStatus] = useState(null); // null | "sending" | "sent" | "error"
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState(null);

  async function handleResend() {
    setResendStatus("sending");
    try {
      await resendVerification();
      setResendStatus("sent");
    } catch {
      setResendStatus("error");
    }
  }

  async function handleCheckAgain() {
    setChecking(true);
    setCheckError(null);
    try {
      const fresh = await fetchCurrentUser();
      if (fresh.is_verified) {
        onUserUpdated(fresh);
      } else {
        setCheckError("Still not verified — click the link in your email first, then try again.");
      }
    } catch {
      setCheckError("Couldn't check your status. Try again in a moment.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: T.paper }}>
      <div style={{ background: "#fff", border: `1px solid ${T.line}`, padding: "32px 36px", width: 420, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: serif, fontSize: 24, fontWeight: 600, color: T.ink }}>StatScholar</div>
        <div style={{ fontSize: 14.5, lineHeight: 1.6 }}>
          We sent a verification link to <strong>{user.email}</strong>. Click it, then come back here
          and press "I've verified — continue."
        </div>
        <div style={{ fontSize: 12.5, color: T.slate, lineHeight: 1.6 }}>
          If your backend isn't set up to send real email yet, check its terminal/log output —
          the link is printed there instead.
        </div>

        {checkError && (
          <div style={{ background: T.amberSoft, borderLeft: `3px solid ${T.amber}`, padding: "8px 12px", fontSize: 13, color: "#7A4C1D" }}>
            {checkError}
          </div>
        )}

        <button
          onClick={handleCheckAgain}
          disabled={checking}
          style={{ background: T.teal, color: "#fff", border: "none", padding: "10px 0", fontSize: 13.5, fontWeight: 500, borderRadius: 4 }}
        >
          {checking ? "Checking…" : "I've verified — continue"}
        </button>

        <button
          onClick={handleResend}
          disabled={resendStatus === "sending"}
          style={{ background: "#fff", color: T.ink, border: `1px solid ${T.line}`, padding: "9px 0", fontSize: 13, borderRadius: 4 }}
        >
          {resendStatus === "sending" ? "Sending…" : resendStatus === "sent" ? "Sent — check again" : "Resend verification email"}
        </button>

        <button
          onClick={onLogout}
          style={{ background: "none", color: T.slate, border: "none", fontSize: 12.5, textDecoration: "underline", padding: 0, alignSelf: "center" }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
