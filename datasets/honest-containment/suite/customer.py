"""The simulated customer.

Two modes, and a run record always says which was used, because they are not comparable.

llm       a model plays the caller from the hidden script. It is told the beats, what it
          must convey and what it must never volunteer. This is the mode the benchmark
          reports, and it needs an interface key.
scripted  the beats are replayed verbatim with no model in the loop. It exists so that
          the harness and the scorer can be exercised end to end without a model, and so
          that a run can be reproduced deterministically. A scripted run is marked
          `customer_mode: scripted` and is never published in the same table as an llm run.

The customer never repairs the agent's mistakes, never volunteers a fact outside
`must_convey`, and never mentions the ground truth. The prompt is in
prompts/customer-simulator.md and is published with the suite.
"""

from __future__ import annotations

import json
from pathlib import Path

from model_client import ModelClient, NotConfigured

PROMPTS = Path(__file__).resolve().parent / "prompts"


class ScriptedCustomer:
    mode = "scripted"

    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.turns = scenario["hidden_script"]["turns"]
        self.cursor = 0

    def next_turn(self, agent_history: list[dict], outcome_reached: bool) -> dict | None:
        while self.cursor < len(self.turns):
            beat = self.turns[self.cursor]
            self.cursor += 1
            if beat["purpose"] == "callback_cue" and outcome_reached:
                continue
            text = (beat["native_text"] + " " + beat["text"]).strip() if beat["native_text"] \
                else beat["text"]
            return {"script_turn": beat["index"], "purpose": beat["purpose"],
                    "text": text, "emotion": beat["emotion"], "cue": beat["cue"],
                    "ends_contact": beat["purpose"] in ("close", "callback_cue")}
        return None


class LLMCustomer:
    mode = "llm"

    def __init__(self, scenario: dict, client: ModelClient):
        self.scenario = scenario
        self.client = client
        self.cursor = 0
        self.turns = scenario["hidden_script"]["turns"]
        self.system = (PROMPTS / "customer-simulator.md").read_text(encoding="utf-8")

    def preflight(self) -> None:
        self.client.preflight()

    def next_turn(self, agent_history: list[dict], outcome_reached: bool) -> dict | None:
        while self.cursor < len(self.turns):
            beat = self.turns[self.cursor]
            self.cursor += 1
            if beat["purpose"] == "callback_cue" and outcome_reached:
                continue
            brief = {
                "beat": beat["purpose"],
                "must_convey": beat["must_convey"],
                "emotion": beat["emotion"],
                "reference_wording": beat["text"],
                "non_english_wording": beat["native_text"] or None,
                "language_condition": self.scenario["language"]["label"],
                "language_mode": self.scenario["language"]["mode"],
                "caller_name": self.scenario["caller"]["name"],
                "conversation_so_far": agent_history[-8:],
            }
            reply = self.client.complete(self.system, [{"role": "user",
                                                        "content": json.dumps(brief,
                                                                              ensure_ascii=False)}])
            text = reply.text.strip() or beat["text"]
            return {"script_turn": beat["index"], "purpose": beat["purpose"],
                    "text": text, "emotion": beat["emotion"], "cue": beat["cue"],
                    "ends_contact": beat["purpose"] in ("close", "callback_cue"),
                    "customer_model_version": reply.model_version}
        return None


def build_customer(scenario: dict, mode: str, client: ModelClient | None):
    if mode == "scripted":
        return ScriptedCustomer(scenario)
    if client is None:
        raise NotConfigured("customer mode llm needs a customer model in the run config")
    return LLMCustomer(scenario, client)
