"use client";

import { useId, useMemo, useState } from "react";
import type { Results } from "@/lib/data";
import { SortableTable, type SortRow } from "@/components/SortableTable";
import { TableWrap } from "@/components/TableWrap";

const SECTION_NAMES: Record<string, string> = {
  A: "A — drift detection and notice",
  B: "B — incident response and communication",
  C: "C — rollback",
  D: "D — monthly report completeness",
  E: "E — evidence and reproducibility",
};

/** The Day-60 rubric, read from day-60/scoresheet.csv. Every observed value is empty. */
export function Day60Rubric({ results }: { results: Results }) {
  const rubric = results.rubric ?? [];
  const totals = results.totals ?? [];
  const context = results.context ?? [];
  const [section, setSection] = useState("all");
  const base = useId();

  const sections = useMemo(() => [...new Set(rubric.map((r) => r.section))].sort(), [rubric]);
  const shown = useMemo(() => (section === "all" ? rubric : rubric.filter((r) => r.section === section)), [rubric, section]);

  const pointsShown = shown.reduce((n, r) => n + (r.maxPoints ?? 0), 0);

  const rows: SortRow[] = shown.map((r) => ({
    id: r.lineId,
    values: {
      lineId: r.lineId,
      line: r.line,
      section: r.section,
      kind: r.kind,
      maxPoints: r.maxPoints,
      observed: r.observed,
      awarded: r.awarded,
    },
    text: {
      observed: r.observed ?? "not exercised",
      awarded: r.awarded === null ? "not exercised" : String(r.awarded),
    },
    muted: ["observed", "awarded"],
  }));

  return (
    <div className="stack-4">
      <p className="body">
        A Day-60 score is 100 points against the rubric below, run against a live deployment sixty days after go-live.
        Every observed value is empty because no deployment has been exercised. Charter 4.5.1: an exercise that cannot
        meet the safety conditions is not run, and the affected rubric lines are scored &quot;not exercised&quot;, never
        assumed.
      </p>

      <div className="filters">
        <div>
          <label className="label" htmlFor={`${base}-section`}>
            Rubric section
          </label>
          <select id={`${base}-section`} className="select" value={section} onChange={(e) => setSection(e.target.value)}>
            <option value="all">Every section — {rubric.reduce((n, r) => n + (r.maxPoints ?? 0), 0)} points</option>
            {sections.map((sec) => (
              <option key={sec} value={sec}>
                {SECTION_NAMES[sec] ?? sec}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="filter-note">
        {shown.length} scoring lines shown, {pointsShown} points of the {rubric.reduce((n, r) => n + (r.maxPoints ?? 0), 0)}{" "}
        the rubric allocates.
      </p>

      <SortableTable
        caption="Day-60 rubric lines, read from day-60/scoresheet.csv"
        columns={[
          { key: "lineId", label: "Line", type: "text", sortable: true },
          { key: "line", label: "What is scored", type: "text", sortable: true },
          { key: "kind", label: "Kind", type: "text", sortable: true },
          { key: "maxPoints", label: "Points", type: "number", sortable: true },
          { key: "observed", label: "Observed", type: "text", sortable: true },
          { key: "awarded", label: "Awarded", type: "number", sortable: true },
        ]}
        rows={rows}
        nullText="not exercised"
        footnote="A ratio line scores full points where the observed value meets the contractual target, half where it is up to twice the target, and zero beyond that or where the contract carries no target. The bands are in day-60/rubric.md section 3.3."
      />

      {context.length > 0 ? (
        <TableWrap label="What the assessor records before scoring">
          <table className="table table-dense">
            <caption>
              Recorded before any line is scored. A Day-60 score is only comparable with another Day-60 score run at the
              same tier, so the tier is printed beside the score.
            </caption>
            <thead>
              <tr>
                <th scope="col">Field</th>
                <th scope="col">What goes in it</th>
                <th scope="col">Recorded</th>
              </tr>
            </thead>
            <tbody>
              {context.map((c) => (
                <tr key={c.lineId}>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    {c.line}
                  </th>
                  <td>{c.measure || c.note}</td>
                  <td className="not-run">not exercised</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      ) : null}

      <TableWrap label="Day-60 point allocation">
        <table className="table table-dense">
          <caption>Point allocation, and what has been awarded.</caption>
          <thead>
            <tr>
              <th scope="col">Section</th>
              <th scope="col" className="numeric">
                Points available
              </th>
              <th scope="col" className="numeric">
                Points awarded
              </th>
            </tr>
          </thead>
          <tbody>
            {totals.map((t) => (
              <tr key={t.lineId}>
                <th scope="row" style={{ fontWeight: 400 }}>
                  {t.line}
                </th>
                <td className="numeric">{t.maxPoints ?? "not stated"}</td>
                <td className="numeric not-run">{t.awarded === null ? "not exercised" : t.awarded}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </div>
  );
}
