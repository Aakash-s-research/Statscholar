import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { MODULES, T, mono, sans, serif } from "../styles/theme";

export default function Layout({ mode, setMode, dataset, interpCount = 0, user, onLogout }) {
  const sidebarLabel = dataset ? `${dataset.row_count} rows · ${dataset.filename}` : "No dataset loaded";
  const topBarLabel = dataset
    ? `${dataset.row_count} rows loaded · ${dataset.filename} · ${dataset.columns.length} columns`
    : "no dataset";

  return (
    <div style={{ fontFamily: sans, background: T.paper, color: T.ink, minHeight: "100vh", display: "flex" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        button { font-family: inherit; cursor: pointer; }
      `}</style>

      <div style={{ width: 216, background: T.sidebarGradient, color: "#DCE3EE", flexShrink: 0, display: "flex", flexDirection: "column", padding: "22px 0 16px" }}>
        <div style={{ padding: "0 18px 20px", display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ fontFamily: serif, fontSize: 20, fontWeight: 600, color: "#fff", letterSpacing: "-0.01em" }}>StatScholar</div>
          <div style={{ fontSize: 11.5, color: "#93A2BE", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={sidebarLabel}>
            {sidebarLabel}
          </div>
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {MODULES.map((m, i) => (
            <NavLink
              key={m.id}
              to={m.path}
              end={m.path === "/"}
              style={({ isActive }) => ({
                display: "flex", alignItems: "center", gap: 9,
                padding: "9px 14px", fontSize: 13, textDecoration: "none",
                background: isActive ? "rgba(255,255,255,0.08)" : "transparent",
                borderLeft: isActive ? `3px solid ${T.teal}` : "3px solid transparent",
                color: isActive ? "#fff" : "#B9C2D4",
                fontWeight: isActive ? 500 : 400,
              })}
            >
              <span style={{ fontFamily: mono, fontSize: 10.5, color: "#7B8AA8", width: 13, flex: "0 0 auto" }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ minWidth: 0 }}>{m.label}</span>
              {m.id === "trend" && <span style={{ marginLeft: "auto", color: "#8FC4BE", fontSize: 11 }}>★</span>}
            </NavLink>
          ))}
        </nav>
        <div style={{ marginTop: "auto", padding: "16px 18px 0", borderTop: "1px solid rgba(255,255,255,0.09)", display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <div style={{ fontSize: 11.5, color: "#93A2BE" }}>This session</div>
            <div style={{ fontFamily: mono, fontSize: 11.5 }}>{interpCount} interpretation{interpCount !== 1 ? "s" : ""}</div>
          </div>
          {user && (
            <div style={{ borderTop: "1px solid rgba(255,255,255,0.09)", paddingTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ fontSize: 11.5, color: "#B9C2D4", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={user.email}>
                {user.email}
              </div>
              <button
                onClick={onLogout}
                style={{ background: "transparent", border: "1px solid rgba(255,255,255,0.25)", color: "#DCE3EE", padding: "5px 0", fontSize: 11.5 }}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div
          style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 30px", borderBottom: `1px solid ${T.line}`, background: T.surface,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: T.teal, flex: "0 0 auto" }} />
            <span style={{ fontFamily: mono, fontSize: 12.5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {topBarLabel}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 11, flex: "0 0 auto" }}>
            <span style={{ fontSize: 12.5, color: T.slate, whiteSpace: "nowrap" }}>Explain results for</span>
            <div style={{ display: "flex", border: `1px solid ${T.line}` }}>
              {["student", "research"].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  style={{
                    border: "none", padding: "7px 15px", fontSize: 13, fontWeight: 500,
                    background: mode === m ? T.teal : "#fff", color: mode === m ? "#fff" : T.ink,
                  }}
                >
                  {m === "student" ? "Student" : "Research"}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div style={{ padding: "30px", maxWidth: 1200, width: "100%" }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
