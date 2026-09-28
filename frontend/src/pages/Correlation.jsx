import React, { useEffect, useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getSeries, runCorrelation } from "../api/client";
import { Card, Heading, InterpretationBox } from "../components/ui";
import { T, mono } from "../styles/theme";

const METHODS = [
  { id: "pearson", label: "Pearson" },
  { id: "spearman", label: "Spearman" },
  { id: "kendall", label: "Kendall Tau" },
];

export default function Correlation({ mode, dataset, addToLog }) {
  const numericCols = dataset ? dataset.columns.filter((c) => c.detected_type !== "nominal").map((c) => c.name) : [];
  const [method, setMethod] = useState("pearson");
  const [variables, setVariables] = useState(numericCols.slice(0, 2));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [scatterData, setScatterData] = useState(null);

  useEffect(() => {
    if (!dataset || variables.length < 2 || !variables[0] || !variables[1]) return;
    let cancelled = false;
    setScatterData(null);
    getSeries(dataset.dataset_id, variables)
      .then((data) => {
        if (cancelled) return;
        const points = data[variables[0]].map((x, i) => ({ x, y: data[variables[1]][i] }));
        setScatterData(points);
      })
      .catch(() => { if (!cancelled) setScatterData(null); });
    return () => { cancelled = true; };
  }, [dataset, variables]);

  async function handleRun() {
    setError(null);
    try {
      const data = await runCorrelation({ datasetId: dataset.dataset_id, variables, method, mode });
      setResult(data);
      if (addToLog) {
        addToLog(`Correlation — ${data.method}`, data.interpretation.student_text, data.interpretation.research_text, { method: data.method, variables: data.variables, matrix: data.matrix });
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Correlation failed.");
    }
  }

  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Correlation</Heading>;

  return (
    <div>
      <Heading sub="How closely two variables move together — and whether that's likely to be real.">Correlation</Heading>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {METHODS.map((m) => (
          <button key={m.id} onClick={() => setMethod(m.id)}
            style={{ padding: "7px 13px", fontSize: 13, borderRadius: 6, border: `1px solid ${method === m.id ? T.teal : T.line}`, background: method === m.id ? T.tealSoft : "#fff", color: method === m.id ? T.teal : T.ink }}>
            {m.label}
          </button>
        ))}
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {[0, 1].map((i) => (
          <select key={i} value={variables[i]} onChange={(e) => setVariables((v) => { const next = [...v]; next[i] = e.target.value; return next; })} style={{ padding: "6px 10px", fontSize: 13 }}>
            {numericCols.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        ))}
        <button onClick={handleRun} style={{ background: T.ink, color: "#fff", border: "none", padding: "7px 16px", borderRadius: 6, fontSize: 13 }}>Run</button>
      </div>

      {error && <Card style={{ marginBottom: 16 }}><span style={{ color: "#7A4A1B", fontSize: 13 }}>{error}</span></Card>}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <Card>
            <div style={{ fontSize: 13, color: T.slate, marginBottom: 10 }}>{variables[0]} vs {variables[1]}</div>
            {scatterData ? (
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart>
                  <CartesianGrid stroke={T.line} />
                  <XAxis dataKey="x" name={variables[0]} tick={{ fontSize: 11, fill: T.slate }} />
                  <YAxis dataKey="y" name={variables[1]} tick={{ fontSize: 11, fill: T.slate }} width={40} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                  <Scatter data={scatterData} fill={T.ink} />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ fontSize: 12.5, color: T.slate, height: 100, display: "flex", alignItems: "center" }}>Loading chart…</div>
            )}
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20 }}>
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{result.method} matrix</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: T.slate }}>
                  <span>−1</span>
                  <span style={{ width: 36, height: 7, background: T.amber, display: "inline-block" }} />
                  <span style={{ width: 14, height: 7, background: T.paper, border: `1px solid ${T.line}`, display: "inline-block" }} />
                  <span style={{ width: 36, height: 7, background: T.teal, display: "inline-block" }} />
                  <span>+1</span>
                </div>
              </div>
              <table style={{ borderCollapse: "collapse", width: "100%" }}>
                <tbody>
                  {result.matrix.map((row, i) => (
                    <tr key={i}>
                      {row.map((val, j) => {
                        const rgb = val >= 0 ? "47,111,107" : "201,125,52";
                        return (
                          <td key={j} style={{ padding: 2 }}>
                            <div style={{ background: `rgba(${rgb},${Math.abs(val)})`, color: Math.abs(val) > 0.5 ? "#fff" : T.ink, fontFamily: mono, fontSize: 12.5, textAlign: "center", padding: "16px 6px" }}>
                              {val.toFixed(2)}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
            <Card>
              <div style={{ fontSize: 13, color: T.slate, marginBottom: 12 }}>Automated Interpretation</div>
              <InterpretationBox mode={mode} studentText={result.interpretation.student_text} researchText={result.interpretation.research_text} flags={result.interpretation.flags} />
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
