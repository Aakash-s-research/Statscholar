import React, { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { clearStoredToken, fetchCurrentUser, getStoredToken } from "./api/client";
import Layout from "./components/Layout";
import Correlation from "./pages/Correlation";
import Dashboard from "./pages/Dashboard";
import DataPrep from "./pages/DataPrep";
import Descriptive from "./pages/Descriptive";
import ForgotPassword from "./pages/ForgotPassword";
import InterpretationLog from "./pages/InterpretationLog";
import Login from "./pages/Login";
import Regression from "./pages/Regression";
import ReportGeneration from "./pages/ReportGeneration";
import ResetPassword from "./pages/ResetPassword";
import Signup from "./pages/Signup";
import TrendAnalysis from "./pages/TrendAnalysis";
import VerifyEmail from "./pages/VerifyEmail";
import VerifyPending from "./pages/VerifyPending";
import Visualization from "./pages/Visualization";

export default function App() {
  const [mode, setMode] = useState("student");
  const [dataset, setDataset] = useState(null);
  const [log, setLog] = useState([]);
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  // On first load, if a token is already stored (from a previous session),
  // validate it against the backend rather than trusting it blindly — an
  // expired or revoked token should send the user back to login, not into
  // a broken app.
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setAuthChecked(true);
      return;
    }
    fetchCurrentUser()
      .then((u) => setUser(u))
      .catch(() => clearStoredToken())
      .finally(() => setAuthChecked(true));
  }, []);

  // If a request anywhere in the app comes back 401 mid-session (token
  // expired), client.js dispatches this event — drop back to a logged-out
  // state so the user sees the login screen instead of silent broken requests.
  useEffect(() => {
    function handleAuthExpired() {
      setUser(null);
      setDataset(null);
      setLog([]);
    }
    window.addEventListener("statscholar:auth-expired", handleAuthExpired);
    return () => window.removeEventListener("statscholar:auth-expired", handleAuthExpired);
  }, []);

  function handleLogout() {
    clearStoredToken();
    setUser(null);
    setDataset(null);
    setLog([]);
  }

  // `raw` carries the underlying statistics object (not just the prose
  // interpretation) so Report Generation's Appendix section can show
  // real numbers, not just repeat the narrative text.
  function addToLog(module, studentText, researchText, raw) {
    setLog((prev) => [...prev, { module, studentText, researchText, raw }]);
  }

  if (!authChecked) {
    return null; // brief blank frame while validating a stored token — avoids a login-screen flash for an already-valid session
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <Login onAuthenticated={setUser} />} />
      <Route path="/signup" element={user ? <Navigate to="/" /> : <Signup onAuthenticated={setUser} />} />

      {/* Reachable regardless of login state — these come from an emailed
          link, which the person may open in a browser where they aren't
          (or no longer are) signed in. */}
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/verify-email" element={<VerifyEmail onVerified={() => setUser((prev) => (prev ? { ...prev, is_verified: true } : prev))} />} />

      {!user ? (
        <Route path="*" element={<Navigate to="/login" />} />
      ) : !user.is_verified ? (
        <Route path="*" element={<VerifyPending user={user} onUserUpdated={setUser} onLogout={handleLogout} />} />
      ) : (
        <Route element={<Layout mode={mode} setMode={setMode} dataset={dataset} interpCount={log.length} user={user} onLogout={handleLogout} />}>
          <Route path="/" element={<Dashboard dataset={dataset} onDatasetLoaded={setDataset} />} />
          <Route path="/prep" element={<DataPrep dataset={dataset} />} />
          <Route path="/descriptive" element={<Descriptive dataset={dataset} />} />
          <Route path="/trend" element={<TrendAnalysis mode={mode} dataset={dataset} addToLog={addToLog} />} />
          <Route path="/correlation" element={<Correlation mode={mode} dataset={dataset} addToLog={addToLog} />} />
          <Route path="/regression" element={<Regression mode={mode} dataset={dataset} addToLog={addToLog} />} />
          <Route path="/visualization" element={<Visualization dataset={dataset} addToLog={addToLog} />} />
          <Route path="/interpretation" element={<InterpretationLog mode={mode} log={log} />} />
          <Route path="/report" element={<ReportGeneration mode={mode} log={log} dataset={dataset} />} />
        </Route>
      )}
    </Routes>
  );
}
