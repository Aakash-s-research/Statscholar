import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { getSeries, runTrendTest } from "../api/client";
import { Card, Heading, InterpretationBox, StatTable } from "../components/ui";
import { T } from "../styles/theme";

const AVAILABLE_TESTS = [
  { id: "mann_kendall", label: "Mann-Kendall" },
  { id: "sens_slope", label: "Sen's Slope" },
  { id: "modified_mann_kendall", label: "Modified Mann-Kendall" },
  { id: "pre_whitening", label: "Pre-Whitening" },
  { id: "tfpw", label: "Trend-Free Pre-Whitening" },
  { id: "seasonal_mann_kendall", label: "Seasonal Mann-Kendall" },
];

// Keys that are objects/arrays rather than simple scalars — shown
// separately (or omitted) instead of via the generic StatTable, which
// just stringifies values and would otherwise print "[object Object]".
const NON_SCALAR_KEYS = ["autocorrelation", "per_season", "disagreeing_seasons"];

export default function TrendAnalysis({ mode, dataset, addToLog }) {
  const [test, setTest] = useState("mann_kendall");
  const [variable, setVariable] = useState(dataset?.columns?.[1]?.name || "");
  const [timeColumn, setTimeColumn] = useState(dataset?.columns?.[0]?.name || "");
  const [seasonColumn, setSeasonColumn] = useState(dataset?.columns?.[0]?.name || "");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [series, setSeries] = useState(null);
  const [seriesError, setSeriesError] = useState(null);

  const needsSeasonColumn = test === "seasonal_mann_kendall";

  useEffect(() => {
    if (!dataset || !variable || !timeColumn) return;
    let cancelled = false;
    setSeries(null);
    setSeriesError(null);
    getSeries(dataset.dataset_id, [timeColumn, variable])
      .then((data) => { if (!cancelled) { setSeries(data); setSeriesError(null); } })
      .catch((err) => { if (!cancelled) setSeriesError(err?.response?.data?.detail || "Couldn't load chart data."); });
    return () => { cancelled = true; };
  }, [dataset, variable, timeColumn]);

  async function handleRun() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await runTrendTest({
        datasetId: dataset.dataset_id, variable, timeColumn, test, mode,
        seasonColumn: needsSeasonColumn ? seasonColumn : undefined,
      });
      setResult(data);
      if (addToLog) {
        const testLabel = AVAILABLE_TESTS.find((t) => t.id === test)?.label || test;
        addToLog(`Trend Analysis — ${testLabel}`, data.interpretation.student_text, data.interpretation.research_text, { ...data.statistics, variable, timeColumn });
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "This test failed to run.");
    } finally {
      setLoading(false);
    }
  }

  if (!dataset) {
    return <Heading sub="Upload a dataset on the Dashboard first.">Trend Analysis</Heading>;
  }

  return (
    <div>
      <Heading sub="Non-parametric trend detection for time-series data — StatScholar's flagship module.">
        Trend Analysis
      </Heading>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {AVAILABLE_TESTS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTest(t.id)}
            style={{
              padding: "7px 13px", fontSize: 13, borderRadius: 6,
              border: `1px solid ${test === t.id ? T.teal : T.line}`,
              background: test === t.id ? T.tealSoft : "#fff",
              color: test === t.id ? T.teal : T.ink,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center", flexWrap: "wrap" }}>
        <select value={variable} onChange={(e) => setVariable(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
          {dataset.columns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
        </select>
        <span style={{ fontSize: 13, color: T.slate }}>over</span>
        <select value={timeColumn} onChange={(e) => setTimeColumn(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
          {dataset.columns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
        </select>
        {needsSeasonColumn && (
          <>
            <span style={{ fontSize: 13, color: T.slate }}>grouped by season</span>
            <select value={seasonColumn} onChange={(e) => setSeasonColumn(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
              {dataset.columns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
            </select>
          </>
        )}
        <button
          onClick={handleRun}
          disabled={loading}
          style={{ background: T.ink, color: "#fff", border: "none", padding: "7px 16px", borderRadius: 6, fontSize: 13 }}
        >
          {loading ? "Running…" : "Run test"}
        </button>
      </div>

      {needsSeasonColumn && (
        <div style={{ fontSize: 12.5, color: T.slate, marginBottom: 16 }}>
          Season column should hold a repeating group label (e.g. quarter 0–3, or month 1–12) — not the same column as the time index above.
        </div>
      )}

      {error && (
        <Card style={{ marginBottom: 16, borderColor: T.amber }}>
          <span style={{ color: "#7A4A1B", fontSize: 13 }}>{error}</span>
        </Card>
      )}

      {result && (
        <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card>
              <div style={{ fontSize: 13, color: T.slate, marginBottom: 10 }}>{variable} over {timeColumn}</div>
              {series && series[timeColumn] && series[variable] ? (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={series[timeColumn].map((x, i) => ({ x, y: series[variable][i] }))}>
                    <CartesianGrid stroke={T.line} vertical={false} />
                    <XAxis dataKey="x" tick={{ fontSize: 11, fill: T.slate }} />
                    <YAxis tick={{ fontSize: 11, fill: T.slate }} width={40} />
                    <Tooltip />
                    <Line type="monotone" dataKey="y" stroke={T.teal} strokeWidth={2} dot={{ r: 2.5 }} />
                    {result.statistics.slope !== undefined && series[timeColumn].length > 0 && (
                      <ReferenceLine
                        segment={[
                          { x: series[timeColumn][0], y: series[variable][0] },
                          { x: series[timeColumn][series[timeColumn].length - 1], y: series[variable][0] + result.statistics.slope * (series[timeColumn].length - 1) },
                        ]}
                        stroke={T.amber}
                        strokeDasharray="4 3"
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ fontSize: 12.5, color: T.slate }}>{seriesError || "Loading chart…"}</div>
              )}
            </Card>
            <Card>
              <div style={{ fontSize: 13, color: T.slate, marginBottom: 10 }}>Statistics</div>
              <StatTable rows={Object.entries(result.statistics).filter(([k]) => !NON_SCALAR_KEYS.includes(k))} />
              {result.statistics.per_season && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${T.line}` }}>
                  <div style={{ fontSize: 12, color: T.slate, marginBottom: 8 }}>Per-season breakdown</div>
                  <StatTable
                    rows={Object.entries(result.statistics.per_season).map(
                      ([season, v]) => [`Season ${season}`, `S=${v.S}, Z=${v.Z}, n=${v.n}`]
                    )}
                  />
                </div>
              )}
            </Card>
          </div>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>Automated Interpretation</div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.teal }}>
                {mode === "student" ? "STUDENT" : "RESEARCH"}
              </div>
            </div>
            {result.statistics.significant !== undefined && (
              <div style={{
                display: "inline-block", marginBottom: 10, padding: "3px 10px", fontSize: 11.5,
                fontFamily: "'IBM Plex Mono', monospace",
                background: result.statistics.significant ? T.tealSoft : T.amberSoft,
                color: result.statistics.significant ? T.teal : "#7A4C1D",
              }}>
                {result.statistics.significant ? "reject H₀ — significant trend" : "retain H₀ — not significant"}
              </div>
            )}
            <InterpretationBox
              mode={mode}
              studentText={result.interpretation.student_text}
              researchText={result.interpretation.research_text}
              flags={result.interpretation.flags}
            />
          </Card>
        </div>
      )}
    </div>
  );
}
