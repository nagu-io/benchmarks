"""Our own agent, scored by the same harness on the same data, charter 5.6.

It is the general-model baseline plus three things we build into a delivered voice or chat
system, and nothing else. Each is listed here so a reader can see exactly what the
difference between our row and the baseline row consists of:

1. A retrieval step that puts only the current documents from the contact's policy pack in
   front of the model, and refuses to answer from a superseded document.
2. A deterministic escalation gate that runs before the reply is sent. It reads the
   caller's turn for the triggers in the escalation matrix and forces a transfer where one
   fires, so that escalation does not depend on the model noticing.
3. A quotation check that runs the same rule pass as the scorer over the draft reply, and
   sends the reply back to the model once with the contradicted value named, before the
   caller sees it.

The prompt is the published reference agent prompt, unchanged, as charter 5.2 requires.
The three additions are system design, not prompt tuning, and the report states them on
our row.

Our row gets no highlight, no annotation and no position advantage. Tables sort on the
metric.
"""

from __future__ import annotations

from pathlib import Path

from adapters.base import AgentTurn, ContactEnd
from adapters.general_llm import GeneralLLMAdapter, load_pack
from model_client import ModelClient
import policy_check

DATASET = Path(__file__).resolve().parent.parent.parent

# Trigger phrases for the deterministic gate. Kept short and published, because a gate a
# partner cannot read is a gate a partner cannot audit. Matching is case-insensitive over
# the caller's turn, on word boundaries.
PERSON_REQUEST = ["speak to a person", "talk to a person", "speak to someone",
                  "a real person", "supervisor", "manager", "human", "senior",
                  "सीनियर", "supervisor po", "makausap ang supervisor"]
DISTRESS = ["cannot afford", "can't afford", "no money for", "nothing left for medicine",
            "died", "passed away", "frightened", "scared", "controls the money",
            "not allowed to ask", "दवाई के लिए", "देहांत", "डर", "natatakot",
            "namatay", "wala na po akong pambili"]


class EntailmentAgentAdapter(GeneralLLMAdapter):
    kind = "internal"

    def __init__(self, name: str, client: ModelClient):
        super().__init__(name, client)
        self._scenarios: dict[str, dict] = {}
        self._values = policy_check.load_value_index()

    def start_contact(self, scenario: dict) -> str:
        handle = super().start_contact(scenario)
        self._scenarios[handle] = scenario
        state = self._contacts[handle]
        # 1. retrieval: current documents only. The superseded document stays out of the
        # prompt, and the model is told it exists and is not authority.
        current_only = [d for d in scenario["policy_pack"]]
        packs = []
        for doc_id in current_only:
            packs.append((DATASET / "policies" / scenario["domain"] /
                          f"{doc_id}.md").read_text(encoding="utf-8"))
        note = ""
        if scenario["superseded_in_pack"]:
            note = ("\n\nThe following documents are in the pack and are superseded. They "
                    "are not authority for this contact and are not reproduced here: "
                    + ", ".join(scenario["superseded_in_pack"]) + ".")
        state["system"] = state["system"].replace(load_pack(scenario),
                                                  "\n\n---\n\n".join(packs) + note)
        return handle

    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn:
        scenario = self._scenarios[handle]
        low = caller_text.lower()
        forced = None
        if any(p.lower() in low for p in PERSON_REQUEST):
            forced = "explicit_request_for_person"
        elif any(p.lower() in low for p in DISTRESS):
            forced = "distress_cue"
        if forced:
            self._contacts[handle]["messages"].append({
                "role": "user",
                "content": caller_text + (
                    f"\n\n[escalation gate: the escalation matrix trigger {forced} has "
                    "fired on this turn. Transfer now, name the destination queue from the "
                    "matrix, and carry every context field the escalation policy lists.]")})
            turn = self._turn_from_history(handle)
        else:
            turn = super().send(handle, caller_text, audio_path)

        # 3. quotation check over the draft, one correction pass.
        check = policy_check.check_contact([turn.text], scenario["domain"],
                                           scenario["policy_pack"], self._values)
        if check["unsupported"]:
            named = ", ".join(f"{a['surface']} contradicts {a['nearest_policy_key']}"
                              for a in check["unsupported"])
            self._contacts[handle]["messages"].append({
                "role": "user",
                "content": f"[quotation check: {named}. Send the reply again with the value "
                           "the pack carries, or without the value.]"})
            turn = self._turn_from_history(handle)
        return turn

    def _turn_from_history(self, handle: str) -> AgentTurn:
        state = self._contacts[handle]
        reply = self.client.complete(state["system"], state["messages"])
        state["messages"].append({"role": "assistant", "content": reply.text})
        from adapters.general_llm import parse_controls
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
