import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { getChartRecommendations, getSeries, runCorrelation } from "../api/client";
import { Heading } from "../components/ui";
import { T, mono, serif } from "../styles/theme";

/**
 * Fetches and renders the actual chart for one recommendation, inline —
 * this is what makes the Visualization module a real feature rather than
 * a list of suggestions pointing you elsewhere. Kept as its own component
 * so each card manages its own fetch/loading state independently.
 */
function InlineChart({ rec, datasetId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);

    async function load() {
      try {
        if (rec.chart_type === "line" || rec.chart_type === "scatter") {
          const s = await getSeries(datasetId, rec.columns);
          const points = s[rec.columns[0]].map((x, i) => ({ x, y: s[rec.columns[1]][i] }));
          if (!cancelled) setData({ type: rec.chart_type, points });
        } else if (rec.chart_type === "heatmap") {
          const res = await runCorrelation({ datasetId, variables: rec.columns, method: "pearson", mode: "student" });
          if (!cancelled) setData({ type: "heatmap", matrix: res.matrix, variables: res.variables });
        } else if (rec.chart_type === "bar") {
          const [groupCol, valCol] = rec.columns;
          const s = await getSeries(datasetId, rec.columns);
          const groups = {};
          s[groupCol].forEach((g, i) => {
            const v = s[valCol][i];
            if (!groups[g]) groups[g] = { sum: 0, count: 0 };
            groups[g].sum += v;
            groups[g].count += 1;
          });
          const bars = Object.entries(groups)
            .map(([g, agg]) => ({ group: g, value: agg.sum / agg.count }))
            .sort((a, b) => (a.group > b.group ? 1 : -1));
          if (!cancelled) setData({ type: "bar", bars });
        }
      } catch (err) {
        if (!cancelled) setError(err?.response?.data?.detail || "Couldn't load chart data.");
      }
    }
    load();
    return () => { cancelled = true; };
  }, [rec, datasetId]);

  if (error) return <div style={{ fontSize: 12.5, color: T.amber, padding: 16 }}>{error}</div>;
  if (!data) return <div style={{ fontSize: 12.5, color: T.slate, padding: 16 }}>Loading chart…</div>;

  if (data.type === "line") {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data.points}>
          <CartesianGrid stroke={T.line} vertical={false} />
          <XAxis dataKey="x" tick={{ fontSize: 11, fill: T.slate }} />
          <YAxis tick={{ fontSize: 11, fill: T.slate }} width={42} />
          <Tooltip />
          <Line type="monotone" dataKey="y" stroke={T.teal} strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (data.type === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart>
          <CartesianGrid stroke={T.line} />
          <XAxis dataKey="x" type="number" tick={{ fontSize: 11, fill: T.slate }} domain={["dataMin", "dataMax"]} />
          <YAxis dataKey="y" type="number" tick={{ fontSize: 11, fill: T.slate }} width={42} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={data.points} fill={T.ink} fillOpacity={0.7} />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }
  if (data.type === "bar") {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data.bars}>
          <CartesianGrid stroke={T.line} vertical={false} />
          <XAxis dataKey="group" tick={{ fontSize: 11, fill: T.slate }} />
          <YAxis tick={{ fontSize: 11, fill: T.slate }} width={42} />
          <Tooltip />
          <Bar dataKey="value" fill={T.teal} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (data.type === "heatmap") {
    return (
      <div style={{ padding: "16px 4px", overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <td />
              {data.variables.map((v) => (
                <td key={v} style={{ fontSize: 10.5, color: T.slate, textAlign: "center", padding: 4 }}>{v}</td>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.matrix.map((row, i) => (
              <tr key={i}>
                <td style={{ fontSize: 10.5, color: T.slate, paddingRight: 6, whiteSpace: "nowrap" }}>{data.variables[i]}</td>
                {row.map((val, j) => {
                  const rgb = val >= 0 ? "47,111,107" : "201,125,52";
                  return (
                    <td key={j} style={{ padding: 2 }}>
                      <div style={{ background: `rgba(${rgb},${Math.abs(val)})`, color: Math.abs(val) > 0.5 ? "#fff" : T.ink, fontFamily: mono, fontSize: 11, textAlign: "center", padding: "10px 4px" }}>
                        {val.toFixed(2)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return null;
}

export default function Visualization({ dataset, addToLog }) {
  const [recommendations, setRecommendations] = useState(null);
  const [error, setError] = useState(null);
  const [openKey, setOpenKey] = useState(null);
  const [addedKeys, setAddedKeys] = useState(new Set());

  useEffect(() => {
    if (!dataset) return;
    let cancelled = false;
    setRecommendations(null);
    setOpenKey(null);
    setAddedKeys(new Set());
    getChartRecommendations(dataset.dataset_id)
      .then((data) => { if (!cancelled) setRecommendations(data); })
      .catch((err) => { if (!cancelled) setError(err?.response?.data?.detail || "Couldn't load recommendations."); });
    return () => { cancelled = true; };
  }, [dataset]);

  function handleAddToReport(rec) {
    if (!addToLog) return;
    addToLog(
      `Visualization — ${rec.name}`,
      rec.why, // same text for both modes — this is a recommendation rationale, not a mode-dependent statistical interpretation
      rec.why,
      { dataset_id: dataset.dataset_id, chart_type: rec.chart_type, columns: rec.columns, title: rec.name }
    );
    setAddedKeys((prev) => new Set(prev).add(rec.name));
  }

  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Visualization</Heading>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <Heading sub="Charts recommended from your column types and their relationships — click any card to render it, or add it straight to your report.">
        Visualization
      </Heading>

      {error && <div style={{ color: T.amber, fontSize: 13 }}>{error}</div>}
      {!recommendations && !error && <div style={{ fontSize: 13, color: T.slate }}>Analyzing columns…</div>}

      {recommendations && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {recommendations.map((c) => {
            const isOpen = openKey === c.name;
            const canRender = c.chart_type !== "none";
            const isAdded = addedKeys.has(c.name);
            return (
              <div key={c.name} style={{ background: T.surface, border: `1px solid ${T.line}`, display: "flex", flexDirection: "column" }}>
                <div
                  onClick={() => canRender && setOpenKey(isOpen ? null : c.name)}
                  style={{
                    height: isOpen ? "auto" : 130, borderBottom: `1px solid ${T.line}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    cursor: canRender ? "pointer" : "default",
                    backgroundImage: isOpen ? "none" : "repeating-linear-gradient(135deg, #F3F1EA 0 6px, #FAFAF7 6px 12px)",
                  }}
                >
                  {isOpen ? (
                    <InlineChart rec={c} datasetId={dataset.dataset_id} />
                  ) : (
                    <span style={{ fontFamily: mono, fontSize: 11, color: T.slate, background: T.paper, border: `1px solid ${T.line}`, padding: "4px 9px" }}>
                      {c.chart_type}
                    </span>
                  )}
                </div>
                <div style={{ padding: "15px 17px", display: "flex", flexDirection: "column", gap: 7, flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontFamily: serif, fontSize: 16, fontWeight: 600 }}>{c.name}</span>
                    <span style={{ fontFamily: mono, fontSize: 11, color: c.score === "recommended" ? T.teal : T.slate }}>{c.score}</span>
                  </div>
                  <span style={{ fontSize: 12.5, color: T.slate, lineHeight: 1.5 }}>{c.why}</span>
                  {canRender && (
                    <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                      <button
                        onClick={() => setOpenKey(isOpen ? null : c.name)}
                        style={{ alignSelf: "flex-start", border: `1px solid ${T.teal}`, background: isOpen ? T.teal : "#fff", color: isOpen ? "#fff" : T.teal, padding: "6px 12px", fontSize: 12.5 }}
                      >
                        {isOpen ? "Hide chart" : "View chart"}
                      </button>
                      <button
                        onClick={() => handleAddToReport(c)}
                        disabled={isAdded}
                        style={{
                          alignSelf: "flex-start", border: `1px solid ${isAdded ? T.line : T.ink}`,
                          background: isAdded ? T.paper : "#fff", color: isAdded ? T.slate : T.ink,
                          padding: "6px 12px", fontSize: 12.5,
                        }}
                      >
                        {isAdded ? "Added ✓" : "Add to report"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
