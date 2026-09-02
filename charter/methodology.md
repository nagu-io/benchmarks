# Benchmark charter and methodology

Owner: Benchmark owner, Entailment Labs (placeholder name)
Charter version 1.0.0
Written 2026-09-02
Applies to: Messy Scan, Honest Containment, Exception Economics, Day-60

> Read this first. Every task in `10-benchmarks/` follows this document. Where a dataset, a harness, a results table or a report disagrees with it, this document wins until it is changed here and the version is raised.
>
> Two warnings that hold throughout. First, the figures marked "arithmetic example" in section 3 are arithmetic. They are invented to show how a formula is applied. They are not results, not ours and not anyone's, and they are never quoted outside the paragraph they sit in. Second, no suite has been run. Section 10 states the status and the reason.

## The charter, in parts

This charter is published in parts so that a section can be linked, reviewed and cited on its own. The parts are the charter: nothing here is a summary and nothing is left out.

| Part | Sections | Read |
|---|---|---|
| 01 | 1. Purpose, 2. The four suites, 3. Metric definitions, 3.1 Rules that apply to every metric in this section, 3.2 Index of metrics, 3.3 Field-level accuracy, 3.4 Document-level straight-through-processing rate, 3.5 Exception rate, 3.6 Confidence calibration, expected calibration error | [`01-1-to-3-6.md`](methodology/01-1-to-3-6.md) |
| 02 | 3.7 Cost per document, 3.8 Latency, 3.9 Containment, 3.10 False containment, 3.11 Escalation accuracy, 3.12 Hallucinated-policy rate, 3.13 Time to first token | [`02-3-7-to-3-13.md`](methodology/02-3-7-to-3-13.md) |
| 03 | 3.14 Automation rate, 3.15 Wrong-automation cost in rework minutes, 3.16 Reviewer minutes per exception, 3.17 90-day drift, 3.18 Drift detection lead time, 3.19 Incident mean time to restore, 3.20 Rollback time | [`03-3-14-to-3-20.md`](methodology/03-3-14-to-3-20.md) |
| 04 | 3.21 Report completeness, 4. Difficulty tiers, 5. Neutrality rules, 6. Data ethics, 7. Versioning | [`04-3-21-to-7.md`](methodology/04-3-21-to-7.md) |
| 05 | 8. Publishing cadence, changelog and disputes, 9. Limitations, 10. Current status | [`05-8-to-10.md`](methodology/05-8-to-10.md) |

## The two rules that govern every part

**A figure with no run is written `not run` with the reason.** It is never estimated, extrapolated, interpolated from a neighbouring tier, or replaced with a plausible-looking figure, in a table, a chart, a chart's sample data, prose or a code fixture. Sections 3.1.8 and 10.4.

**The figures marked "arithmetic example" are arithmetic.** They are invented numbers chosen to demonstrate a formula. They are not results, ours or anyone's, and quoting one as a result is a misuse of this document. Section 10.5.

## Status

No suite has been run. The datasets, the harness and the Day-60 rubric are built and validated. No model interface key was available and the build environment could not reach a model interface. The part carrying section 10 has the status table and what a first run needs from a person.
