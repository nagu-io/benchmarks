"""HTTP transport, and the recorded transport the contract tests drive.

Splitting the call from the parsing is what lets every adapter be tested with no
network: a contract test feeds a recorded fixture through the same
`_parse_response` the live path uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import AdapterCallError


@dataclass
class Request:
    method: str
    url: str
    headers: dict = field(default_factory=dict)
    json_body: dict | None = None
    data: bytes | None = None
    timeout: float = 120.0


class HttpTransport:
    """A thin httpx wrapper. Imported lazily so the package installs without it."""

    def send(self, request: Request) -> dict:
        try:
            import httpx
        except ImportError as exc:                       # pragma: no cover
            raise AdapterCallError(
                "httpx is not installed. Install it with: pip install httpx"
            ) from exc
        try:
            with httpx.Client(timeout=request.timeout) as client:
                resp = client.request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    json=request.json_body,
                    content=request.data,
                )
        except Exception as exc:                         # noqa: BLE001
            raise AdapterCallError(f"{type(exc).__name__}: {exc}") from exc
        if resp.status_code >= 400:
            raise AdapterCallError(f"HTTP {resp.status_code}: {resp.text[:400]}")
        try:
            return resp.json()
        except Exception as exc:                         # noqa: BLE001
            raise AdapterCallError(f"response was not JSON: {resp.text[:400]}") from exc


class RecordedTransport:
    """Replays recorded provider payloads. Used by the adapter contract tests.

    A recorded fixture is synthetic and is labelled as such in
    `tests/fixtures/`. Nothing this transport returns is ever written into a
    results file as a model result: the runner refuses to score a run whose
    adapter is not live unless the run is stamped `synthetic: true`.
    """

    synthetic = True

    def __init__(self, payloads: list[dict] | dict, record_requests: bool = True):
        self.payloads = payloads if isinstance(payloads, list) else [payloads]
        self.requests: list[Request] = []
        self.record_requests = record_requests
        self._index = 0

    def send(self, request: Request) -> Any:
        if self.record_requests:
            self.requests.append(request)
        if not self.payloads:
            raise AdapterCallError("recorded transport has no payloads left")
        payload = self.payloads[min(self._index, len(self.payloads) - 1)]
        self._index += 1
        if isinstance(payload, dict) and payload.get("__error__"):
            raise AdapterCallError(str(payload["__error__"]))
        return payload


def load_fixture(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
