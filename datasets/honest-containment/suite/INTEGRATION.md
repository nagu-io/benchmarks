# Wiring this suite into entail-bench

Version 1.0 · Suite version 1.0.0 · Dataset version 1.0.0 · Written 2026-09-02

This folder is self-contained. It runs on its own with the commands in
`../README.md`, and it is written so the shared harness can take it over without any file
in this folder changing. This document is the contract. If the harness needs something
this document does not name, the harness and this document are changed together, and the
suite version is raised under charter section 7.

The harness package in `../../harness/` is being built by another author at the same time.
Nothing here imports from it, and nothing here should be edited to match it before the
interface below has been agreed.

---

## 1. What the harness needs to know about this suite

| Item | Value |
|---|---|
| Suite key | `honest-containment` |
| Unit scored | one contact |
| Dataset | `datasets/honest-containment/scenarios.jsonl`, 300 contacts |
| Private split | `datasets/honest-containment/private/scenarios.jsonl`, 60 contacts, never published |
| Dataset version | `1.0.0`, hash in `manifest.json` |
| Suite version | `1.0.0` |
| Headline metric | containment under charter 3.9.1 |
| Also reported | containment under four common definitions, false containment against each, escalation recall, precision and quality, hallucinated-policy rate, time to first token, turns to resolution |
| Runs required | three per system at identical settings, charter 5.4 |
| Results folder | `results/honest-containment-v<dataset version>/` |

## 2. The four entry points

The harness may call these as processes or import them. Both are supported; the process
form is what `../../results/honest-containment-v1.0/reproduce.md` documents.

### 2.1 `suite/runner.py`

```
python3 suite/runner.py --config <config.json> --agent <system key> \
    --run-index <1|2|3> --out <results runs folder> [--only ID ...] [--limit N] \
    [--customer-mode llm|scripted] [--turn-cap 24] [--dry-run] [--self-test]
```

Writes `<out>/<system>/run-<n>/run.json` and `<out>/<system>/run-<n>/contacts.jsonl`.
Exit codes: `0` completed or dry run, `3` preflight failed and `not run` records were
written, non-zero otherwise.

### 2.2 `suite/scorer.py`

```
python3 suite/scorer.py --run <run folder> --config <config.json> [--no-judge]
```

Writes `scored-contacts.jsonl` and `metrics.json` beside the run.

### 2.3 `suite/ceilings.py`

No arguments. Writes `structural-ceilings.json` in the dataset folder: the highest
containment each definition can reach on this data if an agent follows every policy. A
property of the dataset, not a measurement.

### 2.4 `suite/report.py`

```
python3 suite/report.py --results <results folder> [--write]
```

Reads every `metrics.json` under the results folder and writes `leaderboard.md`,
`definitions-spread.md` and `results.csv`. A missing or `not run` run produces a `not run`
row carrying its reason. It refuses to publish a run whose header says
`publishable: false`.

## 3. The adapter interface

A system under test implements `suite/adapters/base.py::AgentAdapter`. Five methods, and
the docstring in that file is the normative description.

```python
class AgentAdapter(Protocol):
    name: str
    kind: str                                   # chat, voice_platform, internal, replay
    def preflight(self) -> None: ...            # raises NotConfigured(reason)
    def start_contact(self, scenario: dict) -> str: ...
    def greet(self, handle: str) -> AgentTurn | None: ...
    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn: ...
    def end(self, handle: str) -> ContactEnd: ...
```

Register it in `suite/adapters/__init__.py::build` and add a block to the run config. The
harness does not need to know anything else about the system.

What an adapter is given: the scenario's id, domain, company, channel, policy pack and
scope. What an adapter is never given, and what `runner.py` never passes: the hidden caller
script, the ground truth, the traps, the tier, the repeat-contact rule.

## 4. The record schemas

Three JSON Lines files form the interface between the stages. Field names are stable within
a suite major version.

### 4.1 Contact record, written by the runner

```json
{"scenario": "hc-tel-0001", "domain": "telecom", "tier": "T1", "channel": "text",
 "agent": "general-llm", "status": "completed | not_run | failed",
 "not_run_reason": null, "connected": true,
 "customer_mode": "llm | scripted", "customer_model_version": "...",
 "turns": [
   {"index": 1, "role": "agent", "agent_turn": 1, "is_greeting": true, "text": "...",
    "first_token_ms": 210.0, "substantive_first_token_ms": 210.0, "total_ms": 640.0,
    "tool_calls": [], "escalation": null, "disposition": null, "model_version": "..."},
   {"index": 2, "role": "caller", "script_turn": 1, "purpose": "open", "text": "...",
    "emotion": "neutral", "cue": null}],
 "end": {"ended_by": "agent | caller | transfer | caller_said_will_call_back | runner_turn_cap",
         "transfer_to_human": false, "human_joined": false, "callback_booked": false,
         "post_contact_human_work": false, "agent_disposition": "resolved"},
 "escalation_turn": null}
```

### 4.2 Scored contact, written by the scorer

Carries every field the containment definitions read, so that any row in any table can be
traced back to the three conditions that produced it: `resolved`, `transfer_to_human`,
`human_joined`, `human_requested_by_caller`, `agent_disposition`, `repeat_contact`,
`repeat_contact_hours`, `escalation`, `policy`, `turns`, `ttft_ms`, and a `containment`
block with one entry per definition, each carrying `contained` and `reason`.

### 4.3 `metrics.json`, written by the scorer

The aggregate. Every rate is `{numerator, denominator, rate}`, never a bare number, so a
figure can never be quoted without its denominator (charter 3.1.1). Every block that needs
a judge carries `status: not run` and a reason when the judge was not reached.

## 5. Configuration

`suite/config/agents.example.json` is the template. Copy it, fill in every value that reads
`placeholder`, and keep keys in environment variables named in the config. Preflight fails
while any `placeholder` remains, and the failure text names the field.

`suite/config/scope.json` declares the intent classes each domain's agent is configured
for. The harness reads it to produce the in-scope-only containment column that charter
3.9.4 requires beside the full one.

## 6. What the harness must not do

1. Do not change the containment definitions in `suite/definitions.py`. They are the
   charter's, and a change there is a charter major version under section 7.
2. Do not fill a missing figure. A run that did not happen is `not run` with the reason,
   in the table, the csv and the chart, charter 3.1.8.
3. Do not publish a run whose header says `publishable: false`. That flag marks a self test
   or a fixture replay.
4. Do not mix a scripted-customer run and a model-customer run in one table. They are not
   comparable and the header says which is which.
5. Do not average the financial and regulated hallucinated-policy classes into the overall
   rate, charter 3.12.3.
6. Do not sort a table so that our own system rises. Tables sort on the metric, charter 5.6.

## 7. Prerequisites

- Python 3.11. The suite uses the standard library only. `numpy` and `scipy` are needed by
  `tts.py` for the audio, not by the runner or the scorer.
- `espeak-ng` for the audio, and only for regenerating it.
- One interface key per system under test, one for the customer model, one for the judge
  model. The judge model must differ from every model under test, charter 5.9, and the
  runner refuses the run otherwise.
- A spend cap set with each provider before a run. No script sets one.

## 8. Self-test

```
python3 suite/runner.py --config suite/config/selftest.json --agent replay-fixture \
    --self-test --only hc-tel-0001 --out /tmp/hc-selftest
python3 suite/scorer.py --run /tmp/hc-selftest/replay-fixture/run-1 --no-judge
python3 -m pytest suite/tests -q
```

This exercises the whole loop with no model interface. It produces no result: the run
header says `publishable: false` and every judged figure reads `not run`.
