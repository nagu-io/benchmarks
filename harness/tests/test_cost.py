"""Cost arithmetic and the spend control, charter section 3.7."""

from __future__ import annotations

from decimal import Decimal

import pytest

from entail_bench.cost import (
    SpendTracker,
    cost_report,
    document_cost,
    load_prices,
)
from entail_bench.errors import SpendCapReached


@pytest.fixture
def prices(fixtures_dir):
    return load_prices(fixtures_dir / "prices-test.yaml")


@pytest.fixture
def shipped_prices(harness_root):
    return load_prices(harness_root / "prices.yaml")


# --------------------------------------------------------------------------- #
# The shipped price list carries no invented figure                            #
# --------------------------------------------------------------------------- #


def test_the_shipped_price_list_holds_no_figure_and_no_date(shipped_prices):
    assert shipped_prices.price_list_date is None
    for key, entry in shipped_prices.providers.items():
        assert entry.get("verified") is False, key
        for field in ("input", "output", "reasoning", "per_page", "per_document",
                      "hourly_rate"):
            assert entry.get(field) is None, f"{key}.{field} carries a figure"


def test_an_unverified_price_produces_no_cost_figure(shipped_prices):
    cost, reason = document_cost(
        shipped_prices, "openai", tokens={"input": 1000, "output": 200}, pages_billed=1
    )
    assert cost is None
    assert "not marked verified" in reason


def test_a_missing_price_key_produces_no_cost_figure(prices):
    cost, reason = document_cost(prices, "a_provider_that_is_not_listed",
                                 tokens={"input": 1000})
    assert cost is None
    assert "no entry" in reason


def test_no_price_key_at_all_is_reported(prices):
    cost, reason = document_cost(prices, None, tokens={"input": 1000})
    assert cost is None
    assert "no price key" in reason


# --------------------------------------------------------------------------- #
# The arithmetic, on the synthetic test price list                             #
# --------------------------------------------------------------------------- #


def test_token_billing(prices):
    cost, reason = document_cost(
        prices, "test_tokens",
        tokens={"input": 3_000_000, "output": 400_000, "reasoning": 100_000},
    )
    assert reason is None
    # 3.0 * 1.0 + 0.4 * 10.0 + 0.1 * 20.0
    assert cost == Decimal("9.0")


def test_token_billing_with_a_missing_rate_is_not_priced(prices):
    cost, reason = document_cost(
        prices, "test_tokens_no_output_rate",
        tokens={"input": 1_000_000, "output": 100_000},
    )
    assert cost is None
    assert "no output rate" in reason


def test_page_billing(prices):
    cost, reason = document_cost(prices, "test_pages", pages_billed=6)
    assert reason is None
    assert cost == Decimal("0.06")


def test_document_billing(prices):
    cost, reason = document_cost(prices, "test_documents")
    assert cost == Decimal("0.25")


def test_self_hosted_compute_uses_the_measured_occupancy(prices):
    # 3.6 per hour, 10 seconds of occupancy -> 0.01
    cost, reason = document_cost(prices, "test_compute", elapsed_s=10.0)
    assert reason is None
    assert cost == Decimal("0.01")


def test_self_hosted_compute_without_a_measured_time_is_not_priced(prices):
    cost, reason = document_cost(prices, "test_compute", elapsed_s=None)
    assert cost is None
    assert "occupancy" in reason


# --------------------------------------------------------------------------- #
# Cost per document                                                            #
# --------------------------------------------------------------------------- #


def test_cost_per_document_and_its_denominator(prices):
    per_document = [Decimal("0.10")] * 50
    report = cost_report(
        prices, "test_documents",
        per_document=per_document, unpriced_reasons=[],
        documents_admitted=50, pages_total=100,
    )
    assert report["status"] == "priced"
    assert Decimal(report["total_run_cost"]) == Decimal("5.00")
    assert Decimal(report["cost_per_document"]) == Decimal("0.1")
    assert Decimal(report["cost_per_page"]) == Decimal("0.05")
    assert Decimal(report["cost_per_thousand_documents"]) == Decimal("100.0")
    assert report["documents_admitted"] == 50


def test_one_unpriced_document_makes_the_whole_figure_not_priced(prices):
    report = cost_report(
        prices, "test_documents",
        per_document=[Decimal("0.10")] * 49 + [None],
        unpriced_reasons=["a synthetic reason"],
        documents_admitted=50, pages_total=100,
    )
    assert report["status"] == "not priced"
    assert report["cost_per_document"] is None
    assert report["not_priced_reason"] == "a synthetic reason"
    assert report["documents_not_priced"] == 1


def test_the_price_list_date_and_source_travel_with_the_figure(prices):
    report = cost_report(prices, "test_documents", per_document=[Decimal("0.25")],
                         unpriced_reasons=[], documents_admitted=1, pages_total=1)
    provenance = report["price_list"]
    assert provenance["price_list_date"] == "2026-01-01"
    assert provenance["verified"] is True
    assert "list price" in provenance["basis"]
    assert "review labour" in report["excluded"]


# --------------------------------------------------------------------------- #
# Spend control                                                                #
# --------------------------------------------------------------------------- #


def test_no_cap_never_stops_a_run():
    tracker = SpendTracker(cap=None, documents_total=10)
    for index in range(10):
        tracker.record(f"doc-{index}", Decimal("1000"), None)
        tracker.check()
    assert tracker.stopped is False


def test_the_run_stops_when_the_projected_cost_would_exceed_the_cap():
    tracker = SpendTracker(cap=Decimal("1.00"), documents_total=100)
    with pytest.raises(SpendCapReached) as raised:
        for index in range(100):
            tracker.record(f"doc-{index}", Decimal("0.05"), None)
            tracker.check()
    assert tracker.stopped is True
    assert "projected cost" in str(raised.value)
    # 0.05 a document over 100 documents projects to 5.00, so it stops early.
    assert tracker.documents_done < 100


def test_the_projection_states_its_basis():
    tracker = SpendTracker(cap=Decimal("100"), documents_total=10)
    tracker.record("doc-0", Decimal("1.00"), None)
    projected, basis = tracker.projected_total()
    assert projected == Decimal("10.00")
    assert "mean cost over" in basis
    state = tracker.as_dict()
    assert "not a result" in state["projection_note"]


def test_a_run_with_no_priced_document_makes_no_projection():
    tracker = SpendTracker(cap=Decimal("100"), documents_total=10)
    tracker.record("doc-0", None, "not priced")
    projected, basis = tracker.projected_total()
    assert projected is None
    assert "no priced document" in basis
    tracker.check()          # a cap cannot fire on a projection that cannot be made
    assert tracker.stopped is False


def test_running_totals_are_recorded_per_document():
    tracker = SpendTracker(cap=None, documents_total=3)
    tracker.record("a", Decimal("0.10"), None)
    tracker.record("b", Decimal("0.20"), None)
    tracker.record("c", None, "not priced")
    assert [e["running_total"] for e in tracker.events] == ["0.10", "0.30", "0.30"]
    assert tracker.unpriced_documents == 1
    assert tracker.as_dict()["documents_done"] == 3
