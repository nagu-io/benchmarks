import Link from "next/link";
import { benchmarks, charterSection } from "@/lib/data";
import { Rail, Reading, Section, SectionHeading, Wide } from "@/components/Section";
import { Blocks } from "@/components/Markdown";
import { TableWrap } from "@/components/TableWrap";
import { EMAILS, pageMeta, REPO, REPO_PUBLISHED, REPO_URL } from "@/lib/site";

export const metadata = pageMeta({
  title: "Disputes",
  description:
    "How to dispute any figure published here, what happens next, and the log of every dispute raised, upheld or not.",
  path: "/disputes",
});

export default function Page() {
  const { charter } = benchmarks;
  const section8 = charterSection("8");
  const disputeBlocks = (section8?.blocks ?? []).filter((b) => {
    if (b.t === "p") return /^8\.(3|4)/.test(b.text);
    if (b.t === "table") return b.head[0] === "Step";
    return false;
  });

  return (
    <>
      <Section hero>
        <Reading>
          <h1 className="page-title">Disputes</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            Anyone may dispute any figure. The process is public and its outcomes are published whichever way they go.
          </p>
          <p className="body" style={{ marginTop: 24 }}>
            A dispute about our own system&apos;s row runs through the same steps and is marked in the log as a
            self-dispute, so a reader can count how many there have been and how they went. Nothing leaves the log: a
            dispute we lose stays visible, with the correction linked to it.
          </p>
        </Reading>
        <Rail label="How to raise one">
          <p>
            Open the &quot;dispute a result&quot; issue template in <a href={REPO_URL}>{REPO}</a>, or write to{" "}
            <a href={`mailto:${EMAILS.hello}`}>{EMAILS.hello}</a>.
          </p>
          {REPO_PUBLISHED ? null : (
            <p>
              The public repository is not created yet, so the issue template is not live. Until it is, the email route
              is the one that works.
            </p>
          )}
          <p>
            A dispute must name the table, the row, the dataset and harness versions, and what is wrong: a defect, or a
            disagreement with a definition.
          </p>
        </Rail>
      </Section>

      <Section labelledBy="log">
        <Wide>
          <SectionHeading id="log">The log</SectionHeading>
          <TableWrap label="Disputes log">
            <table className="table">
              <caption>
                Every dispute raised, its status, and its outcome. A dispute never pauses publication of the rest of a
                release: the disputed row is marked &quot;under dispute&quot; with a link to its entry, and the rest
                stands.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Raised</th>
                  <th scope="col">Table and row</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Status</th>
                  <th scope="col">Outcome</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={5} className="not-run">
                    No dispute has been raised. Nothing has been published to dispute: every results table reads
                    &quot;not run&quot;.
                  </td>
                </tr>
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="process">
        <Wide>
          <SectionHeading id="process">The process</SectionHeading>
          <p className="body" style={{ marginBottom: 24 }}>
            Read from charter {charter.version} sections 8.3 and 8.4 when this page was built.
          </p>
          <div className="doc">
            <Blocks blocks={disputeBlocks} tableLabel="Disputes process" />
          </div>
          <p className="note" style={{ marginTop: 24, maxWidth: "68ch" }}>
            The periods above read &quot;placeholder&quot; because they are a decision a person has not made yet. A
            placeholder in a published process is a defect, and it is listed as one:{" "}
            <Link href="/methodology#8-publishing-cadence-changelog-and-disputes">charter section 8</Link>.
          </p>
        </Wide>
      </Section>

      <Section labelledBy="conflict">
        <Wide>
          <SectionHeading id="conflict">Our interest in the outcome</SectionHeading>
        </Wide>
        <Reading>
          <p className="body">
            We are not neutral parties. We sell systems in all four categories these suites measure. The neutrality
            rules are the discipline we accept in return for publishing at all, this page is the route to hold us to
            them, and neither removes the interest we have in the outcome.
          </p>
        </Reading>
        <Rail label="Charter 5.10 and 9.10">
          <p>
            <Link href="/methodology#5-neutrality-rules">The neutrality rules</Link> ·{" "}
            <Link href="/methodology#9-limitations">The limitations</Link>
          </p>
        </Rail>
      </Section>
    </>
  );
}
