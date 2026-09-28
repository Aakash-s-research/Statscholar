import React from "react";
import { Heading } from "../components/ui";
import { T, mono } from "../styles/theme";

const TYPE_PILL = {
  ratio: { bg: T.tealSoft, fg: T.teal },
  ordinal: { bg: T.tealSoft, fg: T.teal },
  interval: { bg: T.tealSoft, fg: T.teal },
  nominal: { bg: "#EEF0F5", fg: T.ink },
};

export default function DataPrep({ dataset }) {
  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Data Preparation</Heading>;

  const maxMissing = Math.max(...dataset.columns.map((c) => c.missing_count), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <Heading sub="Inferred column types, completeness, and a preview of the raw file. Correct any type before running tests — the Mann-Kendall family requires an ordered time index.">
        Data Preparation
      </Heading>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 18 }}>
        <div style={{ background: T.surface, border: `1px solid ${T.line}`, padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Data quality score</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 9 }}>
            <span style={{ fontFamily: mono, fontSize: 44, lineHeight: 1, color: T.teal }}>{dataset.quality_score}</span>
            <span style={{ fontFamily: mono, fontSize: 13, color: T.slate, paddingBottom: 6 }}>/ 100</span>
          </div>
          <div style={{ height: 6, background: T.tealSoft, position: "relative" }}>
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${dataset.quality_score}%`, background: T.teal }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: `1px solid ${T.line}`, paddingTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
              <span>Rows</span><span style={{ fontFamily: mono }}>{dataset.row_count}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
              <span>Columns detected</span><span style={{ fontFamily: mono }}>{dataset.columns.length}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
              <span>Columns with missing values</span>
              <span style={{ fontFamily: mono, color: dataset.columns.some((c) => c.missing_count > 0) ? T.amber : T.teal }}>
                {dataset.columns.filter((c) => c.missing_count > 0).length}
              </span>
            </div>
          </div>
        </div>

        <div style={{ background: T.surface, border: `1px solid ${T.line}`, padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Missing values</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
            {dataset.columns.map((c) => (
              <div key={c.name} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span style={{ fontFamily: mono }}>{c.name}</span>
                  <span style={{ fontFamily: mono, color: T.slate }}>{c.missing_count} ({c.missing_pct}%)</span>
                </div>
                <div style={{ height: 4, background: "#F1EFE8", position: "relative" }}>
                  <div style={{
                    position: "absolute", left: 0, top: 0, bottom: 0,
                    width: `${(c.missing_count / maxMissing) * 100}%`,
                    background: c.missing_count > 0 ? T.amber : T.teal,
                  }} />
                </div>
              </div>
            ))}
          </div>
          {dataset.columns.some((c) => c.missing_count > 0) && (
            <div style={{ background: T.amberSoft, borderLeft: `3px solid ${T.amber}`, padding: "11px 13px", fontSize: 12.5, color: "#7A4C1D", lineHeight: 1.55 }}>
              Mann-Kendall and Sen's Slope tolerate gaps; regression will drop incomplete rows.
            </div>
          )}
        </div>
      </div>

      <div style={{ background: T.surface, border: `1px solid ${T.line}` }}>
        <div style={{ padding: "15px 20px", borderBottom: `1px solid ${T.line}`, display: "flex", justifyContent: "space-between" }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Column types</div>
          <div style={{ fontFamily: mono, fontSize: 11.5, color: T.slate }}>{dataset.columns.length} columns detected</div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: 500, fontSize: 12.5, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: T.paper }}>
                {["Column", "Detected type", "Missing"].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "9px 20px", fontWeight: 500, color: T.slate, borderBottom: `1px solid ${T.line}` }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataset.columns.map((c) => {
                const pill = TYPE_PILL[c.detected_type] || TYPE_PILL.nominal;
                return (
                  <tr key={c.name}>
                    <td style={{ padding: "10px 20px", borderBottom: "1px solid #F1EFE8", fontFamily: mono }}>{c.name}</td>
                    <td style={{ padding: "10px 20px", borderBottom: "1px solid #F1EFE8" }}>
                      <span style={{ background: pill.bg, color: pill.fg, padding: "2.5px 8px", fontSize: 11.5 }}>{c.detected_type}</span>
                    </td>
                    <td style={{ padding: "10px 20px", borderBottom: "1px solid #F1EFE8", fontFamily: mono, color: T.slate }}>{c.missing_count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ background: T.surface, border: `1px solid ${T.line}` }}>
        <div style={{ padding: "15px 20px", borderBottom: `1px solid ${T.line}`, display: "flex", justifyContent: "space-between" }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Preview</div>
          <div style={{ fontFamily: mono, fontSize: 11.5, color: T.slate }}>first {dataset.preview.length} of {dataset.row_count} rows</div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: 480, fontFamily: mono, fontSize: 12, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: T.paper }}>
                {dataset.columns.map((c) => (
                  <th key={c.name} style={{ textAlign: "right", padding: "8px 20px", fontWeight: 500, color: T.slate, borderBottom: `1px solid ${T.line}` }}>{c.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataset.preview.map((row, i) => (
                <tr key={i}>
                  {dataset.columns.map((c) => (
                    <td key={c.name} style={{ padding: "8px 20px", textAlign: "right", borderBottom: "1px solid #F1EFE8" }}>
                      {row[c.name] === null ? "—" : String(row[c.name])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
