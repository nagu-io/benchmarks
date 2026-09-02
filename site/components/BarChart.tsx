/**
 * The three marks, in a chart. A yellow fill is the share the machine carried; a red
 * stroke under the remainder is the share a person had to touch; every rule is a
 * 1px hairline in rule grey. Review red is a mark, never a fill, so the reviewed share
 * is drawn as a 2px underline rather than a block of colour.
 *
 * Where there is nothing to plot the chart renders an explicit empty state. It never
 * renders example bars.
 */

export type Bar = {
  label: string;
  /** 0 to 1. null means the figure was never produced. */
  automated: number | null;
  /** Right-hand annotation, e.g. the denominator. */
  note?: string;
};

const PAPER = "#E4E8EA";
const INK = "#1C2329";
const YELLOW = "#F5E9A0";
const RED = "#B8321A";
const RULE = "#B7BEC3";

export function BarChart({
  title,
  bars,
  automatedLabel = "Carried without a person",
  reviewedLabel = "Reached a person",
  emptyMessage,
  scaleLabel = "0 to 100 percent of the items admitted in that tier",
}: {
  title: string;
  bars: Bar[];
  automatedLabel?: string;
  reviewedLabel?: string;
  emptyMessage: string;
  scaleLabel?: string;
}) {
  const plottable = bars.filter((b) => b.automated !== null);

  if (plottable.length === 0) {
    return (
      <figure className="chart" style={{ margin: 0 }}>
        <figcaption className="ui" style={{ fontWeight: 500, marginBottom: 16 }}>
          {title}
        </figcaption>
        <div className="chart-empty" style={{ border: `1px solid ${RULE}`, borderRadius: 2 }}>
          <p className="note" style={{ maxWidth: "44ch" }}>
            {emptyMessage}
          </p>
        </div>
      </figure>
    );
  }

  const rowH = 44;
  const labelW = 84;
  const noteW = 168;
  const width = 880;
  const barW = width - labelW - noteW - 16;
  const height = bars.length * rowH + 28;

  return (
    <figure className="chart" style={{ margin: 0 }}>
      <figcaption className="ui" style={{ fontWeight: 500, marginBottom: 16 }}>
        {title}
      </figcaption>
      <div style={{ overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          style={{ minWidth: 520, display: "block" }}
          role="img"
          aria-label={`${title}. ${scaleLabel}.`}
        >
          {bars.map((b, i) => {
            const y = i * rowH + 8;
            const share = b.automated ?? 0;
            const fillW = Math.max(0, Math.min(1, share)) * barW;
            return (
              <g key={b.label}>
                <text x={0} y={y + 18} fontSize={14} fill={INK} fontFamily="inherit">
                  {b.label}
                </text>
                <rect x={labelW} y={y} width={barW} height={24} fill={PAPER} stroke={RULE} strokeWidth={1} />
                {fillW > 0 ? <rect x={labelW} y={y} width={fillW} height={24} fill={YELLOW} /> : null}
                {/* The remainder reached a person: a red mark under it, not a red fill. */}
                {fillW < barW ? (
                  <line
                    x1={labelW + fillW}
                    y1={y + 25}
                    x2={labelW + barW}
                    y2={y + 25}
                    stroke={RED}
                    strokeWidth={2}
                  />
                ) : null}
                <line x1={labelW} y1={y} x2={labelW} y2={y + 24} stroke={RULE} strokeWidth={1} />
                <text x={labelW + barW + 16} y={y + 18} fontSize={13} fill="#585E63" fontFamily="inherit">
                  {b.note ?? ""}
                </text>
              </g>
            );
          })}
          <line
            x1={labelW}
            y1={bars.length * rowH + 8}
            x2={labelW + barW}
            y2={bars.length * rowH + 8}
            stroke={RULE}
            strokeWidth={1}
          />
          <text x={labelW} y={bars.length * rowH + 24} fontSize={13} fill="#585E63" fontFamily="inherit">
            0
          </text>
          <text
            x={labelW + barW}
            y={bars.length * rowH + 24}
            fontSize={13}
            fill="#585E63"
            fontFamily="inherit"
            textAnchor="end"
          >
            100
          </text>
        </svg>
      </div>
      <ul className="chart-legend">
        <li>
          <span className="swatch swatch-automated" aria-hidden="true" /> {automatedLabel}
        </li>
        <li>
          <span className="swatch swatch-reviewed" aria-hidden="true" /> {reviewedLabel}
        </li>
      </ul>
    </figure>
  );
}
