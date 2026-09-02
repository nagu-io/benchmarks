import type { ReactNode } from "react";

/** A page section: a hairline on top, the 12-column grid inside. Same structure as the main site. */
export function Section({
  children,
  id,
  hero,
  tight,
  labelledBy,
}: {
  children: ReactNode;
  id?: string;
  hero?: boolean;
  tight?: boolean;
  labelledBy?: string;
}) {
  const classes = ["section", hero ? "section-hero" : "", tight ? "section-tight" : ""].filter(Boolean).join(" ");
  return (
    <section id={id} className={classes} aria-labelledby={labelledBy}>
      <div className="container">
        <div className="grid12">{children}</div>
      </div>
    </section>
  );
}

export function Reading({ children }: { children: ReactNode }) {
  return <div className="reading">{children}</div>;
}

export function Wide({ children }: { children: ReactNode }) {
  return <div className="wide">{children}</div>;
}

export function Full({ children }: { children: ReactNode }) {
  return <div className="full">{children}</div>;
}

export function Rail({ label, children }: { label?: string; children?: ReactNode }) {
  return (
    <div className="rail">
      {label ? <p>{label}</p> : null}
      {children}
    </div>
  );
}

export function SectionHeading({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="h-section" style={{ marginBottom: 24 }}>
      {children}
    </h2>
  );
}
