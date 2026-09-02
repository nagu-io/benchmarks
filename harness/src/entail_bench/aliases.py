"""Shared key normalisation, applied identically to every system's output.

Charter section 5.3. This is the whole of the per-system post-processing the
harness does, and every system receives it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DATA = Path(__file__).parent / "data" / "field-aliases.yaml"
_STRIP = re.compile(r"[\s_\-./]+")


def canonical_key(key: str) -> str:
    return _STRIP.sub("", str(key)).casefold()


@dataclass
class AliasTable:
    version: str
    aliases: dict[str, str]
    source_path: Path
    source_sha256: str

    def resolve(self, key: str) -> str | None:
        return self.aliases.get(canonical_key(key))


@lru_cache(maxsize=1)
def load_aliases(path: str | None = None) -> AliasTable:
    from .util import sha256_file

    p = Path(path) if path else _DATA
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    table = {canonical_key(k): v for k, v in (raw.get("aliases") or {}).items()}
    return AliasTable(
        version=str(raw.get("version", "0")),
        aliases=table,
        source_path=p,
        source_sha256=sha256_file(p),
    )


def apply_aliases(
    returned: dict[str, Any], schema: dict[str, str]
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Map returned keys onto schema field names.

    Returns `(mapped, moved, out_of_schema)`:

    * a key that is already a schema field is kept as it is;
    * a key that differs only in case, spacing or punctuation from a schema
      field is moved onto that field;
    * a key that the published alias table resolves to an unfilled schema field
      is moved onto that field;
    * anything else stays under its own name and is reported as an out-of-schema
      return, excluded from field accuracy under charter section 3.3.4 and
      counted.
    """
    table = load_aliases()
    schema_by_canonical = {canonical_key(k): k for k in schema}
    mapped: dict[str, Any] = {}
    moved: list[str] = []
    out_of_schema: list[str] = []

    for key, value in returned.items():
        if key in schema:
            mapped[key] = value
            continue
        target = schema_by_canonical.get(canonical_key(key))
        if target and target not in mapped:
            mapped[target] = value
            moved.append(f"{key} -> {target}")
            continue
        alias = table.resolve(key)
        if alias and alias in schema and alias not in mapped:
            mapped[alias] = value
            moved.append(f"{key} -> {alias}")
            continue
        mapped[key] = value
        out_of_schema.append(key)

    return mapped, moved, out_of_schema


def apply_row_aliases(row: dict[str, Any], cells: list[str]) -> dict[str, Any]:
    """The same mapping inside one line-item row."""
    table = load_aliases()
    by_canonical = {canonical_key(c): c for c in cells}
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key in cells:
            out[key] = value
            continue
        target = by_canonical.get(canonical_key(key))
        if target and target not in out:
            out[target] = value
            continue
        alias = table.resolve(key)
        if alias and alias in cells and alias not in out:
            out[alias] = value
            continue
        out[key] = value
    return out
