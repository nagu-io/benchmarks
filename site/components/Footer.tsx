import Link from "next/link";
import { benchmarks } from "@/lib/data";
import { EMAILS, MAIN_SITE_URL, REPO, REPO_PUBLISHED, REPO_URL, SUITE_LINKS } from "@/lib/site";

export function Footer() {
  const { charter, harness, generatedAt, sources } = benchmarks;
  return (
    <footer className="footer">
      <div className="container">
        <div className="grid12">
          <div className="wide footer-columns">
            <div className="footer-col">
              <p className="wordmark">
                Entailment Labs <span className="qualifier">benchmarks</span>
              </p>
              <p className="note" style={{ marginTop: 12, maxWidth: "30ch" }}>
                Four suites, published with the definitions, the data, the harness and the disputes process.
              </p>
            </div>
            <div className="footer-col">
              <p className="ui" style={{ fontWeight: 500, marginBottom: 12 }}>
                Suites
              </p>
              <ul className="footer-list">
                {SUITE_LINKS.map((s) => (
                  <li key={s.href}>
                    <Link href={s.href}>{s.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="footer-col">
              <p className="ui" style={{ fontWeight: 500, marginBottom: 12 }}>
                How this is run
              </p>
              <ul className="footer-list">
                <li>
                  <Link href="/methodology">Methodology</Link>
                </li>
                <li>
                  <Link href="/run-it-yourself">Run it yourself</Link>
                </li>
                <li>
                  <Link href="/changelog">Changelog</Link>
                </li>
                <li>
                  <Link href="/disputes">Disputes</Link>
                </li>
              </ul>
            </div>
            <div className="footer-col">
              <p className="ui" style={{ fontWeight: 500, marginBottom: 12 }}>
                Elsewhere
              </p>
              <ul className="footer-list">
                <li>
                  <a href={REPO_URL}>{REPO}</a>
                  {REPO_PUBLISHED ? null : <span className="note"> — not published yet</span>}
                </li>
                <li>
                  <a href={MAIN_SITE_URL}>entailmentlabs.com</a>
                </li>
                <li>
                  <a href={`mailto:${EMAILS.hello}`}>{EMAILS.hello}</a>
                </li>
              </ul>
            </div>
          </div>
          <div className="wide footer-bottom">
            <span>
              Charter {charter.version ?? "not set"} · harness {harness.version ?? "not set"} · data read from{" "}
              {sources.length} source files on {generatedAt}
            </span>
            <span>Data CC BY 4.0. Code MIT.</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
