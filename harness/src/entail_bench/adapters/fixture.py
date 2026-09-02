"""The dry-run fixture adapter.

`entail-bench run --dry-run` uses this to exercise the whole path with no
network and no key. What it returns is synthetic and is stamped as such in every
file the run writes. It is never a fallback: an adapter whose key is missing
reports itself unavailable and the model is recorded `not run`. The only way to
reach this adapter is to ask for it by name on the command line.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..dataset import Document
from .base import Adapter, Availability, Response, TokenCounts

_FIXTURE = Path(__file__).parents[1] / "data" / "dry-run-fixture.yaml"

FIXTURE_MODEL_NAME = "dry-run-fixture"
FIXTURE_WARNING = (
    "Synthetic dry-run fixture. Not a model, not a measurement, not a result."
)


@lru_cache(maxsize=1)
def load_fixture(path: str | None = None) -> dict:
    p = Path(path) if path else _FIXTURE
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["_path"] = str(p)
    return data


class DryRunFixtureAdapter(Adapter):
    adapter_name = "dry-run-fixture"
    provider = "none (recorded fixture)"
    required_env = ()
    synthetic = True
    interface_notes = (
        "No provider is called. Output comes from the recorded fixture at "
        "src/entail_bench/data/dry-run-fixture.yaml.",
        "Every file this run writes is stamped synthetic: true and is refused by "
        "the leaderboard builder.",
    )

    def __init__(self, spec, options=None, transport=None):
        super().__init__(spec, options, transport)
        self.fixture = load_fixture(self.options.get("fixture_path"))
        self._positions: dict[str, int] = {}

    def availability(self) -> Availability:
        return Availability(True, "recorded fixture, no key needed", env_var=None)

    def begin_run(self, run_index: int) -> None:
        # The three runs are at identical settings, and a retry must replay the
        # same recorded event, so the position is fixed per document per run.
        self._positions = {}

    # ------------------------------------------------------------------ #
    def _call(self, document: Document, rendered_prompt: str) -> Any:
        index = self._positions.setdefault(document.doc_id, len(self._positions))
        event = self._event_for(index)
        if event and event["kind"] == "call_error":
            from ..errors import AdapterCallError

            raise AdapterCallError(event["error"])
        return {"index": index, "event": event, "prompt_chars": len(rendered_prompt)}

    def _event_for(self, index: int) -> dict | None:
        for event in self.fixture.get("recorded_events") or []:
            if event.get("at_index") == index:
                return event
        return None

    # ------------------------------------------------------------------ #
    def _parse_response(self, payload: Any, document: Document) -> Response:
        index = payload["index"]
        event = payload["event"]
        pattern = self.fixture["pattern"]
        conf_spec = self.fixture["confidence"]
        lat = self.fixture["latency"]
        tok = self.fixture["tokens"]

        if event and event["kind"] == "parse_error":
            return Response(
                doc_id=document.doc_id, ok=False,
                raw_text=event["raw_text"],
                tokens=TokenCounts(
                    input=tok["input_per_page"] * document.page_count,
                    output=tok["output_base"],
                ),
                model_version=FIXTURE_MODEL_NAME,
                pages_billed=document.page_count,
                error="response is not valid JSON",
                error_kind="parse_error",
                provider_meta={"synthetic": True, "fixture_event": event["kind"]},
            )

        fields, confidence, instances = self._build_answer(document, pattern, conf_spec)
        if event and event["kind"] == "extra_field":
            fields[pattern["extra_field_name"]] = pattern["extra_field_value"]
        report_confidence = not (event and event["kind"] == "no_confidence")
        if not report_confidence:
            confidence = {}

        raw = json.dumps(
            {"fields": fields, "confidence": confidence,
             "document_type": document.doc_subtype},
            ensure_ascii=False, sort_keys=True,
        )
        return Response(
            doc_id=document.doc_id,
            ok=True,
            fields=fields,
            confidence=confidence,
            raw_text=raw,
            tokens=TokenCounts(
                input=tok["input_per_page"] * document.page_count,
                output=tok["output_base"] + tok["output_per_field"] * instances,
            ),
            model_version=FIXTURE_MODEL_NAME,
            pages_billed=document.page_count,
            confidence_reported=report_confidence,
            provider_meta={
                "synthetic": True,
                "warning": FIXTURE_WARNING,
                "fixture_index": index,
                "fixture_event": event["kind"] if event else None,
            },
        )

    # ------------------------------------------------------------------ #
    def _build_answer(self, document: Document, pattern: dict, conf_spec: dict):
        """Return ground-truth values spoiled on a fixed arithmetic cycle."""
        fields: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        position = 0

        def conf_for(pos: int) -> float:
            value = conf_spec["base"] + conf_spec["step"] * (pos % 11)
            return round(min(value, conf_spec["ceiling"]), 3)

        def spoil(pos: int) -> str:
            if pos % pattern["wrong_every_nth"] == pattern["wrong_offset"]:
                return "wrong"
            if pos % pattern["drop_every_nth"] == pattern["drop_offset"]:
                return "drop"
            return "keep"

        for name, type_ in sorted(document.schema.items()):
            value = document.fields.get(name)
            if type_ == "line_items" and isinstance(value, list):
                rows = []
                for row_index, row in enumerate(value):
                    out_row = {}
                    for cell, cell_value in row.items():
                        action = spoil(position)
                        key = f"{name}[{row_index}].{cell}"
                        if action == "keep":
                            out_row[cell] = cell_value
                            confidence[key] = conf_for(position)
                        elif action == "wrong":
                            out_row[cell] = pattern["wrong_value_marker"]
                            confidence[key] = conf_for(position)
                        position += 1
                    rows.append(out_row)
                fields[name] = rows
                confidence[name] = conf_for(position)
                continue

            action = spoil(position)
            if action == "keep":
                fields[name] = value
                confidence[name] = conf_for(position)
            elif action == "wrong":
                fields[name] = pattern["wrong_value_marker"]
                confidence[name] = conf_for(position)
            position += 1

        return fields, confidence, position

    def _sleep(self, seconds: float) -> None:   # no waiting in a dry run
        return
