import { benchmarks } from "@/lib/data";
import { Rail, Reading, Section, Wide } from "@/components/Section";
import { Blocks } from "@/components/Markdown";
import { pageMeta, repoPath } from "@/lib/site";

export const metadata = pageMeta({
  title: "Methodology",
  description:
    "The benchmark charter in full: metric definitions with formula, numerator, denominator and exclusions, the tier schemes, the neutrality rules, the data ethics, the versioning and the limitations.",
  path: "/methodology",
});

export default function Page() {
  const { charter } = benchmarks;
  return (
    <>
      <Section hero>
        <Reading>
          <p className="note" style={{ marginBottom: 12 }}>
            Charter {charter.version} · written {charter.written} · <code>{charter.path}</code>
          </p>
          <h1 className="page-title">Benchmark charter and methodology</h1>
          <p className="lead" style={{ marginTop: 24 }}>
            The document every suite follows. Where a dataset, a harness, a results table or a report disagrees with it,
            this document wins until it is changed here and the version is raised.
          </p>
          <p className="body" style={{ marginTop: 24 }}>
            This page is rendered from the charter file itself when the site is built. It is not a summary of it, and it
            cannot drift from it. The figures marked &quot;arithmetic example&quot; in section 3 are invented numbers
            that demonstrate a formula. They are not results, ours or anyone&apos;s, and quoting one as a result is a
            misuse of this document.
          </p>
        </Reading>
        <Rail label="Contents">
          <ul className="toc">
            {charter.sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{s.title}</a>
              </li>
            ))}
          </ul>
          <p style={{ marginTop: 24 }}>
            The clause language for every metric is in <a href={repoPath(benchmarks.clauses.path)}>contract-clauses.md</a>,
            version {benchmarks.clauses.version ?? "not set"}.
          </p>
          <ul className="toc" style={{ marginTop: 24 }}>
            {charter.frontMatter.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Rail>
      </Section>

      <Section labelledBy="charter">
        <Wide>
          <h2 className="sr-only" id="charter">
            The charter
          </h2>
          <div className="doc" style={{ marginBottom: 40 }}>
            <Blocks blocks={charter.preamble} tableLabel="Charter preamble" />
          </div>
          <div className="doc">
            {charter.sections.map((s) => (
              <section key={s.id} aria-labelledby={s.id}>
                <h2 id={s.id}>{s.title}</h2>
                <Blocks blocks={s.blocks} tableLabel={s.title} />
              </section>
            ))}
          </div>
        </Wide>
      </Section>
    </>
  );
}
