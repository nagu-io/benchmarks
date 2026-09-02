# Reproducing the Honest Containment results

Suite `honest-containment` · dataset version 1.0.0 · harness version 1.0.0 · written
2026-09-02

Everything below is the exact command. Nothing here has been run against a model: this
build had no interface keys and could not reach a model interface, so every row in
`leaderboard.md` reads `not run`. These are the commands that fill it in.

## 0. What a person must supply first

No script does any of this, and no agent may do any of it.

| Item | Detail |
|---|---|
| An interface key per system under test | `HC_VOICE_A_KEY`, `HC_VOICE_B_KEY`, `HC_GENERAL_LLM_KEY`, `HC_ENTAILMENT_KEY` |
| An interface key for the simulated customer | `HC_CUSTOMER_KEY` |
| An interface key for the judge | `HC_JUDGE_KEY`, and the judge model must not be one of the models under test, charter 5.9 |
| A spend cap with each provider, set before the run | three runs over 300 contacts per system |
| The API base, endpoint paths and response paths for each voice platform | from that platform's current documentation, with the documentation date recorded in the config |
| A decision on which model version strings are in scope | recorded in the config |
| The price list date | recorded in the config, charter 5.5 |

## 1. Rebuild the dataset from the seed

```bash
cd 10-benchmarks/datasets/honest-containment
python3 generate.py --seed 20260902
python3 tts.py --check
python3 tts.py
python3 suite/ceilings.py
python3 validate.py --strict-audio
```

`generate.py` takes about a second and writes the policies, the 300 scenarios, the 300
transcripts, `audio-specs.jsonl`, `manifest.json` and `MANIFEST.md`. `tts.py` takes about
25 minutes and writes 970 wav files and `audio-manifest.jsonl`. `validate.py` runs 24
checks and exits non-zero on any failure.

## 2. Configure

```bash
cp suite/config/agents.example.json suite/config/agents.json
$EDITOR suite/config/agents.json      # replace every value that reads placeholder
export HC_VOICE_A_KEY=...  HC_VOICE_B_KEY=...  HC_GENERAL_LLM_KEY=... \
       HC_ENTAILMENT_KEY=...  HC_CUSTOMER_KEY=...  HC_JUDGE_KEY=...
```

Check the configuration without calling anything:

```bash
python3 suite/runner.py --config suite/config/agents.json --agent general-llm \
    --run-index 1 --out ../../results/honest-containment-v1.0/runs --dry-run
```

A dry run prints every preflight failure and writes the `not run` records. That is the
command that produced the current contents of `runs/`.

## 3. Run each system three times

Charter 5.4: three runs per system at identical settings. A single-run figure is never
published.

```bash
cd 10-benchmarks/datasets/honest-containment
for AGENT in voice-platform-a voice-platform-b general-llm entailment-agent; do
  for RUN in 1 2 3; do
    python3 suite/runner.py \
      --config suite/config/agents.json \
      --agent "$AGENT" \
      --run-index "$RUN" \
      --out ../../results/honest-containment-v1.0/runs
  done
done
```

Each run writes `runs/<agent>/run-<n>/run.json` and `runs/<agent>/run-<n>/contacts.jsonl`.

To run a subset while checking a configuration, add `--limit 10`, or `--only hc-tel-0001
hc-bnk-0004`.

## 4. Score every run

```bash
for AGENT in voice-platform-a voice-platform-b general-llm entailment-agent; do
  for RUN in 1 2 3; do
    python3 suite/scorer.py \
      --run ../../results/honest-containment-v1.0/runs/$AGENT/run-$RUN \
      --config suite/config/agents.json
  done
done
```

Each writes `scored-contacts.jsonl` and `metrics.json` beside the run.

## 5. Build the tables

```bash
python3 suite/report.py --results ../../results/honest-containment-v1.0 --write
```

Rewrites `leaderboard.md`, `definitions-spread.md` and `results.csv` from whatever runs
exist. A system with no publishable run keeps its `not run` row and its reason.

## 6. Measure judge agreement

Charter 5.9. Until this is done, every containment, false containment and
hallucinated-policy figure carries the caveat that judge agreement is unmeasured.

```bash
cd 10-benchmarks/datasets/honest-containment/labelling
python3 select.py --seed 20260902          # already run; rewrites adjudication-set.csv
python3 label.py --run ../../../results/honest-containment-v1.0/runs/general-llm/run-1 \
    --labeller A --prepare
python3 label.py --run ../../../results/honest-containment-v1.0/runs/general-llm/run-1 \
    --labeller B --prepare
# two people label all 60 cases from packets/, following labelling-guide.md
python3 label.py --run ... --labeller A --import filled-A.csv
python3 label.py --run ... --labeller B --import filled-B.csv
python3 kappa.py --a labels-A.csv --b labels-B.csv                  # labeller agreement
python3 kappa.py --a labels-A.csv \
    --judge ../../../results/honest-containment-v1.0/runs/general-llm/run-1   # judge agreement
```

`kappa.py` exits 2 and prints how many rows are blank if any case is unlabelled. It does not
compute a partial figure.

## 7. Self-test, no model interface required

```bash
cd 10-benchmarks/datasets/honest-containment
python3 -m pytest suite/tests -q
python3 suite/runner.py --config suite/config/selftest.json --agent replay-fixture \
    --self-test --only hc-tel-0001 --out /tmp/hc-selftest
python3 suite/scorer.py --run /tmp/hc-selftest/replay-fixture/run-1 --no-judge
```

The tests include a check that the scorer reproduces the worked arithmetic in charter
sections 3.9.8, 3.10.6, 3.8.5 and 3.13.5. A self-test run is written `publishable: false`
and `report.py` refuses to put it in a table.

## What is recorded with every published figure

Charter 5.5. Each `run.json` carries the dataset version, the harness version, the harness
commit hash, the prompt file hashes, the model version string the provider reported, the
run date, the customer mode, the turn cap, and the price list date from the config. A figure
that cannot be reproduced from those is withdrawn rather than defended.

## Environment used for this build

Python 3.11.15, Linux, no network access to any model interface. espeak-ng 1.51 for the
audio. numpy 2.4.4 and scipy 1.17.1 for the noise beds. The `piper` package is installed and
its voice models are not, because the model host is blocked by this environment's egress
proxy; `tts.py --check` prints the command that fetches them elsewhere.
