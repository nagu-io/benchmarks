"""Baseline: a general-purpose language model given the published reference agent prompt.

No tools, no retrieval, no memory beyond the contact. The policy pack is placed in the
prompt in full, which is what the prompt says it is. This is the baseline that answers
"what does a good general model do with the documents and nothing else".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from adapters.base import CONTROL_DISPOSITION, CONTROL_TRANSFER, AgentTurn, ContactEnd
from model_client import ModelClient, NotConfigured

DATASET = Path(__file__).resolve().parent.parent.parent
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def load_pack(scenario: dict) -> str:
    parts = []
    for doc_id in scenario["policy_pack"] + scenario["superseded_in_pack"]:
        path = DATASET / "policies" / scenario["domain"] / f"{doc_id}.md"
        parts.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def parse_controls(text: str) -> tuple[str, dict | None, str | None]:
    escalation = None
    m = re.search(CONTROL_TRANSFER, text, re.S)
    if m:
        fields = {}
        if m.group(2):
            try:
                fields = json.loads(m.group(2))
            except json.JSONDecodeError:
                fields = {"unparsed": m.group(2)}
        escalation = {"destination": m.group(1), "fields": fields}
    disposition = None
    d = re.search(CONTROL_DISPOSITION, text)
    if d:
        disposition = d.group(1)
    clean = re.sub(CONTROL_TRANSFER, "", text, flags=re.S)
    clean = re.sub(CONTROL_DISPOSITION, "", clean).strip()
    return clean, escalation, disposition


class GeneralLLMAdapter:
    kind = "chat"

    def __init__(self, name: str, client: ModelClient, opens_contact: bool = True):
        self.name = name
        self.client = client
        self.opens_contact = opens_contact
        self._contacts: dict[str, dict] = {}

    def preflight(self) -> None:
        self.client.preflight()

    def start_contact(self, scenario: dict) -> str:
        system = (PROMPTS / "reference-agent.md").read_text(encoding="utf-8")
        system = system.split("---", 1)[1] if "---" in system else system
        system = (system.replace("{{company}}", scenario["company"])
                        .replace("{{channel}}", scenario["channel"])
                        .replace("{{policy_pack}}", load_pack(scenario)))
        system += "\n\n" + (PROMPTS / "interface-addendum.md").read_text(encoding="utf-8")
        handle = scenario["id"]
        self._contacts[handle] = {"system": system, "messages": [], "end": ContactEnd("agent")}
        return handle

    def greet(self, handle: str) -> AgentTurn | None:
        if not self.opens_contact:
            return None
        return self._turn(handle, "[the contact has connected; open it]", greeting=True)

    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn:
        return self._turn(handle, caller_text)

    def _turn(self, handle: str, user_text: str, greeting: bool = False) -> AgentTurn:
        state = self._contacts[handle]
        state["messages"].append({"role": "user", "content": user_text})
        reply = self.client.complete(state["system"], state["messages"])
        state["messages"].append({"role": "assistant", "content": reply.text})
        clean, escalation, disposition = parse_controls(reply.text)
        if escalation:
            state["end"] = ContactEnd("transfer", transfer_to_human=True, human_joined=True,
                                      agent_disposition=disposition or "transferred")
        elif disposition:
            state["end"] = ContactEnd("agent", agent_disposition=disposition)
        return AgentTurn(text=clean, first_token_ms=reply.first_token_ms,
                         substantive_first_token_ms=reply.first_token_ms,
                         total_ms=reply.total_ms, escalation=escalation,
                         disposition=disposition, model_version=reply.model_version)

    def end(self, handle: str) -> ContactEnd:
        return self._contacts.pop(handle, {}).get("end", ContactEnd("runner_turn_cap"))
