import React from "react";
import { T, mono, sans, serif } from "../styles/theme";

export function Heading({ children, sub }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <h1 style={{ fontFamily: serif, fontSize: 26, fontWeight: 600, margin: 0 }}>{children}</h1>
      {sub && <p style={{ color: T.slate, fontSize: 14, marginTop: 6, maxWidth: 560 }}>{sub}</p>}
    </div>
  );
}

export function Card({ children, style }) {
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.line}`, borderRadius: 8, padding: 22, ...style }}>
      {children}
    </div>
  );
}

export function StatTable({ rows }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: mono, fontSize: 13 }}>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k} style={{ borderBottom: `1px solid ${T.line}` }}>
            <td style={{ padding: "8px 0", color: T.slate, fontFamily: sans }}>{k}</td>
            <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 500 }}>{String(v)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function InterpretationBox({ mode, studentText, researchText, flags = [] }) {
  return (
    <div>
      <div
        style={{
          background: T.tealSoft,
          borderLeft: `3px solid ${T.teal}`,
          padding: "14px 18px",
          borderRadius: 4,
          fontFamily: serif,
          fontSize: 15,
          lineHeight: 1.6,
        }}
      >
        {mode === "student" ? studentText : researchText}
      </div>
      {flags.map((flag, i) => (
        <div
          key={i}
          style={{
            marginTop: 10,
            background: T.amberSoft,
            borderLeft: `3px solid ${T.amber}`,
            padding: "10px 16px",
            borderRadius: 4,
            fontSize: 13,
            color: "#7A4A1B",
          }}
        >
          {flag}
        </div>
      ))}
    </div>
  );
}
