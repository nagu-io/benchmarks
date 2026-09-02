import Link from "next/link";
import type { Block, Metric } from "@/lib/data";
import { paragraphLabel, stripNumber } from "@/lib/data";
import { Blocks, Inline } from "@/components/Markdown";

/**
 * The metric definitions for one suite, taken from charter section 3 at build time.
 *
 * The charter's arithmetic examples are left out here. They are invented numbers that
 * demonstrate a formula, they are marked as such in the charter, and beside a table of
 * "not run" they would read as results. They stay where they belong, in the charter.
 */
export function Definitions({ metrics, charterVersion }: { metrics: Metric[]; charterVersion: string | null }) {
  return (
    <div className="defs">
      {metrics.map((m) => (
        <MetricBlock key={m.section} metric={m} charterVersion={charterVersion} />
      ))}
    </div>
  );
}

function MetricBlock({ metric, charterVersion }: { metric: Metric; charterVersion: string | null }) {
  const rows: { label: string; blocks: Block[] }[] = [];
  let current: { label: string; blocks: Block[] } | null = null;

  for (const b of metric.blocks) {
    if (b.t === "p") {
      const { label, rest } = paragraphLabel(b.text);
      if (label) {
        current = { label, blocks: [{ t: "p", text: rest }] };
        rows.push(current);
        continue;
      }
      if (current) current.blocks.push({ t: "p", text: stripNumber(b.text) });
      else rows.push((current = { label: "Note", blocks: [{ t: "p", text: stripNumber(b.text) }] }));
      continue;
    }
    if (current) current.blocks.push(b);
    else rows.push((current = { label: "Note", blocks: [b] }));
  }

  return (
    <section className="def" aria-labelledby={`metric-${metric.section.replace(".", "-")}`}>
      <div className="def-head">
        <h3 className="h-title" id={`metric-${metric.section.replace(".", "-")}`}>
          {metric.name}
        </h3>
        <p className="note">
          Charter {charterVersion} section {metric.section} ·{" "}
          <Link href={`/methodology#${metric.anchor ?? ""}`}>read it in the charter</Link> · SOW clause {metric.clause}
        </p>
      </div>
      <dl>
        {rows.map((r, i) => (
          <div key={i} style={{ display: "contents" }}>
            <dt>{r.label}</dt>
            <dd>
              <Blocks blocks={r.blocks} tableLabel={`${metric.name}, ${r.label}`} />
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function ContractSentence({ text }: { text: string }) {
  return (
    <p className="body" style={{ fontSize: 15 }}>
      <Inline text={text} />
    </p>
  );
}
