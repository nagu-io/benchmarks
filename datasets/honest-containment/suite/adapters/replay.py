"""Replay of a recorded contact record. Not a system under test.

It exists so the scorer can be exercised on fixed input in tests/. A replay run is written
with `agent_kind: replay` and the scorer refuses to put it in a leaderboard table, because
a fixture is not a result. See tests/fixtures/README.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from adapters.base import AgentTurn, ContactEnd
from model_client import NotConfigured


class ReplayAdapter:
    kind = "replay"

    SUITE = Path(__file__).resolve().parent.parent

    def __init__(self, name: str, config: dict):
        self.name = name
        given = Path(config["fixture"])
        # A fixture path in a config is resolved against the suite folder, so the
        # documented commands work from any working directory.
        self.path = given if given.is_absolute() else (self.SUITE / given)
        self._records: dict[str, dict] = {}
        self._cursor: dict[str, int] = {}

    def preflight(self) -> None:
        if not self.path.exists():
            raise NotConfigured(f"replay fixture not found: {self.path}")
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                self._records[rec["scenario"]] = rec

    def start_contact(self, scenario: dict) -> str:
        if scenario["id"] not in self._records:
            raise NotConfigured(f"replay fixture has no contact for {scenario['id']}")
        self._cursor[scenario["id"]] = 0
        return scenario["id"]

    def _next_agent_turn(self, handle: str) -> AgentTurn | None:
        rec = self._records[handle]
        turns = [t for t in rec["turns"] if t["role"] == "agent"]
        i = self._cursor[handle]
        if i >= len(turns):
            return None
        self._cursor[handle] = i + 1
        t = turns[i]
        return AgentTurn(text=t["text"], first_token_ms=t.get("first_token_ms"),
                         substantive_first_token_ms=t.get("substantive_first_token_ms"),
                         total_ms=t.get("total_ms"), escalation=t.get("escalation"),
                         disposition=t.get("disposition"), model_version="replay")

    def greet(self, handle: str) -> AgentTurn | None:
        return self._next_agent_turn(handle)

    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn:
        turn = self._next_agent_turn(handle)
        return turn or AgentTurn(text="", first_token_ms=None,
                                 substantive_first_token_ms=None, total_ms=None,
                                 error="replay fixture exhausted")

    def end(self, handle: str) -> ContactEnd:
        e = self._records[handle]["end"]
        return ContactEnd(ended_by=e["ended_by"],
                          transfer_to_human=e.get("transfer_to_human", False),
                          human_joined=e.get("human_joined", False),
                          callback_booked=e.get("callback_booked", False),
                          post_contact_human_work=e.get("post_contact_human_work", False),
                          agent_disposition=e.get("agent_disposition", "unresolved"))
