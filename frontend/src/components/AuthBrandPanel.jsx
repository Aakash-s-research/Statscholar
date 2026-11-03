import React from "react";
import { MODULES, T, mono, serif } from "../styles/theme";

const FEATURES = [
  "Six Mann-Kendall family trend tests",
  "Correlation, regression, and full diagnostics",
  "Real charts and tables embedded in every export",
  "Plain-language or research-style, your choice",
];

// Scattered "raw data" points: [x, y, radius, opacity]
const RAW_DOTS = [
  [75, 98, 3, 0.51],
  [120, 64, 3.5, 0.52],
  [93, 63, 3, 0.46],
  [34, 120, 3.5, 0.57],
  [91, 83, 3, 0.58],
  [93, 60, 2.5, 0.64],
  [31, 49, 2.5, 0.56],
  [111, 76, 3.5, 0.64],
  [82, 105, 3, 0.35],
  [34, 106, 3, 0.7],
  [136, 123, 3.5, 0.44],
  [109, 93, 2.5, 0.37],
  [110, 83, 3, 0.49],
  [131, 124, 2.5, 0.42],
  [128, 51, 3, 0.69],
  [69, 53, 3.5, 0.42],
  [100, 77, 3, 0.47],
  [132, 115, 2.5, 0.4],
  [103, 47, 3, 0.63],
  [44, 98, 3, 0.53],
  [134, 117, 3, 0.58],
  [37, 84, 2.5, 0.35],
  [121, 135, 3.5, 0.46],
  [123, 65, 3, 0.7],
  [91, 99, 2.5, 0.7],
  [48, 69, 3.5, 0.47],
];

const TREND_PTS = [[176, 142], [198, 130], [220, 136], [242, 108], [264, 92], [286, 78]];
const label = { fontFamily: mono, fontSize: 10, letterSpacing: 1.5, fill: "#8FC4BE" };

function Logo({ size = 48 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-label="StatScholar logo" role="img">
      <rect width="64" height="64" rx="14" fill="#fff" />
      <path d="M45 13 C20 13 17 30 32 33 C47 36 44 52 19 52" fill="none" stroke="#2F6F6B" strokeWidth="6" strokeLinecap="round" />
      <circle cx="45" cy="13" r="4" fill="#1B2A4A" />
      <circle cx="27" cy="19" r="3" fill="#1B2A4A" />
      <circle cx="32" cy="33" r="3" fill="#1B2A4A" />
      <circle cx="37" cy="47" r="3" fill="#1B2A4A" />
      <circle cx="19" cy="52" r="4" fill="#1B2A4A" />
    </svg>
  );
}

// Raw data -> trend test -> report, over a soft river band
function WorkflowIllustration() {
  return (
    <svg viewBox="0 0 460 250" width="100%" height="100%" aria-hidden="true" style={{ display: "block", maxHeight: 270 }}>
      <defs>
        <linearGradient id="riverFade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#8FC4BE" stopOpacity="0" />
          <stop offset="0.5" stopColor="#8FC4BE" stopOpacity="0.28" />
          <stop offset="1" stopColor="#5FC4B8" stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id="riverEdge" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="1" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <mask id="riverMask">
          <rect x="0" y="170" width="460" height="80" fill="url(#riverEdge)" />
        </mask>
      </defs>

      <g mask="url(#riverMask)">
        <path d="M0 182 C60 164 100 202 160 186 C220 170 260 200 320 184 C380 168 420 194 460 182 L460 250 L0 250Z" fill="url(#riverFade)" />
      </g>

      {RAW_DOTS.map(([x, y, r, o], i) => (
        <circle key={i} cx={x} cy={y} r={r} fill="#fff" fillOpacity={o} />
      ))}
      <text x="24" y="164" style={label}>RAW DATA</text>

      <path d="M146 100 h10 m-4 -4 l4 4 l-4 4" fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

      <line x1="170" y1="150" x2="294" y2="62" stroke="#fff" strokeOpacity="0.6" strokeWidth="2.2" strokeDasharray="6 6" />
      <polyline points={TREND_PTS.map((p) => p.join(",")).join(" ")} fill="none" stroke="#5FC4B8" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      {TREND_PTS.slice(0, -1).map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="4.2" fill="#fff" />
      ))}
      <circle cx="286" cy="78" r="6.5" fill="#5FC4B8" stroke="#fff" strokeWidth="2.6" />
      <text x="172" y="164" style={label}>TREND TEST</text>

      <path d="M306 100 h10 m-4 -4 l4 4 l-4 4" fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

      <rect x="332" y="30" width="104" height="122" rx="8" fill="#fff" fillOpacity="0.95" />
      <rect x="344" y="42" width="48" height="6" rx="3" fill="#1B2A4A" />
      <rect x="344" y="56" width="80" height="4" rx="2" fill="#B9C2D4" />
      <rect x="344" y="65" width="70" height="4" rx="2" fill="#B9C2D4" />
      <polyline points="346,116 362,104 374,110 392,88 410,78 424,68" fill="none" stroke="#2F6F6B" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="344" y="128" width="80" height="4" rx="2" fill="#B9C2D4" />
      <rect x="344" y="137" width="56" height="4" rx="2" fill="#B9C2D4" />
      <text x="338" y="164" style={label}>REPORT</text>
    </svg>
  );
}

export default function AuthBrandPanel() {
  return (
    <div
      style={{
        width: "42%", minWidth: 340, background: T.sidebarGradient, color: "#fff",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
        padding: "36px 44px", boxSizing: "border-box",
        height: "100vh", position: "sticky", top: 0, alignSelf: "flex-start", overflow: "hidden",
      }}
    >
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Logo />
          <div>
            <div style={{ fontFamily: serif, fontSize: 28, fontWeight: 600, lineHeight: 1.1 }}>StatScholar</div>
            <div style={{ fontFamily: mono, fontSize: 10.5, letterSpacing: 2, color: "#8FC4BE", marginTop: 5 }}>
              ADVANCED MANN-KENDALL TREND SUITE
            </div>
          </div>
        </div>
        <div style={{ fontSize: 13.5, color: "#B9C2D4", marginTop: 10, lineHeight: 1.6, maxWidth: 320 }}>
          Upload your time series, test the trend, and export a finished report, all in one place.
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center", padding: "8px 0" }}>
        <WorkflowIllustration />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {FEATURES.map((f) => (
          <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <span style={{ color: "#8FC4BE", fontFamily: mono, fontSize: 13, marginTop: 1 }}>✓</span>
            <span style={{ fontSize: 13.5, color: "#DCE3EE", lineHeight: 1.5 }}>{f}</span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 14 }}>
        <div style={{ fontFamily: mono, fontSize: 11, color: "#7B8AA8" }}>
          {MODULES.length - 1} modules · data preparation to finished report
        </div>
        <div style={{ fontSize: 12, color: "#9AA9C2", lineHeight: 1.5, marginTop: 4 }}>
          © {new Date().getFullYear()} Aakash S<br />
          PhD Scholar, Soil and Water Conservation Engineering<br />
          Tamil Nadu Agricultural University
        </div>
      </div>
    </div>
  );
}
