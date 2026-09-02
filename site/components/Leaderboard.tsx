"use client";

import { useId, useMemo, useState } from "react";
import type { Column, Dimension, Row } from "@/lib/data";
import { SortableTable, type SortRow } from "@/components/SortableTable";

export type LeaderboardProps = {
  caption: string;
  columns: Column[];
  rows: Row[];
  /** What one row is measured over: documents, contacts, work items, deployments. */
  unitPlural: string;
  tiers: Dimension[];
  languages: Dimension[];
  /** "<tier>|<language>" to the number of units in that cell of the labelled set. */
  cells: Record<string, number>;
  total: number | null;
  /** Set when the suite has no language dimension. The control is disabled and says why. */
  noLanguageDimension?: string;
  /** Set when the suite has no labelled set at all, so a slice carries no count. */
  noLabelledSet?: string;
  emptyMessage?: string;
};

const NOT_RUN = "not run";

// Caps stop one long cell from stretching the table past the grid. Nothing is truncated:
// the text wraps inside the cap, and the verbatim reason is published under the table.
const CAPS: Record<string, number> = { system: 17, provider: 12, modelVersion: 16, status: 26 };

/**
 * The leaderboard: one row per system, sortable on every column, filtered by difficulty
 * tier and by language. The filters change the denominator a row would be measured over,
 * which is printed above the table; they do not change which systems appear.
 */
export function Leaderboard({
  caption,
  columns,
  rows,
  unitPlural,
  tiers,
  languages,
  cells,
  total,
  noLanguageDimension,
  noLabelledSet,
  emptyMessage,
}: LeaderboardProps) {
  const [tier, setTier] = useState("all");
  const [language, setLanguage] = useState("all");
  const base = useId();

  const sliceCount = useMemo(() => {
    if (total === null) return null;
    if (tier === "all" && language === "all") return total;
    if (tier !== "all" && language !== "all") return cells[`${tier}|${language}`] ?? 0;
    if (tier !== "all") return tiers.find((t) => t.key === tier)?.count ?? null;
    return languages.find((l) => l.key === language)?.count ?? null;
  }, [tier, language, total, cells, tiers, languages]);

  const sliceLabel = [
    tier === "all" ? "every tier" : tier,
    noLanguageDimension
      ? null
      : language === "all"
        ? "every language"
        : (languages.find((l) => l.key === language)?.label ?? language),
  ]
    .filter(Boolean)
    .join(", ");

  const tableRows: SortRow[] = rows.map((r) => {
    const values: Record<string, number | string | null> = {};
    const text: Record<string, string> = {};
    const muted: string[] = [];
    for (const c of columns) {
      if (c.key === "system") values[c.key] = r.system;
      else if (c.key === "provider") values[c.key] = r.provider || null;
      else if (c.key === "runs") values[c.key] = r.runs;
      else if (c.key === "modelVersion") {
        values[c.key] = r.modelVersion ?? null;
        if (!r.modelVersion) {
          text[c.key] = "not set";
          muted.push(c.key);
        }
      } else {
        const v = r.cells[c.key];
        values[c.key] = v === undefined ? null : v;
      }
    }
    values.status = r.status;
    text.status = r.reason ? `${r.status} — ${r.reason}` : r.status;
    muted.push("status");
    return { id: r.id, values, text, muted };
  });

  const allColumns: (Column & { cap?: number })[] = [
    ...columns.map((c) => ({ ...c, cap: CAPS[c.key] })),
    { key: "status", label: "Status", type: "text" as const, sortable: true, cap: CAPS.status },
  ];

  const footnote = [
    "Column headings sort the table. A figure that was never produced sorts last in both directions; it is not a low score.",
    columns.some((c) => c.key === "modelVersion")
      ? 'A model version reading "not set" is a decision a person makes before a run, per charter 10.3; the harness stores no version string that nobody chose.'
      : null,
    "Charter 5.6: our own system is scored by the same harness, from the same commit, with the same prompts, and sits wherever the sort puts it, with no highlight and no position advantage.",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <div className="filters">
        <div>
          <label className="label" htmlFor={`${base}-tier`}>
            Difficulty tier
          </label>
          <select
            id={`${base}-tier`}
            className="select"
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            disabled={tiers.length === 0}
          >
            <option value="all">Every tier</option>
            {tiers.map((t) => (
              <option key={t.key} value={t.key}>
                {t.count === null ? t.label : `${t.label} — ${t.count.toLocaleString("en-GB")} ${unitPlural}`}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor={`${base}-language`}>
            Language
          </label>
          <select
            id={`${base}-language`}
            className="select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={Boolean(noLanguageDimension) || languages.length === 0}
          >
            <option value="all">{noLanguageDimension ? "Not applicable" : "Every language"}</option>
            {languages.map((l) => (
              <option key={l.key} value={l.key}>
                {l.count === null ? l.label : `${l.label} — ${l.count.toLocaleString("en-GB")} ${unitPlural}`}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="filter-note" role="status">
        {noLanguageDimension ? `${noLanguageDimension} ` : null}
        {sliceCount === null
          ? `Selected slice: ${sliceLabel}. ${noLabelledSet ?? "No count is published for this slice."}`
          : `Selected slice: ${sliceLabel}. ${sliceCount.toLocaleString("en-GB")} ${unitPlural} in the labelled set.`}{" "}
        The filter changes the denominator a row would be measured over. Every measured cell reads {NOT_RUN} in every
        slice.
      </p>

      <div style={{ marginTop: 24 }}>
        <SortableTable
          caption={caption}
          columns={allColumns}
          rows={tableRows}
          emptyMessage={emptyMessage}
          footnote={footnote}
        />
      </div>
    </div>
  );
}
