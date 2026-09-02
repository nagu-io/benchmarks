"""The adapter boundary.

This is the interface entail-bench wires into. A system under test is anything that
implements AgentAdapter. Nothing else in the suite knows how a system is reached.

Contract, in words:

- `preflight()` raises NotConfigured with a reason a results row can carry, or returns.
  It never makes a scored call.
- `start_contact(scenario)` returns an opaque handle. It may set the system's policy pack,
  scope and prompt from the scenario. It must not be given the hidden caller script, the
  ground truth or the traps, and the runner does not pass them.
- `greet(handle)` returns the agent's opening turn or None where the system does not open.
  Its time to first token is recorded separately, charter 3.13.3, because an opening is
  often cached.
- `send(handle, caller_text, audio_path)` returns one AgentTurn. `audio_path` is the
  caller-side wav for a voice contact; a text system ignores it and the report says which
  systems received audio and which received text.
- `end(handle)` returns a ContactEnd. It is called exactly once.

Timing. `first_token_ms` is measured from the moment the runner finishes sending the caller
turn to the first token or audio sample of the reply. `substantive_first_token_ms` is the
first token of the reply that answers the caller, which differs from the first where the
system emits a holding phrase, charter 3.13.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from model_client import NotConfigured  # re-exported for adapter authors


@dataclass
class AgentTurn:
    text: str
    first_token_ms: float | None
    substantive_first_token_ms: float | None
    total_ms: float | None
    tool_calls: list[dict] = field(default_factory=list)
    filler_before_answer: bool = False
    escalation: dict | None = None
    disposition: str | None = None
    model_version: str = ""
    error: str | None = None


@dataclass
class ContactEnd:
    ended_by: str                    # agent, caller, transfer, runner_turn_cap, error
    transfer_to_human: bool = False
    human_joined: bool = False       # transfer, callback taken, or work done afterwards
    callback_booked: bool = False
    post_contact_human_work: bool = False
    agent_disposition: str = "unresolved"
    platform_notes: dict = field(default_factory=dict)


class AgentAdapter(Protocol):
    name: str
    kind: str

    def preflight(self) -> None: ...
    def start_contact(self, scenario: dict) -> str: ...
    def greet(self, handle: str) -> AgentTurn | None: ...
    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn: ...
    def end(self, handle: str) -> ContactEnd: ...


CONTROL_TRANSFER = r"\[\[TRANSFER\s+destination=\"([^\"]*)\"\s*(?:fields=(\{.*?\}))?\s*\]\]"
CONTROL_DISPOSITION = r"\[\[DISPOSITION\s+code=\"([^\"]*)\"\s*\]\]"
