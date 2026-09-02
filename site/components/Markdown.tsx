import { Fragment, type ReactNode } from "react";
import type { Block } from "@/lib/data";
import { TableWrap } from "@/components/TableWrap";

/**
 * Renders the block list `scripts/build-data.mjs` produces from a source markdown file.
 * The site never authors prose that duplicates a source document; it renders the source.
 */

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;

export function Inline({ text }: { text: string }): ReactNode {
  const parts = text.split(INLINE).filter((p) => p !== "");
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} style={{ fontWeight: 500 }}>
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
        const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
        if (link) {
          const href = link[2] ?? "";
          return (
            <a key={i} href={href}>
              {link[1]}
            </a>
          );
        }
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </>
  );
}

export function Blocks({ blocks, tableLabel = "Table" }: { blocks: Block[]; tableLabel?: string }) {
  return (
    <>
      {blocks.map((b, i) => {
        switch (b.t) {
          case "h": {
            const Tag = (b.level <= 2 ? "h2" : b.level === 3 ? "h3" : "h4") as "h2" | "h3" | "h4";
            return (
              <Tag key={i} id={b.id}>
                <Inline text={b.text} />
              </Tag>
            );
          }
          case "p":
            return (
              <p key={i}>
                <Inline text={b.text} />
              </p>
            );
          case "ul":
            return (
              <ul key={i} className="prose-list">
                {b.items.map((it, j) => (
                  <li key={j}>
                    <Inline text={it} />
                  </li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={i} className="prose-list">
                {b.items.map((it, j) => (
                  <li key={j}>
                    <Inline text={it} />
                  </li>
                ))}
              </ol>
            );
          case "table":
            return (
              <TableWrap key={i} label={`${tableLabel}: ${b.head.join(", ")}`}>
                <table className="table table-dense">
                  <thead>
                    <tr>
                      {b.head.map((h, j) => (
                        <th key={j} scope="col">
                          <Inline text={h} />
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((r, j) => (
                      <tr key={j}>
                        {r.map((c, k) => (
                          <td key={k}>
                            <Inline text={c} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            );
          case "code":
            return (
              <pre key={i} className="code">
                <code>{b.code}</code>
              </pre>
            );
          case "quote":
            return (
              <blockquote key={i}>
                <Blocks blocks={b.blocks} tableLabel={tableLabel} />
              </blockquote>
            );
          case "hr":
            return <hr key={i} style={{ border: 0, borderTop: "1px solid var(--color-rule)" }} />;
          default:
            return null;
        }
      })}
    </>
  );
}
