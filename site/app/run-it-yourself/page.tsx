import Link from "next/link";
import { benchmarks } from "@/lib/data";
import { Rail, Reading, Section, SectionHeading, Wide } from "@/components/Section";
import { Blocks } from "@/components/Markdown";
import { TableWrap } from "@/components/TableWrap";
import { pageMeta, repoPath, REPO_PUBLISHED, REPO_URL } from "@/lib/site";

export const metadata = pageMeta({
  title: "Run it yourself",
  description:
    "Install the harness, point it at your own folder of documents, and score any model, document service or pipeline through the same scorer that produces the tables here.",
  path: "/run-it-yourself",
});

export default function Page() {
  const { harness, suites, charter } = benchmarks;
  const readme = harness.readme ?? [];

  return (
    <>
      <Section hero>
        <Reading>
          <h1 className="page-title">Run it on your own data</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            The tables on this site are produced by a harness anyone can install. Point it at a folder of your own
            documents with your own labels and it scores any model, document service or pipeline through the same
            scorer, with the same prompts.
          </p>
          <p className="body" style={{ marginTop: 24 }}>
            Charter 9.1 is the reason this page exists: synthetic data is not your data. The formats, the tier mix, the
            languages and the error patterns here are ours. Yours differ, sometimes by more than the gap between two
            systems in a table.
          </p>
        </Reading>
        <Rail label={`entail-bench ${harness.version ?? "not set"}`}>
          <p>
            Python package, MIT licensed, in <code>{harness.readmePath}</code>. No key is stored in it, or anywhere else
            in it: each adapter names the environment variable it reads.
          </p>
          <p>
            <a href={repoPath("harness")}>harness/</a>
            {REPO_PUBLISHED ? null : (
              <>
                {" "}
                — the public repository <a href={REPO_URL}>{REPO_URL.replace("https://", "")}</a> is not created yet, so
                that link does not resolve.
              </>
            )}
          </p>
        </Rail>
      </Section>

      <Section labelledBy="adapters">
        <Wide>
          <SectionHeading id="adapters">What it can score</SectionHeading>
          <TableWrap label="Adapters in the harness registry">
            <table className="table">
              <caption>
                Read from <code>harness/src/entail_bench/data/models.yaml</code>. Charter 5.6: our own pipeline goes
                through the same adapter interface as anyone else&apos;s and appears in the same table.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Adapter</th>
                  <th scope="col">Provider</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Environment variables it reads</th>
                </tr>
              </thead>
              <tbody>
                {harness.models.map((m) => {
                  const envVars = (m as { env_vars?: string[] }).env_vars ?? [];
                  return (
                    <tr key={m.name}>
                      <th scope="row" style={{ fontWeight: 400 }}>
                        {m.name}
                      </th>
                      <td>{m.provider ?? "not stated"}</td>
                      <td>{(m.kind ?? "").replace(/_/g, " ")}</td>
                      <td className={envVars.length ? undefined : "not-run"}>
                        {envVars.length ? envVars.join(", ") : "none"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="quickstart">
        <Wide>
          <SectionHeading id="quickstart">The quickstart, in full</SectionHeading>
          <p className="body" style={{ marginBottom: 24 }}>
            Rendered from <code>{harness.readmePath}</code> when this page was built.
          </p>
          <div className="doc">
            <Blocks blocks={readme} tableLabel="Harness README" />
          </div>
        </Wide>
      </Section>

      <Section labelledBy="per-suite">
        <Wide>
          <SectionHeading id="per-suite">Per suite</SectionHeading>
          <TableWrap label="How to run each suite">
            <table className="table">
              <caption>Each suite&apos;s own commands sit on its page, read from its reproduce file.</caption>
              <thead>
                <tr>
                  <th scope="col">Suite</th>
                  <th scope="col">Run from</th>
                  <th scope="col">Commands published</th>
                </tr>
              </thead>
              <tbody>
                {suites.map((s) => (
                  <tr key={s.slug}>
                    <th scope="row" style={{ fontWeight: 400 }}>
                      <Link href={`/${s.slug}#reproduce`}>{s.name}</Link>
                    </th>
                    <td>
                      <code>{s.reproduce.source}</code>
                    </td>
                    <td className={s.reproduce.commands.length ? undefined : "not-run"}>
                      {s.reproduce.commands.length
                        ? `${s.reproduce.commands.length} command blocks`
                        : "none — this suite is a scripted exercise run by a person, not a command"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Wide>
      </Section>

      <Section labelledBy="honest">
        <Wide>
          <SectionHeading id="honest">What a run of ours would still need</SectionHeading>
        </Wide>
        <Reading>
          <p className="body">{charter.firstRunNeeds ?? "See charter section 10.3."}</p>
          <p className="body" style={{ marginTop: 16 }}>
            None of that is something an agent supplies. Until a person does, every table on this site reads &quot;not
            run&quot;. Your own run does not wait on ours: the harness, the datasets and the scorer are the same code,
            and a run on your material is the only one that describes your material.
          </p>
        </Reading>
        <Rail label="Cost">
          <p>
            Charter 9.4: cost figures are public list prices on a stated date, with no negotiated discount, no
            committed-use pricing and no caching effect. Your effective price will differ. Set a spend cap before a run.
          </p>
        </Rail>
      </Section>
    </>
  );
}
