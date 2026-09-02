import Link from "next/link";
import { benchmarks, charterSection } from "@/lib/data";
import { Rail, Reading, Section, SectionHeading, Wide } from "@/components/Section";
import { Blocks } from "@/components/Markdown";
import { TableWrap } from "@/components/TableWrap";
import { pageMeta } from "@/lib/site";

export const metadata = pageMeta({
  title: "Changelog",
  description:
    "What has changed in the datasets, the harness and the charter, at which version, and what has not been published yet.",
  path: "/changelog",
});

export default function Page() {
  const { charter, suites, harness, clauses, sources, generatedAt } = benchmarks;
  const versioning = charterSection("7");
  const cadence = charterSection("8");
  const cadenceBlocks = (cadence?.blocks ?? []).filter((b) => b.t === "p" && /^8\.(1|2|3) /.test(b.text));

  return (
    <>
      <Section hero>
        <Reading>
          <h1 className="page-title">Changelog</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            No release has been published, so there is no release changelog entry. Everything below is at its first
            version.
          </p>
          <p className="body" style={{ marginTop: 24 }}>
            A superseded table stays published, marked superseded, with a link to the version that replaced it and a
            changelog entry saying what changed. Nothing is quietly deleted or overwritten; that is the whole point of
            publishing the previous number.
          </p>
        </Reading>
        <Rail label="Cadence">
          <p>
            Quarterly. Each release publishes, per suite: the leaderboards, the calibration report, the findings, the
            reproduce commands, the changelog, the public dataset sample and the disputes log. Between releases a
            correction may be published at any time, and it carries its own entry.
          </p>
          <p>
            The first release date is not set. It waits on a run, which waits on the items in{" "}
            <Link href="/methodology#10-current-status">charter section 10.3</Link>.
          </p>
        </Rail>
      </Section>

      <Section labelledBy="versions-now">
        <Wide>
          <SectionHeading id="versions-now">Versions in force</SectionHeading>
          <TableWrap label="Versions in force">
            <table className="table">
              <caption>
                Read from the charter, the dataset manifests and the harness when this page was built, on{" "}
                {generatedAt}, across {sources.length} source files.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Component</th>
                  <th scope="col">Version</th>
                  <th scope="col">First published</th>
                  <th scope="col">Changes since</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    Charter and methodology
                  </th>
                  <td>{charter.version ?? "not set"}</td>
                  <td className="not-run">not published</td>
                  <td className="not-run">none — first version</td>
                </tr>
                <tr>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    Contract clauses
                  </th>
                  <td>{clauses.version ?? "not set"}</td>
                  <td className="not-run">not published</td>
                  <td className="not-run">none — first version</td>
                </tr>
                <tr>
                  <th scope="row" style={{ fontWeight: 400 }}>
                    Harness, entail-bench
                  </th>
                  <td>{harness.version ?? "not set"}</td>
                  <td className="not-run">not published</td>
                  <td className="not-run">none — first version</td>
                </tr>
                {suites.map((s) => (
                  <tr key={s.slug}>
                    <th scope="row" style={{ fontWeight: 400 }}>
                      Dataset: {s.name}
                    </th>
                    <td className={s.dataset.present ? undefined : "not-run"}>
                      {s.dataset.present ? s.dataset.version : "not a dataset"}
                    </td>
                    <td className="not-run">not published</td>
                    <td className="not-run">none — first version</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="entries">
        <Wide>
          <SectionHeading id="entries">Release entries</SectionHeading>
          <TableWrap label="Release entries">
            <table className="table">
              <caption>
                One file per release, listing dataset changes with their version bump, harness changes with their commit
                range, prompt changes, systems added or removed with the reason, corrections made under the disputes
                process, tables marked superseded, and any run discarded under charter 5.12.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Release</th>
                  <th scope="col">Date</th>
                  <th scope="col">Suites</th>
                  <th scope="col">What changed</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={4} className="not-run">
                    No release has been published. The first release publishes when a suite has been run, and it will
                    list every table it contains.
                  </td>
                </tr>
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="rules">
        <Wide>
          <SectionHeading id="rules">What counts as a version change</SectionHeading>
        </Wide>
        <Reading>
          <div className="doc">
            <Blocks blocks={versioning?.blocks ?? []} tableLabel="Versioning" />
          </div>
        </Reading>
        <Rail label={`Charter ${charter.version}, sections 7 and 8`}>
          <div className="doc" style={{ fontSize: 13, lineHeight: 1.45 }}>
            <Blocks blocks={cadenceBlocks} tableLabel="Cadence" />
          </div>
        </Rail>
      </Section>
    </>
  );
}
