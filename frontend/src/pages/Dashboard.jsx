import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadDataset } from "../api/client";
import { MODULES, T, mono, serif } from "../styles/theme";

const MODULE_DETAILS = {
  prep: {
    short: "Types, completeness and a 0–100 quality score",
    full: "Upload a CSV, XLSX, or TSV file. StatScholar automatically detects each column's type (nominal, ordinal, interval, or ratio), flags missing values, and gives the dataset a 0–100 quality score before you run any analysis.",
  },
  descriptive: {
    short: "Mean, median, SD and skewness per variable",
    full: "Instantly see mean, median, standard deviation, variance, skewness, kurtosis, and a Shapiro-Wilk normality test for every numeric variable in your dataset.",
  },
  trend: {
    short: "Six Mann-Kendall family tests with Sen's slope",
    full: "The flagship module. Six non-parametric trend tests — Mann-Kendall, Sen's Slope, Modified Mann-Kendall, Pre-Whitening, Trend-Free Pre-Whitening, and Seasonal Mann-Kendall — detect and quantify trends in time-series data, with automatic autocorrelation checks.",
  },
  correlation: {
    short: "Pearson, Spearman or Kendall Tau matrix",
    full: "Measure how strongly two variables move together using Pearson, Spearman, or Kendall Tau correlation, shown as a matrix and a scatter plot.",
  },
  regression: {
    short: "OLS fit with assumption diagnostics",
    full: "Fit a simple linear regression between a predictor and an outcome, with automatic checks for whether the model's normality and homoscedasticity assumptions actually hold.",
  },
  visualization: {
    short: "Auto-recommended chart types",
    full: "StatScholar looks at your dataset's actual column types and relationships, then recommends — and renders, right on the page — the chart types that best reveal what's in your data.",
  },
  interpretation: {
    short: "Session log of every explanation",
    full: "Every result you generate comes with an automatic explanation, in plain language or research style depending on your selected mode, and every one is logged here as you go.",
  },
  report: {
    short: "Compile and export DOCX or PDF",
    full: "Compile everything you've run this session — abstract, methods, descriptive statistics, and each analysis's findings — into one report, exportable as a Word document or PDF.",
  },
};

