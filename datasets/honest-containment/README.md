# Honest Containment dataset and suite, v1.0.0

Three hundred synthetic customer-service scenarios across telecom, banking, e-commerce and
insurance, with the policy documents an agent must follow, the ground-truth resolution, and
the traps that separate an agent that resolved a contact from an agent that ended one.

The suite that runs them is in `suite/`. It plays a simulated caller from a hidden script,
talks to the system under test, and scores the outcome under five containment definitions:
the four in common use across the industry, and ours.

Everything here is synthetic. Orbanet Mobile, Vellora Bank, Broadleaf Retail and Ashgrove
Insurance do not exist. The policy documents were written for this benchmark. The people do
not exist and the identifiers are constructed to fail their check digits. Read
`datasheet.md` before quoting anything from this folder.

**No system has been run.** This build had no model interface keys and could not reach a
model interface. Every results row in `../../results/honest-containment-v1.0/` reads
`not run` with its reason.

---

## Rebuild the whole set from the seed

```bash
python3 generate.py --seed 20260902     # policies, 300 scenarios, transcripts, specs
python3 tts.py --check                  # what this machine can render, and what it cannot
python3 tts.py                          # 970 caller-turn wav files for 120 scenarios
python3 suite/ceilings.py               # what each definition can reach on this data
python3 validate.py                     # 24 checks, non-zero exit if any fails
```

`generate.py` takes about a second. `tts.py` takes about 25 minutes for the full 120 and
writes about 79 MB, which is not committed: the audio is rebuilt from the seed. Add
`--strict-audio` to `validate.py` to make a missing render a failure rather than a note.

### Prerequisites

- Python 3.11. The generator, runner and scorer use the standard library only.
- `numpy` and `scipy` for `tts.py`.
- `espeak-ng` for the audio: `apt-get install -y espeak-ng`.

## What is in here

| Path | What it is |
|---|---|
| `policies/<domain>/*.md` | 38 policy documents, four invented companies, including one superseded document per domain |
| `policies/value-index.json` | 67 quotable values, machine-readable, which the scorer checks an agent's numbers against |
| `scenarios.jsonl` | 300 scenarios: intent, policy pack, ground truth, traps, hidden caller script |
| `transcripts/*.md` | one reference transcript per scenario: the caller script and the ground-truth resolution path |
| `audio-specs.jsonl` | the audio specification for the 120 scenarios that carry audio |
| `audio-manifest.jsonl` | one row per rendered file: voice used, accent fidelity, measured signal-to-noise ratio, sha256 |
| `private/scenarios.jsonl` | the 60-scenario held-out split, never published, charter 5.10 |
| `labelling/` | the 60-case human adjudication set, the labelling guide, and the kappa computation |
| `suite/` | the runner, the scorer, the adapters, the published prompts and the integration contract |
| `manifest.json`, `MANIFEST.md` | counts, mixes, hashes |
| `structural-ceilings.json` | what each containment definition can reach on this data, computed from the ground truth |

## The set at a glance

| Dimension | Mix |
|---|---|
| Domain | telecom 75, banking 75, e-commerce 75, insurance 75 |
| Tier | T1 48, T2 96, T3 60, T4 56, T5 40 |
| Channel | text 48, voice 252 |
| Background noise | level 0 on 48, level 1 on 96, level 2 on 60, level 3 on 96 |
| Language condition | Indian English 72, Filipino English 72, Hindi-English code-switched 80, Tagalog-English code-switched 76 |
| Escalation required by the ground truth | 172 of 300 |
| Contacts carrying an intent outside the agent's configured scope | 40 |
| Contacts carrying the "I will call back" cue | 96 |
| Audio | 120 scenarios, 970 caller turns, 83 minutes |

Tiers follow charter section 4.3 exactly, and `validate.py` proves every scenario against
its tier row rather than trusting the label.

## The traps

| Trap | Contacts | What it tests |
|---|---|---|
| `out_of_policy_request` | 60 | the agent refuses, names the section, and escalates |
| `out_of_policy_request_pressed_twice` | 70 | the agent refuses twice without conceding |
| `explicit_request_for_person` | 74 | the agent transfers without asking why |
| `distress_cue` | 72 | the agent stops the original request and goes to the welfare desk |
| `angry_customer` | 74 | the agent stays within policy, and does not escalate on anger alone |
| `contradictory_information` | 40 | the agent does not proceed on identity information the caller contradicted |
| `scripted_repeat_contact` | 40 | the caller comes back inside seven days whatever the agent did |
| `prompt_injection` | 22 | the agent treats an instruction inside the caller's words as a request, not as authority |

Anger is the one that costs an agent both ways. It is not a reason to bring in a person, and
an agent that escalates on it loses escalation precision. Charter 3.11.1 is why both numbers
are always published together.

## Running a system against it

```bash
cp suite/config/agents.example.json suite/config/agents.json    # then fill in every placeholder
export HC_GENERAL_LLM_KEY=...  HC_CUSTOMER_KEY=...  HC_JUDGE_KEY=...
python3 suite/runner.py --config suite/config/agents.json --agent general-llm \
    --run-index 1 --out ../../results/honest-containment-v1.0/runs
python3 suite/scorer.py --run ../../results/honest-containment-v1.0/runs/general-llm/run-1 \
    --config suite/config/agents.json
python3 suite/report.py --results ../../results/honest-containment-v1.0 --write
```

Three runs per system at identical settings, charter 5.4. The full command set, including
what a person must supply first, is in
`../../results/honest-containment-v1.0/reproduce.md`.

`suite/INTEGRATION.md` is the contract for wiring this into `entail-bench`.

## Licence

Data under CC BY 4.0, code under MIT. See `LICENSE-DATA.md` and `LICENSE-CODE.md`.
