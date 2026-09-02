import Link from "next/link";
import { benchmarks } from "@/lib/data";
import { Rail, Reading, Section, SectionHeading, Wide } from "@/components/Section";
import { StatusBanner } from "@/components/StatusBanner";
import { TableWrap } from "@/components/TableWrap";
import { Blocks } from "@/components/Markdown";
import { pageMeta, REPO, REPO_PUBLISHED, REPO_URL } from "@/lib/site";
import { charterSection } from "@/lib/data";

export const metadata = pageMeta({
  title: "Benchmarks",
  description:
    "Four benchmark suites for document, voice, back-office and AI-operations systems, with every definition written so a BPO can put it in a contract.",
  path: "/",
});

export default function Page() {
  const { charter, suites, sources, generatedAt, harness } = benchmarks;
  const purpose = charterSection("1");
  const purposeLead = purpose?.blocks.find((b) => b.t === "p" && b.text.startsWith("1.1"));
  const purposeSecond = purpose?.blocks.find((b) => b.t === "p" && b.text.startsWith("1.2"));

  return (
    <>
      <Section hero>
        <Reading>
          <h1 className="page-title">Four benchmark suites</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            {purposeLead && purposeLead.t === "p" ? purposeLead.text.replace(/^1\.1\s+/, "") : ""}
          </p>
          <p className="body" style={{ marginTop: 24 }}>
            {purposeSecond && purposeSecond.t === "p" ? purposeSecond.text.replace(/^1\.2\s+/, "") : ""}
          </p>
        </Reading>
        <Rail label={`Charter ${charter.version}, written ${charter.written}`}>
          <p>
            Every figure on this site is read at build time from the files in this repository. Nothing on any page is
            typed by hand. On {generatedAt} the build read {sources.length} source files.
          </p>
          <p>
            Harness <code>entail-bench</code> {harness.version ?? "not set"}. Data CC BY 4.0, code MIT, in{" "}
            <a href={REPO_URL}>{REPO}</a>
            {REPO_PUBLISHED ? "." : " — not published yet."}
          </p>
        </Rail>
      </Section>

      <Section labelledBy="status">
        <Wide>
          <SectionHeading id="status">Status</SectionHeading>
          <StatusBanner />
        </Wide>
      </Section>

      <Section labelledBy="suites">
        <Wide>
          <SectionHeading id="suites">The four suites</SectionHeading>
          <TableWrap label="The four suites">
            <table className="table">
              <caption>
                One suite per line of work. Each scores a different unit, and the unit decides every denominator.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Suite</th>
                  <th scope="col">What it measures</th>
                  <th scope="col">Unit scored</th>
                  <th scope="col">Headline metric</th>
                  <th scope="col">Runs</th>
                </tr>
              </thead>
              <tbody>
                {suites.map((s) => (
                  <tr key={s.slug}>
                    <th scope="row" style={{ fontWeight: 400 }}>
                      <Link href={`/${s.slug}`}>{s.name}</Link>
                    </th>
                    <td>{s.measures}</td>
                    <td>{s.unit}</td>
                    <td>{s.headline}</td>
                    <td className="not-run">{s.charterStatus?.runs ?? "not run"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="what-exists">
        <Wide>
          <SectionHeading id="what-exists">What exists, per suite</SectionHeading>
          <TableWrap label="What exists per suite">
            <table className="table">
              <caption>
                Read from the dataset manifests, the harness registry and the results folders when this page was built.
                Honest Containment publishes its whole public split, and holds a separate private set beside it; the
                other two publish a sample drawn to the same tier and language mix as the whole set.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Suite</th>
                  <th scope="col">Dataset</th>
                  <th scope="col" className="numeric">
                    Labelled items
                  </th>
                  <th scope="col" className="numeric">
                    Published sample
                  </th>
                  <th scope="col" className="numeric">
                    Held privately
                  </th>
                  <th scope="col">Results folder</th>
                  <th scope="col" className="numeric">
                    Systems scored
                  </th>
                </tr>
              </thead>
              <tbody>
                {suites.map((s) => (
                  <tr key={s.slug}>
                    <th scope="row" style={{ fontWeight: 400 }}>
                      <Link href={`/${s.slug}`}>{s.name}</Link>
                    </th>
                    <td className={s.dataset.present ? undefined : "not-run"}>
                      {s.dataset.present ? `v${s.dataset.version}, seed ${s.dataset.seed}` : "not a dataset"}
                    </td>
                    <td className="numeric">
                      {s.dataset.cross?.total ? s.dataset.cross.total.toLocaleString("en-GB") : "not applicable"}
                    </td>
                    <td className="numeric">
                      {s.dataset.sampleCount ? s.dataset.sampleCount.toLocaleString("en-GB") : "not applicable"}
                    </td>
                    <td className="numeric">
                      {s.dataset.privateCount ? s.dataset.privateCount.toLocaleString("en-GB") : "not applicable"}
                    </td>
                    <td className={s.results.dir ? undefined : "not-run"}>{s.results.dir ?? "does not exist"}</td>
                    <td className="numeric not-run">0</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="rules">
        <Wide>
          <SectionHeading id="rules">The rules this runs under</SectionHeading>
        </Wide>
        <Reading>
          <div className="doc">
            <Blocks
              blocks={(charterSection("5")?.blocks ?? []).filter(
                (b) => b.t === "p" && /^5\.(1|2|3|4|5|6|7|8) /.test(b.text),
              )}
              tableLabel="Neutrality rules"
            />
          </div>
        </Reading>
        <Rail label={`Charter ${charter.version}, section 5`}>
          <p>
            <Link href="/methodology#5-neutrality-rules">The neutrality rules in full</Link>, and{" "}
            <Link href="/methodology#9-limitations">what these benchmarks cannot tell a buyer</Link>.
          </p>
          <p>
            <Link href="/disputes">Anyone may dispute any figure.</Link> The process is public and its outcomes are
            published whichever way they go.
          </p>
        </Rail>
      </Section>

      <Section labelledBy="pages">
        <Wide>
          <SectionHeading id="pages">The rest of this site</SectionHeading>
          <div className="card-grid">
            <Link className="card" href="/methodology">
              <p className="h-title">Methodology</p>
              <p className="note" style={{ marginTop: 8 }}>
                The charter in full: every metric definition, the tier schemes, the neutrality rules, the data ethics,
                the versioning, the limitations and the current status.
              </p>
            </Link>
            <Link className="card" href="/run-it-yourself">
              <p className="h-title">Run it yourself</p>
              <p className="note" style={{ marginTop: 8 }}>
                Install the harness, point it at your own folder of documents, and score any system through the same
                scorer.
              </p>
            </Link>
            <Link className="card" href="/changelog">
              <p className="h-title">Changelog</p>
              <p className="note" style={{ marginTop: 8 }}>
                What has changed, at what version, and what is still at version one because nothing has been published.
              </p>
            </Link>
            <Link className="card" href="/disputes">
              <p className="h-title">Disputes</p>
              <p className="note" style={{ marginTop: 8 }}>
                How to dispute a figure, what happens next, and the log of every dispute raised.
              </p>
            </Link>
          </div>
        </Wide>
      </Section>
    </>
  );
}