export default function Dashboard({ dataset, onDatasetLoaded }) {
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [showExplanation, setShowExplanation] = useState(true);
  const inputRef = useRef();
  const navigate = useNavigate();

  async function handleFiles(files) {
    const file = files?.[0];
    if (!file) return;
    setError(null);
    try {
      const data = await uploadDataset(file);
      onDatasetLoaded(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload failed — check the backend is running.");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>

      {/* --- Title + toggle (hero gradient band) --- */}
      <div style={{ background: T.heroGradient, border: `1px solid ${T.line}`, padding: "22px 26px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <h1 style={{ fontFamily: serif, fontSize: 28, fontWeight: 600, margin: 0, color: T.ink }}>StatScholar</h1>
          <button
            onClick={() => setShowExplanation((v) => !v)}
            style={{ background: "#fff", color: T.teal, border: `1px solid ${T.teal}`, padding: "6px 13px", fontSize: 12.5 }}
          >
            {showExplanation ? "Hide explanation ▲" : "Show explanation ▼"}
          </button>
        </div>
        <div style={{ fontSize: 14.5, color: "#5A6B72", marginTop: 6 }}>
          A general-purpose statistical analysis platform anchored by a complete Mann-Kendall trend-analysis suite — correlation, regression, and automated reporting built in.
        </div>
      </div>

      {/* --- Collapsible: intro paragraph + full module explanations --- */}
      {showExplanation && (
        <>
          <p style={{ fontSize: 14, lineHeight: 1.65, maxWidth: 760, margin: 0 }}>
            StatScholar walks you from a raw dataset to a finished report in one place: data
            preparation, descriptive statistics, non-parametric trend analysis, correlation,
            regression, chart recommendations, automated interpretation, and report export.
            Every result is explained twice — once in plain language for learning, and once in
            formal statistical reporting style for a paper — switchable at any time with the
            Student/Research toggle in the top bar.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <h2 style={{ margin: 0, fontFamily: serif, fontSize: 19, fontWeight: 600 }}>What each module does</h2>
              <span style={{ fontSize: 12.5, color: T.slate }}>click any card to jump straight there</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
              {MODULES.filter((m) => m.id !== "dashboard").map((m, i) => (
                <button
                  key={m.id}
                  onClick={() => navigate(m.path)}
                  style={{
                    textAlign: "left", background: T.surface, border: `1px solid ${T.line}`,
                    borderTop: `2px solid ${m.id === "trend" ? T.teal : T.line}`,
                    padding: "16px 17px", display: "flex", flexDirection: "column", gap: 7,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontFamily: serif, fontSize: 16.5, fontWeight: 600 }}>{m.label}</span>
                    <span style={{ fontFamily: mono, fontSize: 11, color: T.slate }}>{String(i + 2).padStart(2, "0")}</span>
                  </div>
                  <span style={{ fontSize: 12.5, color: T.slate, lineHeight: 1.6 }}>{MODULE_DETAILS[m.id].full}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* --- Compact module row, shown only when the explanation is collapsed --- */}
      {!showExplanation && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
          {MODULES.filter((m) => m.id !== "dashboard").map((m, i) => (
            <button
              key={m.id}
              onClick={() => navigate(m.path)}
              style={{
                textAlign: "left", background: T.surface, border: `1px solid ${T.line}`,
                borderTop: `2px solid ${m.id === "trend" ? T.teal : T.line}`,
                padding: "11px 13px", display: "flex", flexDirection: "column", gap: 4,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontFamily: serif, fontSize: 14, fontWeight: 600 }}>{m.label}</span>
                <span style={{ fontFamily: mono, fontSize: 10, color: T.slate }}>{String(i + 2).padStart(2, "0")}</span>
              </div>
              <span style={{ fontSize: 11.5, color: T.slate }}>{MODULE_DETAILS[m.id].short}</span>
            </button>
          ))}
        </div>
      )}

      {/* --- Load data / dataset summary — always visible regardless of toggle --- */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <h2 style={{ margin: 0, fontFamily: serif, fontSize: 19, fontWeight: 600 }}>Get started</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 18 }}>
          <div style={{ background: T.surface, border: `1px solid ${T.line}`, padding: 22, display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Load data</div>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
              style={{
                border: `1px dashed ${dragOver ? T.teal : "#C9C4B6"}`, background: T.paper,
                padding: "28px 20px", display: "flex", flexDirection: "column", alignItems: "center", gap: 9, textAlign: "center",
              }}
            >
              <div style={{ width: 34, height: 34, border: `1px solid ${T.teal}`, color: T.teal, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: mono, fontSize: 15 }}>↑</div>
              <div style={{ fontFamily: serif, fontSize: 16 }}>Drop a CSV or XLSX file here</div>
              <div style={{ fontFamily: mono, fontSize: 11.5, color: T.slate }}>.csv · .xlsx · .tsv — up to 25 MB</div>
              <button
                onClick={() => inputRef.current.click()}
                style={{ marginTop: 6, border: `1px solid ${T.teal}`, background: T.teal, color: "#fff", padding: "8px 16px", fontSize: 13, fontWeight: 500 }}
              >
                Browse files
              </button>
              <input ref={inputRef} type="file" accept=".csv,.xlsx,.tsv" onChange={(e) => handleFiles(e.target.files)} style={{ display: "none" }} />
            </div>
            <div style={{ fontSize: 12.5, color: T.slate, lineHeight: 1.5 }}>The first row is read as a header. A date or year column is required for the trend module.</div>
            {error && <div style={{ color: T.amber, fontSize: 13 }}>{error}</div>}
          </div>

          <div style={{ background: T.surface, border: `1px solid ${T.line}`, padding: 22, display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Dataset summary</div>
              {dataset && <div style={{ fontFamily: mono, fontSize: 11.5, color: T.teal }}>validated</div>}
            </div>
            {dataset ? (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))", gap: 14 }}>
                  {[
                    { label: "Rows", value: dataset.row_count },
                    { label: "Columns", value: dataset.columns.length },
                    { label: "Quality", value: `${dataset.quality_score}` },
                  ].map((m) => (
                    <div key={m.label} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                      <div style={{ fontFamily: mono, fontSize: 20 }}>{m.value}</div>
                      <div style={{ fontSize: 12, color: T.slate }}>{m.label}</div>
                    </div>
                  ))}
                </div>
                <div style={{ borderTop: `1px solid ${T.line}`, paddingTop: 14, display: "flex", flexDirection: "column", gap: 7 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                    <span style={{ color: T.slate }}>File</span>
                    <span style={{ fontFamily: mono, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={dataset.filename}>
                      {dataset.filename}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => navigate("/prep")}
                  style={{ background: T.ink, color: "#fff", border: "none", padding: "8px 16px", fontSize: 13, alignSelf: "flex-start" }}
                >
                  Review in Data Preparation
                </button>
              </>
            ) : (
              <div style={{ fontSize: 13, color: T.slate }}>No dataset loaded yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
