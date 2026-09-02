import Link from "next/link";
import { benchmarks, suite as getSuite, type Suite } from "@/lib/data";
import { Full, Rail, Reading, Section, SectionHeading, Wide } from "@/components/Section";
import { StatusBanner } from "@/components/StatusBanner";
import { Leaderboard } from "@/components/Leaderboard";
import { BarChart } from "@/components/BarChart";
import { Definitions } from "@/components/Definitions";
import { Blocks } from "@/components/Markdown";
import { Reproduce } from "@/components/Reproduce";
import { PromptHashes, Provenance } from "@/components/Provenance";
import { TableWrap } from "@/components/TableWrap";
import { ReferencePolicy } from "@/components/ReferencePolicy";
import { Day60Rubric } from "@/components/Day60Rubric";
import { repoPath, REPO_PUBLISHED, REPO_URL } from "@/lib/site";

export function SuitePage({ slug }: { slug: string }) {
  const s: Suite = getSuite(slug);
  const { charter } = benchmarks;
  const cross = s.dataset.cross;
  const noLanguage =
    cross && cross.languages.length === 1 && cross.languages[0]?.key === "not-applicable"
      ? "This suite has no language dimension: a work item is a record, not a document or a conversation."
      : !cross
        ? "The tier here describes the exercise, not an item in a dataset: this suite has no labelled set and no language dimension."
        : undefined;

  const tierOptions = cross?.tiers ?? [];
  const languageOptions = noLanguage ? [] : (cross?.languages ?? []);
  const isDay60 = slug === "day-60";
  const unitNoun = s.dataset.unitPlural ?? "items";
  const leaderboardCaption = isDay60
    ? `${s.name} — deployments exercised against the published rubric, scored 0 to 100`
    : `${s.name} — every system scored by the same harness, from the same commit, on the same data`;
  const verbatim = s.results.rows.filter((r) => (r.reasonFull?.length ?? 0) > 0);
  const chartEmpty = isDay60
    ? `Nothing to plot. No deployment has been exercised, so there is no Day-60 score to draw. Charter 10.4: a chart with no run renders an empty state, not example bars.`
    : `Nothing to plot. No system has been run, so there is no ${s.headline.toLowerCase()} to draw. Charter 10.4: a chart with no run renders an empty state, not example bars. The reason for each row is in the status column above.`;

  return (
    <>
      <Section hero>
        <Reading>
          <p className="note" style={{ marginBottom: 12 }}>
            Suite · {s.line}
          </p>
          <h1 className="page-title">{s.name}</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            {s.measures}.
          </p>
        </Reading>
        <Rail label={`Charter ${charter.version}, section 2`}>
          <p>
            Unit scored: {s.unit.toLowerCase()}. Headline metric: {s.headline.toLowerCase()}.
          </p>
          <p>
            Built from <code>{s.builtFrom}</code>.
          </p>
          <p>
            On this page: <a href="#leaderboard">leaderboard</a>, <a href="#definitions">metric definitions</a>,{" "}
            <a href="#tiers">difficulty tiers</a>, <a href="#reproduce">reproduce</a>,{" "}
            <a href="#versions">versions and hashes</a>.
          </p>
        </Rail>
      </Section>

      <Section labelledBy="status">
        <Wide>
          <SectionHeading id="status">Status</SectionHeading>
          <StatusBanner suite={{ name: s.name, charterStatus: s.charterStatus }} />
        </Wide>
      </Section>

      <Section labelledBy="leaderboard">
        <Full>
          <SectionHeading id="leaderboard">Leaderboard</SectionHeading>
          <Leaderboard
            caption={leaderboardCaption}
            columns={s.results.columns}
            rows={s.results.rows}
            unitPlural={unitNoun}
            tiers={tierOptions}
            languages={languageOptions}
            cells={cross?.cells ?? {}}
            total={cross?.total ?? null}
            noLanguageDimension={noLanguage}
            noLabelledSet={
              isDay60
                ? "No deployment has been exercised at any tier, so the slice carries no count. A Day-60 score is only comparable with another Day-60 score run at the same tier."
                : undefined
            }
            emptyMessage={
              isDay60
                ? "No deployment has been exercised. A Day-60 score needs a live deployment, a partner and an exercise window agreed in writing under charter 4.5.1."
                : undefined
            }
          />
          {verbatim.length > 0 ? (
            <div style={{ marginTop: 32 }}>
              <p className="ui" style={{ fontWeight: 500, marginBottom: 12 }}>
                The preflight failures, verbatim
              </p>
              <p className="note" style={{ maxWidth: "68ch", marginBottom: 16 }}>
                The status column carries each reason in a few words. The full text below is what the runner wrote into{" "}
                <code>{s.results.dir}/runs/&lt;system&gt;/run-1/run.json</code> when it checked the preflight and called
                nothing.
              </p>
              <TableWrap label="Preflight failures, verbatim">
                <table className="table table-dense">
                  <tbody>
                    {verbatim.map((r) => (
                      <tr key={r.id}>
                        <th scope="row" style={{ fontWeight: 400, width: "22%" }}>
                          {r.system}
                        </th>
                        <td className="not-run">
                          <ul className="prose-list" style={{ maxWidth: "72ch" }}>
                            {(r.reasonFull ?? []).map((f, i) => (
                              <li key={i}>{f}</li>
                            ))}
                          </ul>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </div>
          ) : null}

          <div style={{ marginTop: 40 }}>
            <BarChart
              title={`${s.headline}, by ${isDay60 ? "deployment" : "system"}`}
              bars={s.results.rows.map((r) => ({ label: r.system, automated: null }))}
              emptyMessage={chartEmpty}
            />
          </div>
        </Full>
      </Section>

      {s.results.reference ? (
        <Section labelledBy="reference">
          <Full>
            <SectionHeading id="reference">The dataset&apos;s reference decision policy</SectionHeading>
            <ReferencePolicy reference={s.results.reference} dir={s.results.dir} />
          </Full>
        </Section>
      ) : null}

      {s.results.rubric && s.results.rubric.length > 0 ? (
        <Section labelledBy="rubric">
          <Full>
            <SectionHeading id="rubric">The rubric</SectionHeading>
            <Day60Rubric results={s.results} />
          </Full>
        </Section>
      ) : null}

      <Section labelledBy="definitions">
        <Wide>
          <SectionHeading id="definitions">Metric definitions</SectionHeading>
          <p className="body" style={{ marginBottom: 24 }}>
            Read from charter {charter.version} section 3 when this page was built. Each metric carries its formula, its
            numerator, its denominator and its exclusions, and each has clause language in{" "}
            <code>{benchmarks.clauses.path}</code> so it can be written into a statement of work. The charter&apos;s
            arithmetic examples are left out here: they are invented numbers that demonstrate a formula, and beside a
            table of &quot;not run&quot; they would read as results.
          </p>
          <Definitions metrics={s.metrics} charterVersion={charter.version} />
        </Wide>
      </Section>

      {s.tier ? (
        <Section labelledBy="tiers">
          <Wide>
            <SectionHeading id="tiers">Difficulty tiers</SectionHeading>
            <p className="body" style={{ marginBottom: 24 }}>
              Charter {charter.version} section {s.tierSection}. A tier is a property of the item, assigned when it is
              generated, and it never changes because a system found the item hard.
            </p>
            <div className="doc" style={{ maxWidth: "none" }}>
              <Blocks blocks={s.tier.blocks} tableLabel={`${s.name} tiers`} />
            </div>
          </Wide>
        </Section>
      ) : null}

      <Section labelledBy="dataset">
        <Wide>
          <SectionHeading id="dataset">The data</SectionHeading>
        </Wide>
        <Reading>
          {s.dataset.present ? (
            <div className="stack-3">
              <p className="body">
                {s.dataset.cross?.total?.toLocaleString("en-GB")} {s.dataset.unitPlural}, version{" "}
                {s.dataset.version ?? "not set"}, generated from seed {String(s.dataset.seed ?? "not set")}. Every item
                is synthetic. Charter 6.1: nothing is scraped, and no real document, transcript, recording or partner
                record enters a public set.
              </p>
              <TableWrap label={`${s.name} dataset composition`}>
                <table className="table table-dense">
                  <caption>Composition, read from the dataset&apos;s own ground truth and manifest.</caption>
                  <thead>
                    <tr>
                      <th scope="col">Line</th>
                      <th scope="col" className="numeric">
                        {s.dataset.unitPlural}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(s.dataset.splits ?? []).map((sp) => (
                      <tr key={`split-${sp.key}`}>
                        <th scope="row" style={{ fontWeight: 400 }}>
                          Split: {sp.key.replace(/_/g, " ")}
                        </th>
                        <td className="numeric">{sp.count.toLocaleString("en-GB")}</td>
                      </tr>
                    ))}
                    {(s.dataset.types ?? []).map((t) => (
                      <tr key={`type-${t.key}`}>
                        <th scope="row" style={{ fontWeight: 400 }}>
                          {t.key.replace(/_/g, " ")}
                        </th>
                        <td className="numeric">{t.count?.toLocaleString("en-GB") ?? "not exercised"}</td>
                      </tr>
                    ))}
                    {(s.dataset.cross?.tiers ?? []).map((t) => (
                      <tr key={`tier-${t.key}`}>
                        <th scope="row" style={{ fontWeight: 400 }}>
                          Tier {t.key}
                        </th>
                        <td className="numeric">{t.count?.toLocaleString("en-GB") ?? "not exercised"}</td>
                      </tr>
                    ))}
                    {(s.dataset.cross?.languages ?? [])
                      .filter((l) => l.key !== "not-applicable")
                      .map((l) => (
                        <tr key={`lang-${l.key}`}>
                          <th scope="row" style={{ fontWeight: 400 }}>
                            {l.label}
                          </th>
                          <td className="numeric">{l.count?.toLocaleString("en-GB") ?? "not stated"}</td>
                        </tr>
                      ))}
                    {s.dataset.audio ? (
                      <tr>
                        <th scope="row" style={{ fontWeight: 400 }}>
                          Contacts with rendered audio
                        </th>
                        <td className="numeric">{s.dataset.audio.toLocaleString("en-GB")}</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </TableWrap>
            </div>
          ) : (
            <p className="body">
              This suite has no dataset. It is a rubric and a set of scripted exercises run against a live deployment,
              ours or anyone&apos;s, sixty days after go-live.
            </p>
          )}
        </Reading>
        <Rail label="The public sample">
          {s.dataset.present ? (
            <>
              <p>
                {s.dataset.sampleCount === null || s.dataset.sampleCount === undefined
                  ? "The sample size is not published for this suite."
                  : `${s.dataset.sampleCount.toLocaleString("en-GB")} ${s.dataset.unitPlural}, drawn to the same tier and language mix as the whole set, published under CC BY 4.0.`}
              </p>
              <p>
                <a href={repoPath(s.dataset.samplePath ?? s.dataset.path ?? "")}>
                  {s.dataset.samplePath ?? s.dataset.path}
                </a>
              </p>
              {s.dataset.privateCount ? (
                <p>
                  A further {s.dataset.privateCount.toLocaleString("en-GB")} {s.dataset.unitPlural} are held privately
                  and never published. Charter 5.10: the private split exists to detect tuning against the public one.
                </p>
              ) : null}
              {REPO_PUBLISHED ? null : (
                <p>
                  The public repository <a href={REPO_URL}>{REPO_URL.replace("https://", "")}</a> is not created yet, so
                  that link does not resolve. The path is the path inside it.
                </p>
              )}
            </>
          ) : (
            <p>
              Nothing to download. The rubric, the scripted incidents and the self-assessment are documents, listed
              under the reproduce section below.
            </p>
          )}
        </Rail>
      </Section>

      <Section labelledBy="reproduce">
        <Wide>
          <SectionHeading id="reproduce">Reproduce</SectionHeading>
        </Wide>
        <Reading>
          <Reproduce suite={s} />
        </Reading>
        <Rail label="Charter 5.5">
          <p>
            Every result is reproducible from a commit. A figure that cannot be reproduced from the dataset version and
            hash, the harness version and commit, the prompt set hash, the model version string, the run date, the price
            list date and the exact command line is withdrawn, not defended.
          </p>
          <p>
            <Link href="/run-it-yourself">Run it on your own data</Link>.
          </p>
        </Rail>
      </Section>

      <Section labelledBy="versions">
        <Wide>
          <SectionHeading id="versions">Versions and hashes</SectionHeading>
        </Wide>
        <Reading>
          <div className="stack-3">
            <Provenance suite={s} />
            <PromptHashes hashes={s.results.promptHashes} />
          </div>
        </Reading>
        <Rail label="Charter 7.3">
          <p>
            No table mixes versions. A row produced under a different dataset, harness or charter version sits in a
            different table, and a superseded table stays published, marked superseded, with a link to the one that
            replaced it.
          </p>
          <p>
            <Link href="/changelog">Changelog</Link> · <Link href="/disputes">Dispute a figure on this page</Link>
          </p>
        </Rail>
      </Section>
    </>
  );
}
