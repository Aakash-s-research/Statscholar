import React, { useEffect, useState } from "react";
import { ScatterChart, Scatter, Line, ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getSeries, runRegression } from "../api/client";
import { Card, Heading, InterpretationBox, StatTable } from "../components/ui";
import { T } from "../styles/theme";

export default function Regression({ mode, dataset, addToLog }) {
  const numericCols = dataset ? dataset.columns.filter((c) => c.detected_type !== "nominal").map((c) => c.name) : [];
  const [predictor, setPredictor] = useState(numericCols[0]);
  const [outcome, setOutcome] = useState(numericCols[1]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [points, setPoints] = useState(null);

  useEffect(() => {
    if (!dataset || !predictor || !outcome) return;
    let cancelled = false;
    setPoints(null);
    getSeries(dataset.dataset_id, [predictor, outcome])
      .then((data) => {
        if (cancelled) return;
        setPoints(data[predictor].map((x, i) => ({ x, y: data[outcome][i] })));
      })
      .catch(() => { if (!cancelled) setPoints(null); });
    return () => { cancelled = true; };
  }, [dataset, predictor, outcome]);

  async function handleRun() {
    setError(null);
    try {
      const data = await runRegression({ datasetId: dataset.dataset_id, predictor, outcome, mode });
      setResult(data);
      if (addToLog) {
        addToLog(`Regression — ${predictor} → ${outcome}`, data.interpretation.student_text, data.interpretation.research_text, { intercept: data.intercept, slope: data.slope, r_squared: data.r_squared, f_statistic: data.f_statistic, p_value: data.p_value, predictor, outcome });
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Regression failed.");
    }
  }

  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Regression</Heading>;

  // Build a fit line across the observed x-range once we have both the
  // scatter points and the fitted coefficients.
  const fitLine = points && result
    ? (() => {
        const xs = points.map((p) => p.x);
        const xMin = Math.min(...xs), xMax = Math.max(...xs);
        return [
          { x: xMin, fit: result.intercept + result.slope * xMin },
          { x: xMax, fit: result.intercept + result.slope * xMax },
        ];
      })()
    : null;

  return (
    <div>
      <Heading sub="Predict one variable from another, with assumption checks run automatically.">Regression</Heading>
      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
        <select value={predictor} onChange={(e) => setPredictor(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
          {numericCols.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span style={{ fontSize: 13, color: T.slate }}>predicts</span>
        <select value={outcome} onChange={(e) => setOutcome(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
          {numericCols.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={handleRun} style={{ background: T.ink, color: "#fff", border: "none", padding: "7px 16px", borderRadius: 6, fontSize: 13 }}>Run</button>
      </div>

      {error && <Card style={{ marginBottom: 16 }}><span style={{ color: "#7A4A1B", fontSize: 13 }}>{error}</span></Card>}

      {result && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <Card>
            <div style={{ fontSize: 13, color: T.slate, marginBottom: 10 }}>{predictor} vs {outcome}</div>
            {points ? (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart>
                  <CartesianGrid stroke={T.line} />
                  <XAxis dataKey="x" type="number" name={predictor} tick={{ fontSize: 11, fill: T.slate }} domain={["dataMin", "dataMax"]} />
                  <YAxis dataKey="y" type="number" name={outcome} tick={{ fontSize: 11, fill: T.slate }} width={40} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  <Scatter data={points} fill={T.ink} fillOpacity={0.7} />
                  {fitLine && <Line data={fitLine} dataKey="fit" stroke={T.teal} strokeWidth={2} dot={false} activeDot={false} />}
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ fontSize: 12.5, color: T.slate, height: 100, display: "flex", alignItems: "center" }}>Loading chart…</div>
            )}
          </Card>
          <Card>
            <div style={{ fontSize: 13, color: T.slate, marginBottom: 10 }}>Model output</div>
            <StatTable rows={[["Intercept", result.intercept], ["Slope", result.slope], ["R²", result.r_squared], ["F", result.f_statistic], ["p-value", result.p_value]]} />
          </Card>
          <Card style={{ gridColumn: "1 / -1" }}>
            <div style={{ fontSize: 13, color: T.slate, marginBottom: 12 }}>Automated Interpretation</div>
            <InterpretationBox mode={mode} studentText={result.interpretation.student_text} researchText={result.interpretation.research_text} flags={result.interpretation.flags} />
          </Card>
        </div>
      )}
    </div>
  );
}
