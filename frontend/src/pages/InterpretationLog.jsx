import React from "react";
import { Card, Heading } from "../components/ui";
import { T, serif } from "../styles/theme";

export default function InterpretationLog({ mode, log }) {
  if (!log.length) {
    return (
      <div>
        <Heading sub="Every result you generate gets threaded into a running narrative here, ready to feed into the report.">
          Automated Interpretation
        </Heading>
        <Card><div style={{ fontSize: 13.5, color: T.slate }}>Nothing run yet — results from Trend, Correlation, and Regression will appear here.</div></Card>
      </div>
    );
  }

  return (
    <div>
      <Heading sub="Every result you've generated this session.">Automated Interpretation</Heading>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {log.map((entry, i) => (
          <Card key={i}>
            <div style={{ fontSize: 12, color: T.slate, marginBottom: 8 }}>{entry.module}</div>
            <div style={{ fontFamily: serif, fontSize: 15, lineHeight: 1.6 }}>
              {mode === "student" ? entry.studentText : entry.researchText}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
