# Entailment Labs benchmarks

Four benchmark suites for the systems BPOs actually buy: document extraction, voice and chat
agents, back-office automation, and the operations around a deployment sixty days after it
goes live.

They exist to measure the distance between the number in a vendor deck and the number a
process produces in production, and to state both in definitions a BPO can write into a
statement of work. Every metric here carries a formula, a numerator, a denominator, its
exclusions and a contract sentence. `charter/contract-clauses.md` turns each one into clause
language.

Data is CC BY 4.0. Code is MIT. Leaderboards, definitions and the disputes log are at
[bench.entailmentlabs.com](https://bench.entailmentlabs.com).

---

## Status: no suite has been run

Every results table in this repository reads `not run`, with the reason, on every row. That
is not a placeholder for a number we have and have not published. There is no number.

| Suite | Dataset | Harness | Runs | Status |
|---|---|---|---|---|
| Messy Scan | v1.0.0, 1,000 documents | entail-bench 1.0.0 | 0 | not run — no model interface key, no reachable model interface |
| Honest Containment | v1.0.0, 300 contacts | suite runner 1.0.0 | 0 | not run — no model interface key, no reachable model interface |
| Exception Economics | v1.0.0, 2,000 work items | scorer 1.0.0 | 0 | not run — no model interface key, no reachable model interface |
| Day-60 | Rubric, not a dataset | rubric scoring | 0 | not run — requires a live deployment and an agreed exercise window |

The datasets are built and validated. The harness is built and its tests pass. What is
missing is a person's decisions: an interface key per provider, a spend cap set before the
run, a decision on which model versions are in scope, an account whose rate limits allow
three runs over the full set, the price list date, and for Day-60 a partner and a deployment
willing to be exercised under the safety rules in the charter section 4.5.1.

Exception Economics is the one suite that produces figures without any of that, because it
scores a decision policy over labelled items and the arithmetic needs no model call. The
figures it publishes describe the dataset's own synthetic reference policy. They are a
property of the data. They are not a measurement of any model, service or vendor, and they
are labelled that way everywhere they appear.

---

## The four suites

| Suite | Unit scored | Headline metric | What it measures | What it does not |
|---|---|---|---|---|
| **Messy Scan** | One document | Document-level straight-through-processing rate | What degradation does to extraction across five tiers, four document families and four language mixes | Integration effort, review-queue design, anything a person does after the output |
| **Honest Containment** | One contact | Containment under charter 3.9 | Whether a contact was resolved or only ended, scored under four common industry definitions and under ours, with the spread published as a column | Voice quality, speech recognition in isolation, telephony reliability |
| **Exception Economics** | One work item | Net cost per item at a stated confidence threshold | What automation costs when it is wrong, in reviewer minutes and money, at three confidence thresholds | The partner's own reviewer productivity, which varies more than any model in the table |
| **Day-60** | One deployment | Day-60 score, 0 to 100 | Whether a deployment is still trustworthy two months in: drift detection, incident restoration, rollback, monthly report | Model quality, which is the point of running it alongside the other three |

### Messy Scan

1,000 synthetic documents: invoices in Indian GST, US, EU VAT and Philippine BIR formats,
KYC packs, insurance claim forms and purchase orders. Each is rendered and then degraded
across five tiers, from a born-digital PDF to a low-quality messaging-app recompression of a
multi-document bundle with rotated pages and two languages on one page. Ground truth is
embedded at generation, so every field has a known answer.

A 50-document public sample ships in `datasets/messy-scan/sample/`. A 200-document private
split does not ship, and exists to detect tuning against the public one.

### Honest Containment

300 synthetic customer-service scenarios across telecom, banking, e-commerce and insurance,
each with a policy pack the agent must follow, a ground-truth resolution, and scripted traps:
an out-of-policy request pressed twice, an explicit request for a person, a distress cue, an
identity that cannot be verified, a superseded policy document sitting beside the current one.
120 of them carry rendered audio in Indian English, Filipino English and code-switched
Hindi-English and Tagalog-English at three noise levels.

Containment is the metric most often quoted and least often defined, so every agent is scored
under all five definitions and the spread is a column, not a footnote.

### Exception Economics

2,000 synthetic back-office items — ticket triage, KYC cases, invoice-to-purchase-order
reconciliations — with ground truth and a published labour model. Scored at three confidence
thresholds, plus a sweep, plus a ninety-day drift simulation that shifts the input
distribution and re-scores.

Automation rate is never published alone here. The wrong-automation figure sits on the same
row, because a system that automates everything and is wrong on a tenth of it can cost more
than one that automates half and is right.

### Day-60

Not a dataset. A rubric and a set of scripted exercises run against a live deployment, ours
or anyone's, sixty days after go-live: inject a drift and time the detection and the notice;
raise an incident and time the restoration and the communication; force a rollback and time
it; audit the monthly report against a completeness checklist. 100 points, published bands,
and a self-assessment version a BPO can run against its current supplier in an afternoon.

---

## How to run them

Full commands per suite are in each suite's `results/<suite>/reproduce.md`, or on the suite's
page at bench.entailmentlabs.com. The short version:

### The harness, on your own documents

```bash
cd harness
pip install -e .
entail-bench --version
entail-bench list-models
```

Put your documents in a folder with a `ground-truth.jsonl` beside them, one JSON object per
document, then:

```bash
entail-bench validate-config
entail-bench run --dry-run --dataset ./their-folder --runs 3
export OPENAI_API_KEY=...
entail-bench run --suite messy-scan --model openai --model-id <the model you are scoring> \
  --dataset ./their-folder --runs 3 --max-spend 25.00
```

`harness/README.md` has the five-minute quickstart, the ground-truth record shape, the
adapter list and the environment variable each adapter reads. No key is stored in this
repository, or anywhere in the harness.

### Rebuild a dataset from its seed

Every dataset is deterministic. The repository holds the generators and the ground truth;
the rendered documents and the audio are rebuilt, not committed.

```bash
cd datasets/messy-scan
python3 generate.py --seed 20260902
python3 render.py
python3 degrade.py
python3 validate.py
```

```bash
cd datasets/honest-containment
python3 generate.py --seed 20260902
python3 tts.py
python3 validate.py --strict-audio
```

```bash
cd datasets/exception-economics
python3 generate.py --seed 20260902
python3 validate.py
python3 score.py --out ../../results/exception-economics-v1.0/scores-baseline.json
python3 drift.py  --out ../../results/exception-economics-v1.0/drift.json
python3 report.py --results ../../results/exception-economics-v1.0
```

`validate.py` exits non-zero if a ground-truth field is missing, if totals do not reconcile,
if a regenerated file differs from the committed one, or if any identifier in the set passes
its real check digits. That last check is the one that matters: every Aadhaar-style,
PAN-style, card and IBAN identifier in these datasets is format-valid and checksum-invalid by
construction, so nothing here can resolve to a real person or account.

### Score a system the harness has no adapter for

Every suite takes predictions through a documented file interface. For Exception Economics,
one JSON object per line:

```json
{"item_id": "EE-0001", "proposed_outcome": "recon:matched:PO-446576", "confidence": 0.91}
```

```bash
python3 score.py --predictions runs/vendor-a.jsonl --label "Vendor A" \
    --out ../../results/exception-economics-v1.0/scores-vendor-a.json
```

An item with no line in the predictions file is scored as a processing failure and counted as
one. It is never dropped from the denominator.

---

## The rules this runs under

Full text in `charter/methodology.md`, section 5. In short:

- **Prompts are fixed and published in full.** They live in `harness/prompts/`, and every
  report prints or hashes the set it used. There is no private prompt.
- **The same prompt goes to every model.** The only permitted differences are the mechanical
  requirements of an interface, and every one is listed per model in the report.
- **No vendor-specific tuning.** No per-model prompt rewriting, no per-model few-shot
  selection, no temperature search, no retry with a different prompt after a poor answer, and
  no post-processing that only one system receives.
- **Three runs per model per suite** at identical settings, reported as the mean with the
  standard deviation and the minimum and maximum. A single-run figure is never published.
- **Every result is reproducible from a commit.** A figure that cannot be reproduced from the
  dataset version and hash, the harness commit, the prompt set hash, the model version string,
  the run date, the price list date and the exact command line is withdrawn, not defended.
- **Our own system is scored by the same harness**, from the same commit, with the same
  prompts, on the same data, and appears in the same table with no highlight, no bold, no
  footnote and no position advantage.
- **A figure that was not produced by a run is written `not run` with the reason.** Never
  estimated, never extrapolated, never interpolated from a neighbouring tier, never replaced
  with a plausible-looking figure — not in a table, a chart, a chart's sample data, prose or a
  test fixture.

And the disclosure that belongs beside all of it: we are not neutral parties. Entailment Labs
sells systems in all four of these categories. The rules above are the discipline we accept in
return for publishing at all, the disputes process below is the route to hold us to them, and
neither removes the interest we have in the outcome.

---

## Disputing a figure

Anyone may dispute any figure. Open a
[dispute a result](../../issues/new?template=dispute-a-result.yml) issue, or write to
hello@entailmentlabs.com. Name the table, the row, the dataset and harness versions, and what
is wrong.

The process, its time limits and its outcomes are public. A dispute we lose stays in the log,
with the correction linked to it. A dispute about our own system's row runs through the same
steps and is marked a self-dispute, so a reader can count how many there have been and how
they went. See `charter/methodology.md` section 8.4.

To have a system added, open an
[add a model](../../issues/new?template=add-a-model.yml) issue.

---

## Layout

```
charter/              methodology.md and contract-clauses.md — read these first
datasets/             generators, ground truth, datasheets, manifests, public samples
harness/              entail-bench: adapters, scorer, prompts, tests
day-60/               the rubric, the scripted incidents, the scoresheet, the self-assessment
results/              one folder per suite version; leaderboards, findings, reproduce commands
```

`LAYOUT.md` says which folders of the internal working tree map to which paths here, and
which generated artefacts are deliberately kept out. `REGENERATED.md` lists every artefact
rebuilt from a seed rather than committed, with the SHA-256 to check a rebuild against.

---

## Licences

| What | Licence | Where |
|---|---|---|
| Code: the harness, the generators, the scorers, the validators | MIT | `LICENSE` |
| Data: ground truth, manifests, policy packs, transcripts, audio specifications, results | CC BY 4.0 | `LICENSE-DATA`, and `datasets/LICENSE` |

Attribution for the data: *Entailment Labs benchmarks, <suite> dataset v<version>*. Cite the
repository with `CITATION.cff`.

The private splits are not published and are not covered by either licence.

---

## Contributing, conduct and security

- `CONTRIBUTING.md` — what a useful contribution looks like, and what changes a version.
- `CODE_OF_CONDUCT.md` — how people are expected to behave here.
- `SECURITY.md` — how to report a vulnerability. security@entailmentlabs.com.
