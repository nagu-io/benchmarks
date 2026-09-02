import type { CSSProperties, ReactNode } from "react";

/** A table that scrolls sideways on narrow screens. Focusable, so keyboard users can scroll it. */
export function TableWrap({ label, children, style }: { label: string; children: ReactNode; style?: CSSProperties }) {
  return (
    <div className="table-wrap" tabIndex={0} role="group" aria-label={label} style={style}>
      {children}
    </div>
  );
}
