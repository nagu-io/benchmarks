"""Baseline: a developer voice platform reached over its own HTTP interface.

Two platform slots are scored, `voice-platform-a` and `voice-platform-b`. This adapter is
generic on purpose. It is driven by a configuration block that names the endpoints, the
authentication header and the JSON paths to read a reply, a transfer and a disposition
out of the platform's response. Nothing about any platform's API is written into this
file, because this environment cannot reach a platform to verify it, and a plausible
endpoint written from memory is an invented fact.

Whoever runs the benchmark fills the configuration in from the platform's current API
documentation and records the documentation date in the run configuration. The report then
names the platform, its documentation date and its agent version string. Until that
happens, `preflight()` refuses the run and the results row reads `not run` with the reason.

Configuration block, in config/agents.example.json:

    "voice-platform-a": {
      "adapter": "voice_platform",
      "display_name": "developer voice platform A",
      "base_url": "placeholder - the platform's API base, from its current docs",
      "api_key_env": "VOICE_PLATFORM_A_KEY",
      "docs_date": "placeholder - the date of the API documentation used",
      "paths": {
        "create_session": {"method": "POST", "path": "placeholder", "body": {}},
        "send_turn":      {"method": "POST", "path": "placeholder", "body": {}},
        "end_session":    {"method": "POST", "path": "placeholder", "body": {}}
      },
      "response_paths": {
        "reply_text": "placeholder json path",
        "first_token_ms": "placeholder json path",
        "transfer": "placeholder json path",
        "transfer_destination": "placeholder json path",
        "disposition": "placeholder json path"
      },
      "sends_audio": true,
      "receives_interface_addendum": false
    }

Every value written `placeholder` must be replaced before a run. The adapter checks for the
word and refuses while it is present, so a misconfigured run cannot produce a number.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from adapters.base import AgentTurn, ContactEnd
from model_client import NotConfigured

PLACEHOLDER = "placeholder"


def dig(obj, path: str):
    """Read a dotted json path. `a.b.0.c` walks objects and arrays."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class VoicePlatformAdapter:
    kind = "voice_platform"

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.display_name = config.get("display_name", name)
        self._sessions: dict[str, dict] = {}

    def preflight(self) -> None:
        cfg = self.config
        blanks = [k for k, v in cfg.items() if isinstance(v, str) and PLACEHOLDER in v]
        for group in ("paths", "response_paths"):
            for k, v in (cfg.get(group) or {}).items():
                text = json.dumps(v)
                if PLACEHOLDER in text:
                    blanks.append(f"{group}.{k}")
        if blanks:
            raise NotConfigured(
                f"{self.name} is not configured: {', '.join(sorted(set(blanks)))} still "
                f"read placeholder. Fill them in from the platform's current API "
                f"documentation and record the documentation date in the run config.")
        env = cfg.get("api_key_env", "")
        if not env or not os.environ.get(env):
            raise NotConfigured(
                f"{self.name} has no interface key: environment variable "
                f"{env or '(unset in config)'} is not set")

    def _call(self, spec: dict, payload: dict) -> dict:
        url = self.config["base_url"].rstrip("/") + spec["path"]
        body = dict(spec.get("body") or {})
        body.update(payload)
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method=spec.get("method", "POST"),
            headers={"content-type": "application/json",
                     "authorization": f"Bearer {os.environ[self.config['api_key_env']]}"})
        try:
            with urllib.request.urlopen(req, timeout=self.config.get("timeout_s", 60)) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise NotConfigured(f"{self.name} unreachable: {exc}") from exc

    def start_contact(self, scenario: dict) -> str:
        out = self._call(self.config["paths"]["create_session"],
                         {"scenario": scenario["id"], "channel": scenario["channel"]})
        handle = str(out.get("id") or scenario["id"])
        self._sessions[handle] = {"raw": out, "end": ContactEnd("agent")}
        return handle

    def greet(self, handle: str) -> AgentTurn | None:
        return None

    def send(self, handle: str, caller_text: str, audio_path: str | None) -> AgentTurn:
        payload = {"session": handle, "text": caller_text}
        if self.config.get("sends_audio") and audio_path:
            payload["audio_path"] = audio_path
        started = time.perf_counter()
        out = self._call(self.config["paths"]["send_turn"], payload)
        total = (time.perf_counter() - started) * 1000.0
        rp = self.config["response_paths"]
        text = dig(out, rp["reply_text"]) or ""
        ttft = dig(out, rp["first_token_ms"])
        transfer = bool(dig(out, rp["transfer"]))
        escalation = None
        if transfer:
            escalation = {"destination": dig(out, rp["transfer_destination"]) or "",
                          "fields": dig(out, rp.get("transfer_fields", "")) or {}}
            self._sessions[handle]["end"] = ContactEnd(
                "transfer", transfer_to_human=True, human_joined=True,
                agent_disposition=dig(out, rp["disposition"]) or "transferred")
        return AgentTurn(text=text,
                         first_token_ms=float(ttft) if ttft is not None else None,
                         substantive_first_token_ms=float(ttft) if ttft is not None else None,
                         total_ms=total, escalation=escalation,
                         disposition=dig(out, rp["disposition"]),
                         model_version=str(dig(out, rp.get("agent_version", "")) or ""))

    def end(self, handle: str) -> ContactEnd:
        session = self._sessions.pop(handle, {})
        try:
            self._call(self.config["paths"]["end_session"], {"session": handle})
        except NotConfigured:
            pass
        return session.get("end", ContactEnd("runner_turn_cap"))
