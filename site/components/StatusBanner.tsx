import Link from "next/link";
import { benchmarks } from "@/lib/data";

/**
 * The banner every page carries while no suite has been run. Its wording is the charter's
 * own, sections 10.1 and 10.3, read at build time rather than retyped here.
 */
export function StatusBanner({ suite }: { suite?: { name: string; charterStatus: { status: string } | null } }) {
  const { charter } = benchmarks;
  return (
    <div className="banner">
      <p className="banner-title condensed">No suite has been run</p>
      <p className="body" style={{ fontSize: 15 }}>
        {charter.noRunStatement ??
          "No suite has been run. Every results table on this site reads not run, with the reason."}
      </p>
      {suite?.charterStatus ? (
        <p className="body" style={{ fontSize: 15 }}>
          {suite.name}: {suite.charterStatus.status}.
        </p>
      ) : null}
      {charter.firstRunNeeds ? (
        <p className="body" style={{ fontSize: 15 }}>
          {charter.firstRunNeeds}
        </p>
      ) : null}
      <p className="note">
        Charter {charter.version} section 10. A row with no run is written &quot;not run&quot; with the reason. It is
        never estimated, extrapolated, interpolated from a neighbouring tier, or replaced with a plausible-looking
        figure. <Link href="/methodology#10-current-status">The status section in full</Link>.
      </p>
    </div>
  );
}
