"""Dataset loading.

A dataset folder is anything holding a `ground-truth.jsonl` and a `documents/`
tree, which is what `datasets/messy-scan/` and each of its split folders is, and
what `--dataset ./their-folder` points at. The record shape is the one the Messy
Scan datasheet publishes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .errors import DatasetError
from .util import sha256_file

REQUIRED_KEYS = ("doc_id", "fields", "schema")


@dataclass
class Document:
    doc_id: str
    doc_type: str
    doc_subtype: str
    tier: int | None
    languages: list[str]
    page_count: int
    split: str | None
    schema: dict[str, str]
    fields: dict[str, Any]
    display_formats: dict[str, str]
    root: Path
    page_paths: list[Path] = field(default_factory=list)
    pdf_path: Path | None = None
    raw: dict = field(default_factory=dict)

    @property
    def language_key(self) -> str:
        return "+".join(self.languages) if self.languages else "unstated"

    @property
    def currency(self) -> str | None:
        value = self.fields.get("currency")
        return value if isinstance(value, str) and value else None

    @property
    def rendered(self) -> bool:
        return bool(self.page_paths) or self.pdf_path is not None


@dataclass
class Dataset:
    name: str
    version: str
    root: Path
    ground_truth_path: Path
    ground_truth_sha256: str
    documents: list[Document]
    schema_version: str | None = None
    split: str | None = None
    unrendered: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.documents)

    def __iter__(self) -> Iterator[Document]:
        return iter(self.documents)

    def by_id(self, doc_id: str) -> Document:
        for d in self.documents:
            if d.doc_id == doc_id:
                return d
        raise DatasetError(f"no document {doc_id!r} in {self.root}")

    def summary(self) -> dict:
        tiers: dict[str, int] = {}
        langs: dict[str, int] = {}
        subtypes: dict[str, int] = {}
        for d in self.documents:
            tiers[str(d.tier)] = tiers.get(str(d.tier), 0) + 1
            langs[d.language_key] = langs.get(d.language_key, 0) + 1
            subtypes[d.doc_subtype] = subtypes.get(d.doc_subtype, 0) + 1
        return {
            "dataset": self.name,
            "dataset_version": self.version,
            "schema_version": self.schema_version,
            "documents": len(self.documents),
            "ground_truth_sha256": self.ground_truth_sha256,
            "tier_mix": dict(sorted(tiers.items())),
            "language_mix": dict(sorted(langs.items())),
            "subtype_mix": dict(sorted(subtypes.items())),
            "unrendered_documents": len(self.unrendered),
        }


def resolve_dataset_dir(path: str | Path, split: str | None = None) -> Path:
    """Accept a dataset root or a split folder, and find the ground truth."""
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise DatasetError(f"dataset folder not found: {root}")
    if (root / "ground-truth.jsonl").exists() and split in (None, "", "all"):
        return root
    if split:
        candidates = {
            "public_sample": root / "sample",
            "sample": root / "sample",
            "private_holdout": root / "private",
            "private": root / "private",
        }
        candidate = candidates.get(split)
        if candidate and (candidate / "ground-truth.jsonl").exists():
            return candidate
        if (root / "ground-truth.jsonl").exists():
            return root
        raise DatasetError(
            f"split {split!r} not found under {root}. Looked for "
            f"{candidate}/ground-truth.jsonl and {root}/ground-truth.jsonl"
        )
    raise DatasetError(f"no ground-truth.jsonl in {root}")


def load_dataset(
    path: str | Path,
    *,
    split: str | None = None,
    limit: int | None = None,
    require_rendered: bool = True,
) -> Dataset:
    root = resolve_dataset_dir(path, split)
    gt = root / "ground-truth.jsonl"
    if not gt.exists():
        raise DatasetError(f"no ground-truth.jsonl in {root}")

    documents: list[Document] = []
    unrendered: list[str] = []
    name = "unknown"
    version = "unknown"
    schema_version = None
    split_seen: set[str] = set()

    with open(gt, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"{gt}:{lineno} is not valid JSON: {exc}") from exc
            missing = [k for k in REQUIRED_KEYS if k not in rec]
            if missing:
                raise DatasetError(
                    f"{gt}:{lineno} is missing required key(s) {missing}. "
                    "A dataset record needs at least doc_id, fields and schema."
                )
            name = rec.get("dataset", name)
            version = rec.get("dataset_version", version)
            schema_version = rec.get("schema_version", schema_version)
            if rec.get("split"):
                split_seen.add(rec["split"])

            render = rec.get("render") or {}
            pages = [root / p["path"] for p in render.get("pages", []) if p.get("path")]
            pdf = (render.get("pdf") or {}).get("path")
            pdf_path = root / pdf if pdf else None
            doc = Document(
                doc_id=rec["doc_id"],
                doc_type=rec.get("doc_type", "unknown"),
                doc_subtype=rec.get("doc_subtype", rec.get("doc_type", "unknown")),
                tier=rec.get("tier"),
                languages=list(rec.get("languages") or []),
                page_count=int(rec.get("page_count") or len(pages) or 1),
                split=rec.get("split"),
                schema=dict(rec["schema"]),
                fields=dict(rec["fields"]),
                display_formats=dict(rec.get("display_formats") or {}),
                root=root,
                page_paths=pages,
                pdf_path=pdf_path,
                raw=rec,
            )
            if not doc.rendered or not all(p.exists() for p in doc.page_paths):
                unrendered.append(doc.doc_id)
            documents.append(doc)
            if limit and len(documents) >= limit:
                break

    if not documents:
        raise DatasetError(f"{gt} holds no records")
    if require_rendered and len(unrendered) == len(documents):
        raise DatasetError(
            f"no rendered pages found under {root}. Build the dataset first: "
            "see datasets/messy-scan/README.md"
        )

    return Dataset(
        name=name,
        version=str(version),
        root=root,
        ground_truth_path=gt,
        ground_truth_sha256=sha256_file(gt),
        documents=documents,
        schema_version=schema_version,
        split=sorted(split_seen)[0] if len(split_seen) == 1 else None,
        unrendered=unrendered,
    )
