import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmail } from "../api/client";
import { T, serif } from "../styles/theme";

export default function VerifyEmail({ onVerified }) {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [status, setStatus] = useState("pending"); // pending | success | error
  const [error, setError] = useState(null);
  const hasRun = useRef(false);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("This link is missing its verification token.");
      return;
    }
    // React 18 StrictMode intentionally runs effects twice in development
    // to surface side-effect bugs. Without this guard, that means calling
    // a single-use verification token twice — the first call succeeds and
    // consumes it, the second fails, and whichever resolves last wins the
    // displayed state. This ref makes the actual API call fire only once
    // regardless of how many times the effect itself runs.
    if (hasRun.current) return;
    hasRun.current = true;

    verifyEmail(token)
      .then(() => {
        setStatus("success");
        if (onVerified) onVerified();
      })
      .catch((err) => {
        setStatus("error");
        setError(err?.response?.data?.detail || "Verification failed — the link may be invalid or expired.");
      });
  }, [token]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: T.paper }}>
      <div style={{ background: "#fff", border: `1px solid ${T.line}`, padding: "32px 36px", width: 380, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontFamily: serif, fontSize: 24, fontWeight: 600, color: T.ink }}>StatScholar</div>
        {status === "pending" && <div style={{ fontSize: 13.5, color: T.slate }}>Verifying…</div>}
        {status === "success" && <div style={{ fontSize: 13.5 }}>Your email has been verified.</div>}
        {status === "error" && <div style={{ fontSize: 13.5, color: T.amber }}>{error}</div>}
        <Link to="/" style={{ color: T.teal, fontSize: 13 }}>Go to StatScholar</Link>
      </div>
    </div>
  );
}
