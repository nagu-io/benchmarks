"""The adapter interface every system under test is scored through.

    Adapter.extract(document, prompt) -> Response

One interface, one scorer, one prompt. A model, a document service and a
partner's own pipeline are scored by the same code path, which is the point.

Availability
------------
Every adapter reads its credential from an environment variable. When the
variable is absent the adapter reports itself unavailable and the run records
that model as `not run` with the reason. It never falls back to a stub, and a
stub result is never written into a results file. No key is hard-coded anywhere
in this package, and no key value is ever written to a results folder.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ..dataset import Document
from ..errors import AdapterCallError, AdapterUnavailable
from ..prompts import Prompt


# --------------------------------------------------------------------------- #
# Value types                                                                  #
# --------------------------------------------------------------------------- #


@dataclass
class TokenCounts:
    input: int | None = None
    output: int | None = None
    reasoning: int | None = None

    def as_dict(self) -> dict:
        return {"input": self.input, "output": self.output, "reasoning": self.reasoning}

    def __add__(self, other: "TokenCounts") -> "TokenCounts":
        def add(a, b):
            if a is None and b is None:
                return None
            return (a or 0) + (b or 0)
        return TokenCounts(
            add(self.input, other.input),
            add(self.output, other.output),
            add(self.reasoning, other.reasoning),
        )


@dataclass
class Response:
    """What one document's extraction produced.

    `fields` and `confidence` are the parsed structure. `raw_text` is what the
    system returned before parsing, kept so a disputed figure can be re-scored
    without re-running the model (charter 7.5).
    """

    doc_id: str
    ok: bool = True
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""
    tokens: TokenCounts = field(default_factory=TokenCounts)
    latency_s: float | None = None
    backoff_s: float = 0.0
    model_version: str | None = None
    pages_billed: int | None = None
    requests: int = 0
    retries: int = 0
    error: str | None = None
    error_kind: str | None = None          # parse_error | call_error | timeout
    confidence_reported: bool = False
    interface_notes: list[str] = field(default_factory=list)
    provider_meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        from ..util import redact

        return {
            "doc_id": self.doc_id,
            "ok": self.ok,
            "fields": self.fields,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "tokens": self.tokens.as_dict(),
            "latency_s": self.latency_s,
            "backoff_s": self.backoff_s,
            "model_version": self.model_version,
            "pages_billed": self.pages_billed,
            "requests": self.requests,
            "retries": self.retries,
            "error": self.error,
            "error_kind": self.error_kind,
            "confidence_reported": self.confidence_reported,
            "interface_notes": self.interface_notes,
            "provider_meta": redact(self.provider_meta),
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Response":
        tokens = raw.get("tokens") or {}
        return cls(
            doc_id=raw["doc_id"],
            ok=bool(raw.get("ok", True)),
            fields=raw.get("fields") or {},
            confidence=raw.get("confidence") or {},
            raw_text=raw.get("raw_text") or "",
            tokens=TokenCounts(tokens.get("input"), tokens.get("output"), tokens.get("reasoning")),
            latency_s=raw.get("latency_s"),
            backoff_s=raw.get("backoff_s") or 0.0,
            model_version=raw.get("model_version"),
            pages_billed=raw.get("pages_billed"),
            requests=int(raw.get("requests") or 0),
            retries=int(raw.get("retries") or 0),
            error=raw.get("error"),
            error_kind=raw.get("error_kind"),
            confidence_reported=bool(raw.get("confidence_reported", False)),
            interface_notes=list(raw.get("interface_notes") or []),
            provider_meta=raw.get("provider_meta") or {},
        )


@dataclass(frozen=True)
class Availability:
    available: bool
    reason: str = ""
    env_var: str | None = None

    def as_dict(self) -> dict:
        return {"available": self.available, "reason": self.reason, "env_var": self.env_var}


@dataclass
class AdapterSpec:
    """How a named model is reached. Registered in `data/models.yaml`."""

    name: str
    adapter: str
    provider: str
    model_id: str | None = None
    kind: str = "model"                    # model | document_service | pipeline
    env_vars: list[str] = field(default_factory=list)
    optional_env_vars: list[str] = field(default_factory=list)
    price_key: str | None = None
    options: dict = field(default_factory=dict)
    note: str = ""


# --------------------------------------------------------------------------- #
# Base adapter                                                                 #
# --------------------------------------------------------------------------- #


class Adapter:
    """Base class. Subclasses implement `_build_request` and `_parse_response`.

    `extract` is the contract every system is scored through. It times the call
    from immediately before the first provider call to the moment the parsed
    output is returned, which is the admission-to-output clock of charter
    section 3.8.2.
    """

    adapter_name = "base"
    provider = "unknown"
    #: Environment variables that must be present for this adapter to run.
    required_env: tuple[str, ...] = ()
    optional_env: tuple[str, ...] = ()
    #: Mechanical interface differences, listed per model in the report
    #: (charter section 5.2).
    interface_notes: tuple[str, ...] = ()

    def __init__(self, spec: AdapterSpec, options: dict | None = None, transport=None):
        self.spec = spec
        self.options = {**spec.options, **(options or {})}
        self.transport = transport
        self._model_version: str | None = None

    # -- availability ---------------------------------------------------- #
    @property
    def env_vars(self) -> tuple[str, ...]:
        return tuple(self.spec.env_vars) or self.required_env

    def availability(self) -> Availability:
        missing = [v for v in self.env_vars if not os.environ.get(v, "").strip()]
        if missing:
            return Availability(
                False,
                f"environment variable{'s' if len(missing) > 1 else ''} "
                f"{', '.join(missing)} not set",
                env_var=missing[0],
            )
        return self._extra_availability()

    def _extra_availability(self) -> Availability:
        return Availability(True, "", env_var=self.env_vars[0] if self.env_vars else None)

    def require_available(self) -> None:
        state = self.availability()
        if not state.available:
            raise AdapterUnavailable(state.reason)

    def _env(self, name: str, default: str = "") -> str:
        return os.environ.get(name, default).strip()

    def begin_run(self, run_index: int) -> None:
        """Called before each of the three runs. Adapters reset per-run state here.

        Charter 5.4: the three runs are at identical settings, so nothing may
        carry over from one run into the next.
        """
        return

    # -- the contract ---------------------------------------------------- #
    def extract(self, document: Document, prompt: Prompt) -> Response:
        self.require_available()
        rendered = prompt.render(document)
        started = time.perf_counter()
        backoff = 0.0
        requests = 0
        retries = 0
        last_error: Exception | None = None
        payload = None
        max_attempts = int(self.options.get("max_retries", 2)) + 1

        for attempt in range(max_attempts):
            requests += 1
            try:
                payload = self._call(document, rendered)
                break
            except AdapterUnavailable:
                raise
            except Exception as exc:                     # noqa: BLE001 - recorded, not raised
                last_error = exc
                retries += 1
                if attempt == max_attempts - 1:
                    payload = None
                    break
                wait = float(self.options.get("retry_backoff_s", 1.0)) * (2 ** attempt)
                # Charter 3.8.4: backoff is reported separately, so it is the
                # time actually spent waiting, measured, not the time intended.
                waited_from = time.perf_counter()
                self._sleep(wait)
                backoff += time.perf_counter() - waited_from

        elapsed = time.perf_counter() - started
        if payload is None:
            return Response(
                doc_id=document.doc_id,
                ok=False,
                latency_s=elapsed,
                backoff_s=backoff,
                requests=requests,
                retries=retries,
                model_version=self._model_version or self.spec.model_id,
                error=str(last_error) if last_error else "call failed",
                error_kind="call_error",
                interface_notes=list(self.interface_notes),
            )

        response = self._parse_response(payload, document)
        response.doc_id = document.doc_id
        response.latency_s = elapsed
        response.backoff_s = backoff
        response.requests = requests
        response.retries = retries
        response.interface_notes = list(self.interface_notes)
        if response.model_version is None:
            response.model_version = self._model_version or self.spec.model_id
        if response.pages_billed is None:
            response.pages_billed = document.page_count
        return response

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    # -- to implement ---------------------------------------------------- #
    def _call(self, document: Document, rendered_prompt: str) -> Any:
        raise NotImplementedError

    def _parse_response(self, payload: Any, document: Document) -> Response:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Shared parsing of a model's JSON answer                                      #
# --------------------------------------------------------------------------- #

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def parse_model_json(text: str) -> tuple[dict | None, str | None]:
    """Pull the JSON object out of a model's reply.

    Returns `(object, error)`. A reply that cannot be parsed after these steps
    is a processing failure for that document, recorded under `FAIL`. It is
    never repaired by a per-model fixer: charter section 5.3 forbids
    post-processing that only one system receives, so every system gets exactly
    these three steps and no more.
    """
    if text is None:
        return None, "empty response"
    stripped = text.strip()
    if not stripped:
        return None, "empty response"

    for candidate in _json_candidates(stripped):
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj, None
    return None, "response is not valid JSON"


def _json_candidates(text: str):
    yield text
    for match in _FENCE_RE.findall(text):
        yield match.strip()
    start = text.find("{")
    if start >= 0:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    yield text[start:i + 1]
                    return


def split_answer(obj: dict) -> tuple[dict, dict, bool]:
    """Split a parsed answer into fields and confidences.

    Accepts the shape the published prompt asks for, and the two shapes a model
    reaches for when it does not follow it exactly: a bare field object, and
    fields nested under `extraction` or `data`. Applied identically to every
    system.
    """
    fields = obj.get("fields")
    if not isinstance(fields, dict):
        for alt in ("extraction", "data", "result"):
            if isinstance(obj.get(alt), dict):
                fields = obj[alt]
                break
    if not isinstance(fields, dict):
        reserved = {"confidence", "confidences", "document_type", "doc_type", "notes"}
        fields = {k: v for k, v in obj.items() if k not in reserved}

    conf_raw = obj.get("confidence")
    if not isinstance(conf_raw, dict):
        conf_raw = obj.get("confidences") if isinstance(obj.get("confidences"), dict) else {}
    confidence: dict[str, float] = {}
    for key, value in (conf_raw or {}).items():
        parsed = _as_float(value)
        if parsed is not None:
            confidence[key] = parsed
    return fields, confidence, bool(confidence)


def _as_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:                                       # NaN
        return None
    if f > 1.0 and f <= 100.0:
        f = f / 100.0                                # a percentage
    return min(max(f, 0.0), 1.0)


def response_from_text(
    text: str,
    document: Document,
    *,
    tokens: TokenCounts | None = None,
    model_version: str | None = None,
    pages_billed: int | None = None,
    provider_meta: dict | None = None,
) -> Response:
    """Build a Response from a system's text reply. Shared by every adapter."""
    obj, error = parse_model_json(text)
    if obj is None:
        return Response(
            doc_id=document.doc_id,
            ok=False,
            raw_text=text or "",
            tokens=tokens or TokenCounts(),
            model_version=model_version,
            pages_billed=pages_billed,
            error=error,
            error_kind="parse_error",
            provider_meta=provider_meta or {},
        )
    fields, confidence, reported = split_answer(obj)
    return Response(
        doc_id=document.doc_id,
        ok=True,
        fields=fields,
        confidence=confidence,
        raw_text=text,
        tokens=tokens or TokenCounts(),
        model_version=model_version,
        pages_billed=pages_billed,
        confidence_reported=reported,
        provider_meta=provider_meta or {},
    )


def image_media_type(path) -> str:
    suffix = str(path).lower().rsplit(".", 1)[-1]
    return {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "webp": "image/webp", "gif": "image/gif", "tif": "image/tiff",
        "tiff": "image/tiff", "pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")


def document_images(document: Document, max_pages: int | None = None) -> list:
    """The page images a vision model is shown, in page order."""
    pages = [p for p in document.page_paths if p.exists()]
    if max_pages:
        pages = pages[:max_pages]
    return pages


def encode_b64(path) -> str:
    import base64

    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


CallableTransport = Callable[[str, dict, dict], Any]
