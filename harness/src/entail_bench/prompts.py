"""Prompt loading and rendering.

The prompt file is the published artefact. Its SHA-256 is taken over the file as
it sits on disk, before any placeholder is filled, so the hash in a report
identifies the prompt a reader can open.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .dataset import Document
from .errors import ConfigError
from .util import sha256_text


@dataclass(frozen=True)
class Prompt:
    name: str
    path: Path
    text: str
    sha256: str

    def render(self, document: Document) -> str:
        return (
            self.text.replace("{{DOCUMENT_TYPE}}", document.doc_type)
            .replace("{{DOCUMENT_SUBTYPE}}", document.doc_subtype)
            .replace("{{PAGE_COUNT}}", str(document.page_count))
            .replace("{{FIELD_SCHEMA}}", render_schema(document))
        )


def render_schema(document: Document) -> str:
    """The field schema, rendered identically for every model."""
    lines = ["```json", json.dumps(_schema_block(document), indent=2, sort_keys=True), "```"]
    return "\n".join(lines)


def _schema_block(document: Document) -> dict:
    block: dict[str, object] = {}
    for name, type_ in sorted(document.schema.items()):
        if type_ == "line_items":
            cells = _line_cells(document, name)
            block[name] = [{c: "string" for c in cells}]
        else:
            block[name] = type_
    return block


def _line_cells(document: Document, list_name: str) -> list[str]:
    from .fieldrules import load_field_rules

    rules = load_field_rules()
    rows = document.fields.get(list_name)
    keys: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                for k in row:
                    if k not in keys:
                        keys.append(k)
    out = []
    for k in keys:
        scored, _ = rules.line_cell_scored(k, document.doc_subtype)
        if scored:
            out.append(k)
    return out or ["description", "quantity", "unit_price", "amount"]


def prompt_dir(explicit: str | Path | None = None) -> Path:
    """Where prompts live: an explicit path, else `prompts/` beside the package."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in (here.parents[2], here.parents[3] if len(here.parents) > 3 else here.parents[2]):
        candidate = parent / "prompts"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "prompts"


def load_prompt(name_or_path: str | Path, *, directory: str | Path | None = None) -> Prompt:
    p = Path(name_or_path)
    if not p.is_absolute():
        base = prompt_dir(directory)
        candidate = base / p
        if not candidate.exists() and not str(p).endswith(".md"):
            candidate = base / f"{p}.md"
        p = candidate
    if not p.exists():
        raise ConfigError(
            f"prompt file not found: {p}. Prompts live in harness/prompts/ and are "
            "named <suite>-v<version>.md"
        )
    text = p.read_text(encoding="utf-8")
    return Prompt(name=p.name, path=p, text=text, sha256=sha256_text(text))


def default_prompt_name(suite: str) -> str:
    return {"messy-scan": "messy-scan-v1.0.0.md"}.get(suite, f"{suite}-v1.0.0.md")
