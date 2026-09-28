import React, { useEffect, useMemo, useState } from "react";
import { describeVariable, exportReport, exportReportPdf } from "../api/client";
import { Card, Heading } from "../components/ui";
import { T, mono, serif } from "../styles/theme";

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// Rough page-length estimate for the length indicator next to each
// section — ~1800 characters/page is a reasonable approximation for a
// single-spaced report paragraph at standard margins. It's an estimate,
// shown as one; not a promise of exact pagination.
function estimatePages(text) {
  return Math.max(1, Math.ceil((text || "").length / 1800));
}

function logEntriesFor(log, prefix) {
  return log.filter((e) => e.module.startsWith(prefix));
}

function joinEntries(entries, mode, emptyText) {
  if (entries.length === 0) return emptyText;
  return entries.map((e) => (mode === "student" ? e.studentText : e.researchText)).join("\n\n");
}

// Builds a chart spec (dataset_id, chart_type, columns) from the first log
// entry of a given kind that has enough raw data to regenerate a chart —
// this is what lets the export actually embed a real image server-side,
// rather than just repeating the text interpretation.
function chartSpecFor(entries, kind, datasetId) {
  const entry = entries.find((e) => e.raw);
  if (!entry) return null;
  const raw = entry.raw;

  if (kind === "trend" && raw.timeColumn && raw.variable) {
    return { dataset_id: datasetId, chart_type: "line", columns: [raw.timeColumn, raw.variable], title: `${raw.variable} over ${raw.timeColumn}` };
  }
  if (kind === "correlation" && raw.variables && raw.variables.length >= 2) {
    return { dataset_id: datasetId, chart_type: "scatter", columns: [raw.variables[0], raw.variables[1]], title: `${raw.variables[0]} vs ${raw.variables[1]}` };
  }
  if (kind === "regression" && raw.predictor && raw.outcome) {
    return { dataset_id: datasetId, chart_type: "scatter", columns: [raw.predictor, raw.outcome], title: `${raw.predictor} vs ${raw.outcome}` };
  }
  return null;
}

