"use client";

import { useId, useMemo, useState } from "react";
import { TableWrap } from "@/components/TableWrap";

export type SortDirection = "ascending" | "descending" | "none";

export type SortColumn = {
  key: string;
  label: string;
  type: "text" | "number";
  sortable: boolean;
  /** Cap the cell text at this many characters wide, so one long cell cannot stretch the table. */
  cap?: number;
};

export type SortRow = {
  id: string;
  /** Cell values. null means the figure was never produced. */
  values: Record<string, number | string | null>;
  /** Cell text overrides, used where a null needs a reason rather than the default word. */
  text?: Record<string, string>;
  /** Cells rendered at annotation weight, typically the ones that read "not run". */
  muted?: string[];
};

/**
 * A real table with client-side sorting. No library: a button inside each sortable
 * `th`, `aria-sort` on the header, and a live region that announces the change.
 * Clicking cycles ascending, descending, unsorted.
 */
export function SortableTable({
  caption,
  columns,
  rows,
  nullText = "not run",
  emptyMessage,
  footnote,
}: {
  caption: string;
  columns: SortColumn[];
  rows: SortRow[];
  nullText?: string;
  emptyMessage?: string;
  footnote?: string;
}) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [direction, setDirection] = useState<SortDirection>("none");
  const liveId = useId();

  const sorted = useMemo(() => {
    if (!sortKey || direction === "none") return rows;
    const factor = direction === "ascending" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = a.values[sortKey] ?? null;
      const bv = b.values[sortKey] ?? null;
      // A figure that was never produced sorts last in both directions. It is not a low score.
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * factor;
      return String(av).localeCompare(String(bv), "en", { numeric: true }) * factor;
    });
  }, [rows, sortKey, direction]);

  function toggle(key: string) {
    if (sortKey !== key) {
      setSortKey(key);
      setDirection("ascending");
    } else if (direction === "ascending") {
      setDirection("descending");
    } else {
      setSortKey(null);
      setDirection("none");
    }
  }

  const sortLabel =
    sortKey && direction !== "none"
      ? `Sorted by ${columns.find((c) => c.key === sortKey)?.label ?? sortKey}, ${direction}.`
      : "No sort applied. Rows are in source order.";

  return (
    <div>
      <p className="sr-only" id={liveId} aria-live="polite">
        {sortLabel}
      </p>
      <TableWrap label={caption}>
        <table className="table">
          <caption>{caption}</caption>
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sortKey === c.key && direction !== "none";
                // A numeric heading wraps inside a narrow cap rather than forcing the table wider.
                const headCap = c.cap ?? (c.type === "number" ? 13 : undefined);
                return (
                  <th
                    key={c.key}
                    scope="col"
                    className={c.type === "number" ? "numeric" : undefined}
                    aria-sort={active ? direction : "none"}
                  >
                    {c.sortable ? (
                      <button
                        type="button"
                        className="sort-button"
                        onClick={() => toggle(c.key)}
                        aria-label={`${c.label}, sort ${active && direction === "ascending" ? "descending" : "ascending"}`}
                      >
                        <span style={headCap ? { maxWidth: `${headCap}ch` } : undefined}>{c.label}</span>
                        <span className="sort-state" aria-hidden="true">
                          {active ? (direction === "ascending" ? "↑" : "↓") : "↕"}
                        </span>
                      </button>
                    ) : (
                      c.label
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="not-run">
                  {emptyMessage ?? `No row has been produced. ${nullText}.`}
                </td>
              </tr>
            ) : (
              sorted.map((r) => (
                <tr key={r.id}>
                  {columns.map((c, i) => {
                    const raw = r.values[c.key] ?? null;
                    const body = r.text?.[c.key] ?? (raw === null ? nullText : typeof raw === "number" ? raw.toLocaleString("en-GB") : String(raw));
                    const muted = r.muted?.includes(c.key) || (raw === null && !r.text?.[c.key]);
                    const className = [c.type === "number" ? "numeric" : "", muted ? "not-run" : ""]
                      .filter(Boolean)
                      .join(" ");
                    // overflow-wrap lets a long identifier such as an environment variable name
                    // break inside the cap instead of forcing the whole table wider.
                    const content = c.cap ? (
                      <span style={{ display: "block", maxWidth: `${c.cap}ch`, overflowWrap: "anywhere" }}>{body}</span>
                    ) : (
                      body
                    );
                    if (i === 0) {
                      return (
                        <th key={c.key} scope="row" style={{ fontWeight: 400 }}>
                          {content}
                        </th>
                      );
                    }
                    return (
                      <td key={c.key} className={className || undefined}>
                        {content}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </TableWrap>
      {footnote ? <p className="filter-note">{footnote}</p> : null}
    </div>
  );
}
