# Exception Economics v1.0 — reproduce

Dataset `exception-economics` version 1.0.0 · seed 20260902 · ground truth sha256 `49af7a5ee30fb3fc` · scorer version 1.0.0 · charter version 1.0.0 · run date 2026-09-02 · ground truth synthetic.

## Versions and hashes

| Item | Value |
|---|---|
| Dataset | `exception-economics` v1.0.0 |
| Dataset seed | 20260902 |
| Schema version | 1.0 |
| Generator version | 1.0.0 |
| Scorer version | 1.0.0 |
| Drift simulation version | 1.0.0 |
| Charter version | 1.0.0 |
| Ground truth sha256 | `49af7a5ee30fb3fcdd458458c4194ec2ff9409d96e0ff432556cedf8580e5733` |
| Items | 2,000 |
| Baseline population | 1,700 |
| Shifted population | 300 |
| Run date | 2026-09-02 |
| Model interface calls made | 0 |
| Price list date | not applicable — no provider charge was incurred |

## Prerequisites

Python 3.11 and PyYAML. Nothing else. No model interface key, no network access and no browser are needed, because this suite scores a decision policy over labelled items rather than calling a model.

```bash
pip install pyyaml --break-system-packages
```

## The four commands

From `10-benchmarks/datasets/exception-economics/`:

```bash
python3 generate.py --seed 20260902
python3 validate.py
python3 score.py --out ../../results/exception-economics-v1.0/scores-baseline.json
python3 drift.py  --out ../../results/exception-economics-v1.0/drift.json
python3 report.py --results ../../results/exception-economics-v1.0
```

`generate.py` takes under a second and writes `ground-truth.jsonl`, `manifest.json` and `sample/ground-truth.jsonl`. `validate.py` exits non-zero if any check fails, including the check that regenerating from the seed reproduces the file byte for byte. `score.py` and `drift.py` each take under a second. `report.py` rewrites every markdown file in the results folder from the two JSON files, so no figure in a report is typed by hand.

## Scoring a real system

Write one JSON object per line, one line per item:

```json
{"item_id": "EE-0001", "proposed_outcome": "recon:matched:PO-446576", "confidence": 0.91}
```

`proposed_outcome` uses the encoding in `outcomes.py`: `route:<category>/<priority>[/escalate]` for ticket triage, `kyc:<decision>[/<reason>]` for a know-your-customer case and `recon:<decision>:<po>|<po>` for a reconciliation. The optional booleans `processing_failure`, `validation_failure` and `policy_flag` default to false. Then:

```bash
python3 score.py --predictions runs/vendor-a.jsonl --label "Vendor A" \
    --out ../../results/exception-economics-v1.0/scores-vendor-a.json
```

An item with no line in the predictions file is scored as a processing failure and counted as one. It is never dropped from the denominator, per charter 3.1.2.

## Reproducing a single figure

Every figure in `leaderboard.md` and `drift.md` is a field in `scores-baseline.json` or `drift.json`. To check one:

```bash
python3 -c "import json;d=json.load(open('scores-baseline.json'));print(d['thresholds'][0]['rates']['automation_rate'])"
```

## Neutrality

Charter 5.5 requires every result to be reproducible from a commit. The dataset seed, the ground-truth hash, the generator, scorer and drift versions and the exact commands are all above. There is no private prompt and no per-system tuning in this suite, because there is no prompt: the scorer is arithmetic.

Charter 3.1.4 requires three runs per system per suite. That rule applies to a run of a model. This scorer is deterministic and its output does not vary between runs on the same input, so the three-run rule takes effect when a real system's predictions are scored, and the three prediction files are then the three runs.

## What a person still has to supply

| Needed | Why |
|---|---|
| A model interface key per provider, with a spend cap set first | no system row can be produced without one |
| A decision on which model versions are in scope | charter 5.5 records the model version string with every figure |
| A partner's fully loaded reviewer cost, in INR or USD or both | every money figure in this report is a placeholder until then |
| A partner's own measured reviewer minutes, if any exist | every minute in the labour model is a modelling assumption |
| A measured cost per item from a run | machine cost is zero here, so net cost is labour only |

