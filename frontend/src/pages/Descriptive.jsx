import React, { useEffect, useState } from "react";
import { describeVariable } from "../api/client";
import { Card, Heading, StatTable } from "../components/ui";
import { T } from "../styles/theme";

export default function Descriptive({ dataset }) {
  const [selected, setSelected] = useState([]);
  const [results, setResults] = useState({});

  useEffect(() => {
    if (!dataset) return;
    const numeric = dataset.columns.filter((c) => c.detected_type !== "nominal").map((c) => c.name);
    setSelected(numeric);
    numeric.forEach(async (name) => {
      try {
        const r = await describeVariable(dataset.dataset_id, name);
        setResults((prev) => ({ ...prev, [name]: r }));
      } catch {
        // leave unset for v1
      }
    });
  }, [dataset]);

  if (!dataset) return <Heading sub="Upload a dataset on the Dashboard first.">Descriptive Statistics</Heading>;

  return (
    <div>
      <Heading sub="Central tendency and dispersion, computed per variable.">Descriptive Statistics</Heading>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        {selected.map((name) => {
          const r = results[name];
          return (
            <Card key={name}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>{name}</div>
              {r ? (
                <StatTable rows={[["Mean", r.mean], ["Median", r.median], ["SD", r.sd], ["Skewness", r.skewness]]} />
              ) : (
                <div style={{ fontSize: 13, color: T.slate }}>Loading…</div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