export default function ReportGeneration({ mode, log, dataset }) {
  const [descriptiveText, setDescriptiveText] = useState(null);
  const [descriptiveResults, setDescriptiveResults] = useState(null);
  const [exporting, setExporting] = useState(null);
  const [checked, setChecked] = useState({
    abstract: true, data: true, methods: true, descriptive: true,
    trend: true, correlation: true, regression: true, figures: true, appendix: false,
  });

  useEffect(() => {
    if (!dataset) return;
    let cancelled = false;
    const numericCols = dataset.columns.filter((c) => c.detected_type !== "nominal").map((c) => c.name);
    Promise.all(numericCols.slice(0, 6).map((name) => describeVariable(dataset.dataset_id, name).catch(() => null)))
      .then((results) => {
        if (cancelled) return;
        const valid = results.filter(Boolean);
        const lines = valid.map((r) => `${r.variable}: mean = ${r.mean}, SD = ${r.sd}, skewness = ${r.skewness}`);
        setDescriptiveText(lines.length ? lines.join("\n") : "No numeric columns available for descriptive statistics.");
        setDescriptiveResults(valid);
      });
    return () => { cancelled = true; };
  }, [dataset]);

  const sections = useMemo(() => {
    const trendEntries = logEntriesFor(log, "Trend Analysis");
    const corrEntries = logEntriesFor(log, "Correlation");
    const regEntries = logEntriesFor(log, "Regression");
    const vizEntries = logEntriesFor(log, "Visualization");
    const modulesRun = [...new Set(log.map((e) => e.module.split(" — ")[0]))];
    const datasetId = dataset?.dataset_id;

    const trendChart = chartSpecFor(trendEntries, "trend", datasetId);
    const corrChart = chartSpecFor(corrEntries, "correlation", datasetId);
    const regChart = chartSpecFor(regEntries, "regression", datasetId);
    const embeddedCount = [trendChart, corrChart, regChart].filter(Boolean).length + vizEntries.length;

    // Real formatted tables for the Figures & tables section — descriptive
    // statistics (from the same data the "Descriptive statistics" section's
    // text summarizes) and a correlation matrix (from the first correlation
    // run this session, if any).
    const descriptiveTable = descriptiveResults && descriptiveResults.length
      ? {
          title: "Descriptive Statistics",
          headers: ["Variable", "Mean", "Median", "SD", "Skewness"],
          rows: descriptiveResults.map((r) => [r.variable, String(r.mean), String(r.median), String(r.sd), String(r.skewness)]),
        }
      : null;

    const corrEntryWithMatrix = corrEntries.find((e) => e.raw && e.raw.matrix && e.raw.variables);
    const correlationTable = corrEntryWithMatrix
      ? {
          title: `Correlation Matrix (${corrEntryWithMatrix.raw.method})`,
          headers: ["", ...corrEntryWithMatrix.raw.variables],
          rows: corrEntryWithMatrix.raw.matrix.map((row, i) => [corrEntryWithMatrix.raw.variables[i], ...row.map((v) => v.toFixed(2))]),
        }
      : null;

    const figuresTables = [descriptiveTable, correlationTable].filter(Boolean);
    const tableCount = figuresTables.length;

    const abstractText = dataset
      ? log.length > 0
        ? `This report examines a dataset of ${dataset.row_count} rows across ${dataset.columns.length} variables (${dataset.filename}). ${log.length} analys${log.length === 1 ? "is was" : "es were"} run this session, covering ${modulesRun.join(", ")}.${trendEntries.length ? " " + (mode === "student" ? trendEntries[0].studentText : trendEntries[0].researchText) : ""}`
        : `This report is based on ${dataset.filename} (${dataset.row_count} rows, ${dataset.columns.length} columns). No analyses have been run yet this session — visit Trend Analysis, Correlation, or Regression to generate findings for this report.`
      : "No dataset loaded.";

    const dataText = dataset
      ? `The dataset "${dataset.filename}" contains ${dataset.row_count} rows and ${dataset.columns.length} columns: ${dataset.columns.map((c) => c.name).join(", ")}. Data quality score: ${dataset.quality_score}/100.`
      : "No dataset loaded.";

    const methodsText = modulesRun.length
      ? `This report includes results from: ${modulesRun.join(", ")}.`
      : "No methods have been run yet this session.";

    const figuresText = log.length || tableCount
      ? `${log.length} chart${log.length !== 1 ? "s" : ""} were generated this session across ${modulesRun.join(", ") || "no modules"}. ${embeddedCount > 0 ? `${embeddedCount} of them are embedded as real images in the sections above.` : "None had enough data captured this session to embed as an image."} ${tableCount} formatted table${tableCount !== 1 ? "s" : ""} ${tableCount === 1 ? "is" : "are"} included below.`
      : "No charts or tables have been generated yet this session.";

    const appendixText = log.some((e) => e.raw)
      ? log.filter((e) => e.raw).map((e) => `${e.module}\n${JSON.stringify(e.raw, null, 2)}`).join("\n\n")
      : "No raw output captured yet this session.";

    // Charts explicitly added from the Visualization module each get their
    // own section — unlike Trend/Correlation/Regression (one representative
    // chart per category), these were individually chosen by the user via
    // "Add to report", so each one is kept distinct rather than collapsed.
    const vizSections = vizEntries.map((entry, i) => ({
      key: `viz-${i}`,
      title: entry.module.replace("Visualization — ", ""),
      text: mode === "student" ? entry.studentText : entry.researchText,
      chart: entry.raw,
    }));

    return [
      { key: "abstract", title: "Abstract", text: abstractText },
      { key: "data", title: "Data", text: dataText },
      { key: "methods", title: "Methods", text: methodsText },
      { key: "descriptive", title: "Descriptive statistics", text: descriptiveText || "Loading…" },
      { key: "trend", title: "Trend analysis", text: joinEntries(trendEntries, mode, "No trend analysis results were generated this session."), chart: trendChart },
      { key: "correlation", title: "Correlation", text: joinEntries(corrEntries, mode, "No correlation results were generated this session."), chart: corrChart },
      { key: "regression", title: "Regression", text: joinEntries(regEntries, mode, "No regression results were generated this session."), chart: regChart },
      ...vizSections,
      { key: "figures", title: "Figures & tables", text: figuresText, tables: figuresTables.length ? figuresTables : undefined },
      { key: "appendix", title: "Appendix — raw output", text: appendixText },
    ];
  }, [log, mode, dataset, descriptiveText, descriptiveResults]);

  const activeSections = sections.filter((s) => checked[s.key] !== false);
  const totalPages = activeSections.reduce((sum, s) => sum + estimatePages(s.text), 0);

  async function handleExport(format) {
    setExporting(format);
    try {
      const exportSections = activeSections.map((s) => ({
        title: s.title, text: s.text,
        ...(s.chart ? { chart: s.chart } : {}),
        ...(s.tables ? { tables: s.tables } : {}),
      }));
      const title = dataset ? `StatScholar Report — ${dataset.filename}` : "StatScholar Report";
      if (format === "docx") {
        const blob = await exportReport({ projectTitle: title, sections: exportSections });
        downloadBlob(blob, "statscholar_report.docx");
      } else {
        const blob = await exportReportPdf({ projectTitle: title, sections: exportSections });
        downloadBlob(blob, "statscholar_report.pdf");
      }
    } finally {
      setExporting(null);
    }
  }

  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Report Generation</Heading>;

  return (
    <div>
      <Heading sub="Select the sections to compile. Interpretation text follows the current mode.">
        Report Generation
      </Heading>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20 }}>
        <Card>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Sections</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {sections.map((s) => (
              <label key={s.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0", fontSize: 13.5, cursor: "pointer" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={checked[s.key] !== false}
                    onChange={() => setChecked((c) => ({ ...c, [s.key]: !c[s.key] }))}
                  />
                  {s.title}
                  {s.chart && <span style={{ fontFamily: mono, fontSize: 10, color: T.teal }}>📊</span>}
                  {s.tables && <span style={{ fontFamily: mono, fontSize: 10, color: T.teal }}>▦</span>}
                </span>
                <span style={{ fontFamily: mono, fontSize: 11.5, color: T.slate }}>{estimatePages(s.text)}p</span>
              </label>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", borderTop: `1px solid ${T.line}`, marginTop: 12, paddingTop: 12, fontSize: 13 }}>
            <span style={{ color: T.slate }}>Estimated length</span>
            <span style={{ fontFamily: mono }}>{totalPages} page{totalPages !== 1 ? "s" : ""}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
            <button
              onClick={() => handleExport("docx")}
              disabled={!activeSections.length || exporting}
              style={{ background: T.ink, color: "#fff", border: "none", borderRadius: 6, padding: "9px 0", fontSize: 13, opacity: activeSections.length ? 1 : 0.5 }}
            >
              {exporting === "docx" ? "Exporting…" : "Export DOCX"}
            </button>
            <button
              onClick={() => handleExport("pdf")}
              disabled={!activeSections.length || exporting}
              style={{ background: "#fff", color: T.ink, border: `1px solid ${T.line}`, borderRadius: 6, padding: "9px 0", fontSize: 13, opacity: activeSections.length ? 1 : 0.5 }}
            >
              {exporting === "pdf" ? "Exporting…" : "Export PDF"}
            </button>
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Live preview</div>
            <div style={{ fontFamily: mono, fontSize: 11, color: T.slate }}>
              {mode === "student" ? "Student mode" : "Research mode"}
            </div>
          </div>
          <div style={{ border: `1px solid ${T.line}`, padding: "24px 28px" }}>
            <div style={{ fontFamily: serif, fontSize: 22, fontWeight: 600, marginBottom: 6 }}>
              StatScholar Report — {dataset.filename}
            </div>
            <div style={{ fontSize: 12.5, color: T.slate, marginBottom: 18 }}>
              Compiled by StatScholar · {activeSections.length} sections · {totalPages} pages
            </div>
            <div style={{ borderTop: `1px solid ${T.line}`, paddingTop: 16, display: "flex", flexDirection: "column", gap: 18 }}>
              {activeSections.map((s, i) => (
                <div key={s.key}>
                  <div style={{ fontFamily: mono, fontSize: 11.5, color: T.slate }}>{i + 1}.</div>
                  <div style={{ fontFamily: serif, fontSize: 17, fontWeight: 600, marginBottom: 6 }}>{s.title}</div>
                  <div style={{ fontSize: 13.5, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>{s.text}</div>
                  {s.chart && (
                    <div style={{ marginTop: 8, fontFamily: mono, fontSize: 11, color: T.teal, border: `1px dashed ${T.teal}`, padding: "6px 10px", display: "inline-block" }}>
                      📊 chart will be embedded here on export: {s.chart.title}
                    </div>
                  )}
                  {(s.tables || []).map((t, ti) => (
                    <div key={ti} style={{ marginTop: 12 }}>
                      {t.title && <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 6 }}>{t.title}</div>}
                      <table style={{ borderCollapse: "collapse", fontSize: 11.5 }}>
                        <thead>
                          <tr>
                            {t.headers.map((h, hi) => (
                              <th key={hi} style={{ border: `1px solid ${T.line}`, background: T.ink, color: "#fff", padding: "4px 8px", textAlign: "left" }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {t.rows.map((row, ri) => (
                            <tr key={ri}>
                              {row.map((val, ci) => (
                                <td key={ci} style={{ border: `1px solid ${T.line}`, padding: "4px 8px" }}>{val}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
