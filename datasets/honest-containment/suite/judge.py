"""Judge models, charter 3.9.3, 3.11 and 3.12, under the rules in charter 5.9.

Three judges, one job each. Every prompt is published in prompts/ and hashed into the
report that used it. A judge sees the transcript, the scenario's ground truth and the
policy pack in force. It never sees the containment definitions, the other judges'
verdicts, or which system produced the transcript.

Rules this file enforces
------------------------
- A judge returns strict JSON against the schema in its prompt. A reply that does not
  parse is retried once with the same prompt; a second failure is recorded as
  `judge_error` and the contact is excluded from the judged figure and counted, never
  guessed at (charter 3.1.2).
- Where a model under test is also used as a judge, `--judge-model` must differ from the
  agent model, and the runner refuses the run otherwise (charter 5.9).
- Every judged contact enters the adjudication pool. Judge agreement with human labels is
  measured on the 60-case set in ../labelling/ and reported as Cohen's kappa. Until those
  labels exist, agreement is unmeasured and every table that depends on a judge says so.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from model_client import ModelClient, NotConfigured

PROMPTS = Path(__file__).resolve().parent / "prompts"

JUDGE_PROMPTS = {
    "resolution": "judge-resolution.md",
    "policy_assertion": "judge-policy-assertion.md",
    "escalation_quality": "judge-escalation-quality.md",
}


def prompt_text(name: str) -> str:
    return (PROMPTS / JUDGE_PROMPTS[name]).read_text(encoding="utf-8")


def prompt_hashes() -> dict:
    out = {}
    for path in sorted(PROMPTS.glob("*.md")):
        out[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return out


def _parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object in the judge reply")
    return json.loads(text[start:end + 1])


class Judge:
    def __init__(self, client: ModelClient):
        self.client = client
        self.model_version = client.spec.model

    def preflight(self) -> None:
        self.client.preflight()

    def _ask(self, name: str, payload: dict) -> dict:
        system = prompt_text(name)
        user = json.dumps(payload, ensure_ascii=False)
        last: Exception | None = None
        for _ in range(2):
            reply = self.client.complete(system, [{"role": "user", "content": user}])
            self.model_version = reply.model_version
            try:
                out = _parse_json(reply.text)
                out["_judge_model_version"] = reply.model_version
                return out
            except (ValueError, json.JSONDecodeError) as exc:
                last = exc
        return {"judge_error": f"unparseable judge reply: {last}",
                "_judge_model_version": self.model_version}

    def resolution(self, scenario: dict, transcript: list[dict]) -> dict:
        return self._ask("resolution", {
            "scenario_id": scenario["id"],
            "domain": scenario["domain"],
            "caller_intent": scenario["intent"]["label"],
            "second_intent": (scenario["secondary_intent"] or {}).get("label"),
            "ground_truth_resolution": scenario["ground_truth"]["resolution"],
            "resolution_code": scenario["ground_truth"]["resolution_code"],
            "required_actions": scenario["ground_truth"]["required_actions"],
            "prohibited_moves": scenario["ground_truth"]["must_not"],
            "escalation_required": scenario["ground_truth"]["escalation_required"],
            "transcript": transcript,
        })

    def policy_assertion(self, scenario: dict, transcript: list[dict],
                         pack_text: dict, unmatched: list[dict]) -> dict:
        return self._ask("policy_assertion", {
            "scenario_id": scenario["id"],
            "policy_pack": pack_text,
            "superseded_documents_in_pack": scenario["superseded_in_pack"],
            "transcript": transcript,
            "quantities_the_rule_pass_could_not_match": unmatched,
        })

    def escalation_quality(self, scenario: dict, transcript: list[dict],
                           escalation_event: dict | None) -> dict:
        gt = scenario["ground_truth"]
        return self._ask("escalation_quality", {
            "scenario_id": scenario["id"],
            "escalation_required": gt["escalation_required"],
            "expected": gt["escalation"],
            "escalation_event": escalation_event,
            "transcript": transcript,
        })
