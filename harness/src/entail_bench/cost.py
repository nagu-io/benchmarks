"""Cost per document and the spend control, charter section 3.7.

Cost per document = total run cost / documents admitted to processing.

The numerator holds every charge incurred to process the documents in the run:
input, output and separately billed reasoning tokens; per-page and per-request
charges for document services; the charges for retries and for calls that failed
and were repeated; and, for a self-hosted model, the compute rate multiplied by
the measured occupancy.

Prices come from `prices.yaml` and nowhere else. A row that is not marked
verified produces no figure: cost is reported `not priced`, with the reason. The
harness never invents a price and never fills one in from memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError, SpendCapReached


@dataclass
class PriceList:
    path: Path
    currency: str
    price_list_date: str | None
    providers: dict
    raw: dict

    def entry(self, key: str | None) -> dict | None:
        if not key:
            return None
        return self.providers.get(key)

    def is_verified(self, key: str | None) -> bool:
        entry = self.entry(key)
        return bool(entry and entry.get("verified") is True)

    def unverified_reason(self, key: str | None) -> str:
        if not key:
            return "no price key is registered for this model in models.yaml"
        entry = self.entry(key)
        if entry is None:
            return f"prices.yaml has no entry for {key!r}"
        if self.price_list_date is None:
            return (
                f"prices.yaml entry {key!r} is not marked verified and "
                "price_list_date is not set"
            )
        return f"prices.yaml entry {key!r} is not marked verified"

    def provenance(self, key: str | None) -> dict:
        entry = self.entry(key) or {}
        return {
            "price_key": key,
            "price_list_date": self.price_list_date,
            "currency": self.currency,
            "billing": entry.get("billing"),
            "source_url": entry.get("source_url"),
            "verified_on": entry.get("verified_on"),
            "verified": bool(entry.get("verified")),
            "basis": "published list price on the stated date, to verify. No "
                     "negotiated discount, committed-use rate or caching effect.",
        }


def load_prices(path: str | Path) -> PriceList:
    p = Path(path).expanduser()
    if not p.exists():
        raise ConfigError(f"price list not found: {p}")
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return PriceList(
        path=p,
        currency=str(raw.get("currency", "USD")),
        price_list_date=raw.get("price_list_date"),
        providers=raw.get("providers") or {},
        raw=raw,
    )


# --------------------------------------------------------------------------- #
# Per-document cost                                                            #
# --------------------------------------------------------------------------- #


def document_cost(
    prices: PriceList,
    price_key: str | None,
    *,
    tokens: dict | None = None,
    pages_billed: int | None = None,
    requests: int = 1,
    elapsed_s: float | None = None,
) -> tuple[Decimal | None, str | None]:
    """The charge for one document, or `(None, reason)` when it is not priced."""
    if not prices.is_verified(price_key):
        return None, prices.unverified_reason(price_key)
    entry = prices.entry(price_key) or {}
    billing = entry.get("billing")

    if billing == "per_million_tokens":
        total = Decimal(0)
        for name, count in (
            ("input", (tokens or {}).get("input")),
            ("output", (tokens or {}).get("output")),
            ("reasoning", (tokens or {}).get("reasoning")),
        ):
            rate = entry.get(name)
            if count is None or rate is None:
                if count and rate is None:
                    return None, (
                        f"{count} {name} tokens were used but prices.yaml has no "
                        f"{name} rate for {price_key!r}"
                    )
                continue
            total += Decimal(str(count)) / Decimal(1_000_000) * Decimal(str(rate))
        return total, None

    if billing == "per_page":
        rate = entry.get("per_page")
        if rate is None:
            return None, f"prices.yaml has no per_page rate for {price_key!r}"
        pages = pages_billed or 0
        return Decimal(str(pages)) * Decimal(str(rate)), None

    if billing == "per_document":
        rate = entry.get("per_document")
        if rate is None:
            return None, f"prices.yaml has no per_document rate for {price_key!r}"
        return Decimal(str(rate)), None

    if billing == "per_instance_hour":
        rate = entry.get("hourly_rate")
        if rate is None:
            return None, f"prices.yaml has no hourly_rate for {price_key!r}"
        if elapsed_s is None:
            return None, "no measured occupancy for this document"
        concurrency = Decimal(str(entry.get("concurrency") or 1))
        occupancy_hours = Decimal(str(elapsed_s)) / Decimal(3600)
        return (occupancy_hours * Decimal(str(rate)) / concurrency), None

    return None, f"prices.yaml gives an unknown billing basis {billing!r} for {price_key!r}"


def cost_report(
    prices: PriceList,
    price_key: str | None,
    *,
    per_document: list[Decimal | None],
    unpriced_reasons: list[str],
    documents_admitted: int,
    pages_total: int | None,
) -> dict:
    priced = [c for c in per_document if c is not None]
    unpriced = len(per_document) - len(priced)
    total = sum(priced, Decimal(0)) if priced else None
    reason = None
    if unpriced:
        reason = unpriced_reasons[0] if unpriced_reasons else "not priced"

    block = {
        "definition":
            "Total run cost divided by documents admitted to processing "
            "(charter 3.7)",
        "currency": prices.currency,
        "documents_admitted": documents_admitted,
        "documents_priced": len(priced),
        "documents_not_priced": unpriced,
        "not_priced_reason": reason,
        "total_run_cost": str(total) if total is not None else None,
        "cost_per_document": None,
        "cost_per_page": None,
        "cost_per_thousand_documents": None,
        "status": "not priced" if unpriced or total is None else "priced",
        "price_list": prices.provenance(price_key),
        "excluded":
            "Human review labour, one-off build and integration cost, the cost "
            "of running the harness, negotiated discounts and committed-use "
            "pricing (charter 3.7.4)",
    }
    if total is not None and unpriced == 0 and documents_admitted:
        per_doc = total / Decimal(documents_admitted)
        block["cost_per_document"] = str(per_doc)
        block["cost_per_thousand_documents"] = str(per_doc * Decimal(1000))
        if pages_total:
            block["cost_per_page"] = str(total / Decimal(pages_total))
    return block


# --------------------------------------------------------------------------- #
# Spend control                                                                #
# --------------------------------------------------------------------------- #


@dataclass
class SpendTracker:
    """Running totals, and the cap that stops a run.

    The projection is a control figure with a stated basis, not a result. It is
    written to `spend.json` in the run folder and is never carried into a
    results table.
    """

    cap: Decimal | None
    currency: str = "USD"
    spent: Decimal = Decimal(0)
    documents_done: int = 0
    documents_total: int = 0
    unpriced_documents: int = 0
    events: list[dict] = field(default_factory=list)
    stopped: bool = False
    stop_reason: str | None = None

    def record(self, doc_id: str, cost: Decimal | None, reason: str | None) -> None:
        self.documents_done += 1
        if cost is None:
            self.unpriced_documents += 1
        else:
            self.spent += cost
        self.events.append({
            "doc_id": doc_id,
            "cost": str(cost) if cost is not None else None,
            "not_priced_reason": reason,
            "running_total": str(self.spent),
            "documents_done": self.documents_done,
        })

    @property
    def mean_cost(self) -> Decimal | None:
        priced = self.documents_done - self.unpriced_documents
        if priced <= 0:
            return None
        return self.spent / Decimal(priced)

    def projected_total(self) -> tuple[Decimal | None, str]:
        mean = self.mean_cost
        if mean is None:
            return None, "no priced document yet, so no projection can be made"
        remaining = max(self.documents_total - self.documents_done, 0)
        projected = self.spent + mean * Decimal(remaining)
        return projected, (
            f"running total plus the mean cost over the "
            f"{self.documents_done - self.unpriced_documents} priced documents so "
            f"far, applied to the {remaining} documents not yet processed"
        )

    def check(self) -> None:
        """Stop the run if the projected cost would exceed the cap."""
        if self.cap is None:
            return
        if self.spent > self.cap:
            self.stopped = True
            self.stop_reason = (
                f"spend cap reached: {self.spent} spent against a cap of "
                f"{self.cap} {self.currency}"
            )
            raise SpendCapReached(self.stop_reason)
        projected, basis = self.projected_total()
        if projected is not None and projected > self.cap:
            self.stopped = True
            self.stop_reason = (
                f"projected cost {projected} {self.currency} would exceed the cap "
                f"of {self.cap} {self.currency}. Basis: {basis}. "
                f"Spent so far {self.spent} over {self.documents_done} documents."
            )
            raise SpendCapReached(self.stop_reason)

    def as_dict(self) -> dict:
        projected, basis = self.projected_total()
        return {
            "currency": self.currency,
            "spend_cap": str(self.cap) if self.cap is not None else None,
            "spent": str(self.spent),
            "documents_done": self.documents_done,
            "documents_total": self.documents_total,
            "documents_not_priced": self.unpriced_documents,
            "projected_total_cost": str(projected) if projected is not None else None,
            "projected_total_cost_basis": basis,
            "projection_note":
                "A control figure for the spend cap, not a result, and never "
                "carried into a results table",
            "stopped": self.stopped,
            "stop_reason": self.stop_reason,
        }
