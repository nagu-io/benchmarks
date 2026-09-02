"""The one place in this suite that talks to a model interface.

Every path to a provider runs through here so that a run with no key fails in one place,
with one reason, and writes `not run` rather than a number. Nothing in this file invents
a response, and there is no offline fallback that produces model-shaped text.

Configuration comes from the run configuration file and from the environment. No key is
read from, written to or logged by this file: only the name of the environment variable
that was missing appears in a reason string.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class NotConfigured(RuntimeError):
    """No usable interface. Carries the reason that reaches the results row."""


@dataclass
class ModelSpec:
    role: str                 # agent, customer or judge
    provider: str             # openai_compatible, anthropic_messages, http_generic
    base_url: str
    model: str
    api_key_env: str
    max_output_tokens: int = 900
    temperature: float = 0.0
    timeout_s: float = 60.0
    extra_headers: dict | None = None

    @classmethod
    def from_dict(cls, role: str, d: dict) -> "ModelSpec":
        return cls(role=role, provider=d["provider"], base_url=d["base_url"],
                   model=d["model"], api_key_env=d["api_key_env"],
                   max_output_tokens=d.get("max_output_tokens", 900),
                   temperature=d.get("temperature", 0.0),
                   timeout_s=d.get("timeout_s", 60.0),
                   extra_headers=d.get("extra_headers"))


@dataclass
class Reply:
    text: str
    first_token_ms: float
    total_ms: float
    model_version: str
    raw: dict


class ModelClient:
    def __init__(self, spec: ModelSpec):
        self.spec = spec

    def preflight(self) -> None:
        """Raise NotConfigured with the exact reason, or return."""
        key = os.environ.get(self.spec.api_key_env)
        if not key:
            raise NotConfigured(
                f"no interface key: environment variable {self.spec.api_key_env} is not set "
                f"for the {self.spec.role} model {self.spec.model}")
        if not self.spec.base_url.startswith("https://"):
            raise NotConfigured(
                f"{self.spec.role} base_url is not an https endpoint: {self.spec.base_url}")

    def complete(self, system: str, messages: list[dict]) -> Reply:
        """One turn. Streaming is used where the provider supports it, because time to
        first token in charter 3.13 is measured at the first token and not at the last."""
        self.preflight()
        key = os.environ[self.spec.api_key_env]
        if self.spec.provider == "openai_compatible":
            url = self.spec.base_url.rstrip("/") + "/chat/completions"
            body = {"model": self.spec.model, "temperature": self.spec.temperature,
                    "max_tokens": self.spec.max_output_tokens, "stream": True,
                    "messages": [{"role": "system", "content": system}] + messages}
            headers = {"authorization": f"Bearer {key}", "content-type": "application/json"}
        elif self.spec.provider == "anthropic_messages":
            url = self.spec.base_url.rstrip("/") + "/v1/messages"
            body = {"model": self.spec.model, "system": system, "messages": messages,
                    "max_tokens": self.spec.max_output_tokens,
                    "temperature": self.spec.temperature, "stream": True}
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
                       "content-type": "application/json"}
        else:
            raise NotConfigured(f"unknown provider {self.spec.provider}")
        headers.update(self.spec.extra_headers or {})

        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers=headers, method="POST")
        started = time.perf_counter()
        first = None
        chunks: list[str] = []
        version = self.spec.model
        try:
            with urllib.request.urlopen(req, timeout=self.spec.timeout_s) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload in ("", "[DONE]"):
                        continue
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    piece = _extract_delta(event, self.spec.provider)
                    if piece:
                        if first is None:
                            first = time.perf_counter()
                        chunks.append(piece)
                    version = event.get("model") or version
        except urllib.error.URLError as exc:
            raise NotConfigured(
                f"{self.spec.role} interface unreachable at {self.spec.base_url}: {exc}") from exc
        total = (time.perf_counter() - started) * 1000.0
        ttft = ((first - started) * 1000.0) if first else total
        return Reply(text="".join(chunks), first_token_ms=ttft, total_ms=total,
                     model_version=str(version), raw={})


def _extract_delta(event: dict, provider: str) -> str:
    if provider == "openai_compatible":
        try:
            return event["choices"][0]["delta"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            return ""
    if provider == "anthropic_messages":
        if event.get("type") == "content_block_delta":
            return event.get("delta", {}).get("text", "") or ""
        return ""
    return ""
