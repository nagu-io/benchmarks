# Honest Containment findings

Suite `honest-containment` · dataset version 1.0.0 · harness version 1.0.0 · written
2026-09-02

**There are no findings yet.** This file is the structure the findings will be written
into. It is published empty on purpose, so that the shape of the analysis is fixed before
any result exists and cannot be arranged around a number afterwards.

No system has been run. This build had no model interface keys and the environment could
not reach a model interface. `leaderboard.md` carries the `not run` rows and the reason for
each. Charter section 3.1.8 governs this file as it governs the tables: nothing here is
estimated, extrapolated, illustrated or filled with a plausible-looking figure, and no
sentence below asserts a result.

Each section states what will be written into it, and what evidence will support it. A
section that the first run cannot support will say so rather than being quietly dropped.

---

## 1. What was run

To be written after the first run. Systems scored, model version strings as the provider
reported them, number of runs per system, dataset version and hash, harness commit, prompt
set hashes, run dates, and every system that could not complete with the reason. Charter
5.5 and 5.8.

## 2. The spread between definitions

To be written after the first run. The per-system table is in `definitions-spread.md`. This
section will report: the size of the spread per system, whether the ranking of systems
changes when the definition changes, and which of the three conditions in charter 3.9.1
accounts for most of the gap on this data.

The question this section answers: does the choice of definition change who wins, or only
by how much.

## 3. False containment

To be written after the first run. Against each of the four common definitions, with the
breakdown by failing condition, which is where the cost to a BPO differs: a refused request
for a person is a complaint, a repeat contact is a second contact to pay for, and an
unsupported resolution is a rework item that arrives later.

## 4. Escalation

To be written after the first run. Recall, precision and quality together, never one alone.
Two specific questions this dataset was built to answer:

- whether systems escalate on anger, which the ground truth does not require, and what that
  costs them in precision;
- whether systems escalate on the distress cues in the welfare policies, which the ground
  truth does require within one turn.

The escalation base rate in this set is 172 of 300, a design consequence of the tier table
in charter 4.3 and not a traffic mix. The datasheet says so and this section will repeat it
beside any figure.

## 5. Hallucinated policy

To be written after the first run. The rate over contacts that made an assertion and the
rate over all contacts, side by side, so that a system which avoids the subject is visible
rather than flattered. The financial and regulated classes reported separately and never
averaged in. The tier-5 question specifically: whether systems quote the superseded document
that sits in the pack beside the current one.

## 6. Latency and turns

To be written after the first run. Time to first token at the 50th and 95th percentiles by
nearest rank, with the population size, the opening turn reported separately, and time to
first substantive token reported separately for any system that emits a holding phrase.
Turns to resolution as a distribution against the expected range each scenario carries.

## 7. Per tier and per language

To be written after the first run. Every headline figure broken out by tier, with the tier
mix printed beside it, charter 3.1.7 and 4.1.4. The language breakout carries the caveat
from the datasheet: the accents in the audio are approximated, so a language difference
observed here is a difference on approximated speech.

## 8. Judge agreement

To be written after the 60 adjudication cases are labelled. Cohen's kappa per dimension,
judge against each human labeller, and labeller against labeller. Charter 5.9 sets 0.8 as
the level below which every table that depends on the judge carries the caveat. As at this
writing the figure is unmeasured, not low: the cases are selected and unlabelled, and
`labelling/kappa.py` refuses to compute a partial figure.

## 9. What this run did not measure

To be written after the first run, and it will not be short. The permanent items are in the
datasheet: the escalation base rate is a design choice, the accents are approximated, the
policy packs are shorter and more consistent than real ones, the caller is a model, the
repeat-contact rule is scripted, and no scenario tests a caller expressing an intention to
self-harm.

## 10. What we got wrong

To be written after the first run. Defects found in the dataset, the harness or this
analysis, what changed as a result, and the version the correction landed in. Charter 8.4
requires the disputes log; this section is where we record the ones we find ourselves.
