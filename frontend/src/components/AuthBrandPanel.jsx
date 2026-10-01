import React from "react";
import { MODULES, T, mono, serif } from "../styles/theme";

const FEATURES = [
  "Six Mann-Kendall family trend tests",
  "Correlation, regression, and full diagnostics",
  "Real charts and tables embedded in every export",
  "Plain-language or research-style, your choice",
];

export default function AuthBrandPanel() {
  return (
    <div
      style={{
        width: "42%", minWidth: 340, background: T.sidebarGradient, color: "#fff",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
        padding: "48px 44px",
      }}
    >
      <div>
        <div style={{ fontFamily: serif, fontSize: 26, fontWeight: 600 }}>StatScholar</div>
        <div style={{ fontSize: 13.5, color: "#B9C2D4", marginTop: 8, lineHeight: 1.6, maxWidth: 320 }}>
          A general-purpose statistical analysis platform anchored by a complete Mann-Kendall trend-analysis suite.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {FEATURES.map((f) => (
          <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <span style={{ color: "#8FC4BE", fontFamily: mono, fontSize: 13, marginTop: 1 }}>✓</span>
            <span style={{ fontSize: 13.5, color: "#DCE3EE", lineHeight: 1.5 }}>{f}</span>
          </div>
        ))}
      </div>

     <div style={{ display: "flex", flexDirection: "column", gap: 6 }}> <div style={{ fontFamily: mono, fontSize: 11, color: "#7B8AA8" }}> {MODULES.length - 1} modules · data preparation to finished report </div> <div style={{ fontSize: 10.5, color: "#5F7089", lineHeight: 1.5, marginTop: 4 }}> © {new Date().getFullYear()} Aakash S<br /> PhD Scholar, Soil and Water Conservation Engineering<br /> Tamil Nadu Agricultural University </div> </div> </div> ); }
    
