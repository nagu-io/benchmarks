"""Scorer unit tests, charter sections 3.3, 3.4, 3.5 and 3.1.2."""

from __future__ import annotations

import pytest

from entail_bench.adapters.base import Response, TokenCounts, response_from_text
from entail_bench.errors import ReconciliationError
from entail_bench.scoring import (
    Admission,
    ScoringSettings,
    audit_draw,
    score_document,
    score_run,
)


def perfect_answer(document) -> dict:
    """Every ground-truth value returned, with a high confidence for each."""
    fields = dict(document.fields)
    confidence = {name: 0.99 for name in document.schema}
    for name, type_ in document.schema.items():
        if type_ == "line_items":
            for index, row in enumerate(document.fields.get(name) or []):
                for cell in row:
                    confidence[f"{name}[{index}].{cell}"] = 0.99
    return {"fields": fields, "confidence": confidence}


def make_response(document, answer: dict, **kwargs) -> Response:
    base = dict(
        doc_id=document.doc_id,
        ok=True,
        fields=answer.get("fields", {}),
        confidence=answer.get("confidence", {}),
        raw_text="",
        tokens=TokenCounts(1000, 200, None),
        latency_s=1.5,
        model_version="synthetic-test-model",
        pages_billed=document.page_count,
        confidence_reported=bool(answer.get("confidence")),
    )
    base.update(kwargs)
    return Response(**base)


# --------------------------------------------------------------------------- #
# Field-level accuracy                                                         #
# --------------------------------------------------------------------------- #


def test_a_perfect_answer_scores_one(tiny_invoice, settings):
    score = score_document(tiny_invoice, make_response(tiny_invoice,
                                                       perfect_answer(tiny_invoice)), settings)
    assert score.assessed == score.correct
    assert score.outcome == "straight_through"
    assert score.queue_codes == []


def test_a_missing_field_is_counted_in_the_denominator(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    baseline = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    answer["fields"].pop("vendor_ein")
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)

    assert score.assessed == baseline.assessed, "the denominator does not shrink"
    assert score.correct == baseline.correct - 1
    missing = [i for i in score.instances if i.path == "vendor_ein"]
    assert missing[0].correct is False
    assert missing[0].reason == "missing"


def test_an_extra_field_outside_the_schema_is_excluded_and_counted(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    baseline = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    answer["fields"]["a_field_that_is_not_in_the_schema"] = "invented"
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)

    assert score.assessed == baseline.assessed
    assert score.out_of_schema_keys == ["a_field_that_is_not_in_the_schema"]


def test_an_extra_line_item_row_is_assessed_and_always_incorrect(tiny_invoice, settings):
    """Charter 3.3.3: a returned instance with no counterpart is always wrong."""
    answer = perfect_answer(tiny_invoice)
    baseline = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    answer["fields"]["line_items"] = list(answer["fields"]["line_items"]) + [{
        "sl": 2, "description": "Invented row", "hsn_sac": "00000000",
        "uom": "NOS", "quantity": "1", "unit_price": "1.00", "amount": "1.00",
    }]
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)

    extra = [i for i in score.instances if i.origin == "returned_only"]
    assert extra, "the invented row produced assessed instances"
    assert all(i.correct is False for i in extra)
    assert score.assessed > baseline.assessed
    assert score.correct == baseline.correct


def test_a_missing_line_item_row_is_still_assessed(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    baseline = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    answer["fields"]["line_items"] = []
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    assert score.assessed == baseline.assessed
    assert score.correct < baseline.correct


def test_internal_line_cells_are_not_scored_and_are_counted(tiny_invoice, settings):
    score = score_document(tiny_invoice, make_response(tiny_invoice,
                                                       perfect_answer(tiny_invoice)), settings)
    paths = {i.path for i in score.instances}
    assert not any("amount_minor" in p for p in paths)
    assert not any("quantity_thousandths" in p for p in paths)
    assert score.excluded_cells == 3


def test_free_text_is_reported_separately_from_the_exact_and_normalised_classes(
    tiny_invoice, settings
):
    score = score_document(tiny_invoice, make_response(tiny_invoice,
                                                       perfect_answer(tiny_invoice)), settings)
    groups = {i.group for i in score.instances}
    assert groups == {"exact_normalised", "free_text"}
    free_text_fields = {i.field for i in score.instances if i.group == "free_text"}
    assert "vendor_address" in free_text_fields
    assert "invoice_total" not in free_text_fields


# --------------------------------------------------------------------------- #
# Malformed and empty replies                                                  #
# --------------------------------------------------------------------------- #


def test_a_model_returning_malformed_json_is_a_processing_failure(tiny_invoice, settings):
    response = response_from_text(
        '{"fields": {"invoice_number": "TST/26-27/0001",', tiny_invoice
    )
    response.latency_s = 0.5
    score = score_document(tiny_invoice, response, settings)

    assert score.processing_failure is True
    assert score.queue_codes == ["FAIL"]
    assert score.outcome == "exception"
    assert score.instances == [], "a failed document is excluded from field accuracy"


def test_an_empty_reply_is_a_processing_failure(tiny_invoice, settings):
    response = response_from_text("", tiny_invoice)
    score = score_document(tiny_invoice, response, settings)
    assert score.processing_failure is True
    assert score.failure_reason == "empty response"


def test_json_inside_a_code_fence_is_read(tiny_invoice):
    response = response_from_text(
        '```json\n{"fields": {"invoice_number": "X"}, "confidence": {"invoice_number": 0.5}}\n```',
        tiny_invoice,
    )
    assert response.ok is True
    assert response.fields["invoice_number"] == "X"
    assert response.confidence["invoice_number"] == 0.5


def test_json_with_prose_around_it_is_read(tiny_invoice):
    response = response_from_text(
        'Sure. {"fields": {"invoice_number": "X"}} I hope that helps.', tiny_invoice
    )
    assert response.ok is True
    assert response.fields["invoice_number"] == "X"


def test_a_bare_field_object_is_accepted(tiny_invoice):
    response = response_from_text('{"invoice_number": "X", "currency": "INR"}', tiny_invoice)
    assert response.ok is True
    assert response.fields["invoice_number"] == "X"
    assert response.confidence_reported is False


def test_a_percentage_confidence_is_rescaled(tiny_invoice):
    response = response_from_text(
        '{"fields": {"invoice_number": "X"}, "confidence": {"invoice_number": 95}}',
        tiny_invoice,
    )
    assert response.confidence["invoice_number"] == 0.95


# --------------------------------------------------------------------------- #
# The queue, straight-through and exception                                    #
# --------------------------------------------------------------------------- #


def test_a_low_confidence_field_routes_the_document_to_review(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    answer["confidence"]["vendor_ein"] = 0.40
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    assert "LOWCONF" in score.queue_codes
    assert score.outcome == "exception"


def test_the_threshold_moves_the_exception_rate(tiny_invoice):
    answer = perfect_answer(tiny_invoice)
    answer["confidence"]["vendor_ein"] = 0.90
    high = score_document(tiny_invoice, make_response(tiny_invoice, answer),
                          ScoringSettings(confidence_threshold=0.95))
    low = score_document(tiny_invoice, make_response(tiny_invoice, answer),
                         ScoringSettings(confidence_threshold=0.85))
    assert "LOWCONF" in high.queue_codes
    assert "LOWCONF" not in low.queue_codes


def test_a_broken_total_is_a_validation_failure(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    answer["fields"]["invoice_total"] = "9999.00"
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    assert "VALFAIL" in score.queue_codes
    failed = [v for v in score.validation if v["status"] == "fail"]
    assert any(v["rule"] == "total_equals_components" for v in failed)


def test_a_missing_key_is_a_validation_failure_when_required_fields_is_all(tiny_invoice):
    answer = perfect_answer(tiny_invoice)
    answer["fields"].pop("due_date")
    strict = score_document(tiny_invoice, make_response(tiny_invoice, answer),
                            ScoringSettings(required_fields="all"))
    lenient = score_document(tiny_invoice, make_response(tiny_invoice, answer),
                             ScoringSettings(required_fields="none"))
    assert "VALFAIL" in strict.queue_codes
    assert "VALFAIL" not in lenient.queue_codes


def test_a_validation_rule_with_no_inputs_is_not_applicable_not_a_failure(
    tiny_dataset, settings
):
    kyc = tiny_dataset.by_id("tiny-kyc-0003")
    score = score_document(kyc, make_response(kyc, perfect_answer(kyc)), settings)
    statuses = {v["rule"]: v["status"] for v in score.validation}
    assert statuses["total_equals_components"] == "not_applicable"
    assert "VALFAIL" not in score.queue_codes


def test_an_audit_that_changed_nothing_is_still_straight_through(tiny_invoice):
    settings = ScoringSettings(audit_rate=1.0)
    score = score_document(tiny_invoice, make_response(tiny_invoice,
                                                       perfect_answer(tiny_invoice)), settings)
    assert score.audit_drawn is True
    assert score.audit_changed is False
    assert score.outcome == "straight_through"


def test_an_audit_that_changed_the_output_is_an_exception(tiny_invoice):
    settings = ScoringSettings(audit_rate=1.0, confidence_threshold=0.0,
                               required_fields="none", validation=False)
    answer = perfect_answer(tiny_invoice)
    answer["fields"]["vendor_name"] = "Something Else Entirely"
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    assert score.audit_changed is True
    assert score.outcome == "exception"
    assert "AUDIT" in score.queue_codes


def test_the_audit_draw_is_deterministic():
    first = [audit_draw(f"doc-{i}", "seed", 0.5) for i in range(50)]
    second = [audit_draw(f"doc-{i}", "seed", 0.5) for i in range(50)]
    assert first == second
    assert audit_draw("doc-1", "seed", 0.0) is False


# --------------------------------------------------------------------------- #
# Run level                                                                    #
# --------------------------------------------------------------------------- #


def test_the_identity_holds_and_the_counts_reconcile(tiny_dataset, settings):
    responses = {d.doc_id: make_response(d, perfect_answer(d)) for d in tiny_dataset}
    admission = Admission(received=len(tiny_dataset))
    run = score_run(tiny_dataset, responses, settings, admission)

    counts = run["counts"]
    assert counts["documents_admitted_to_processing"] == 3
    assert (counts["documents_straight_through"] + counts["documents_exception"]) == 3
    assert run["identity_check"]["holds"] is True
    assert run["straight_through"]["denominator"] == run["exception"]["denominator"]


def test_a_rejected_document_leaves_the_denominator_and_is_counted(tiny_dataset, settings):
    documents = [d for d in tiny_dataset if d.doc_id != "tiny-kyc-0003"]
    responses = {d.doc_id: make_response(d, perfect_answer(d)) for d in documents}
    admission = Admission(
        received=len(tiny_dataset),
        rejected=[{"doc_id": "tiny-kyc-0003", "rule": "a named pre-processing rule"}],
    )
    run = score_run(tiny_dataset, responses, settings, admission)
    assert run["counts"]["documents_received"] == 3
    assert run["counts"]["documents_rejected_before_processing"] == 1
    assert run["counts"]["documents_admitted_to_processing"] == 2


def test_counts_that_do_not_reconcile_fail_the_run(tiny_dataset, settings):
    responses = {d.doc_id: make_response(d, perfect_answer(d)) for d in tiny_dataset}
    admission = Admission(received=99)          # deliberately wrong
    with pytest.raises(ReconciliationError):
        score_run(tiny_dataset, responses, settings, admission)


def test_breakdowns_cover_tier_language_and_type(tiny_dataset, settings):
    responses = {d.doc_id: make_response(d, perfect_answer(d)) for d in tiny_dataset}
    run = score_run(tiny_dataset, responses, settings, Admission(received=3))
    assert set(run["breakdowns"]["by_tier"]) == {"T1", "T4", "T5"}
    assert set(run["breakdowns"]["by_language"]) == {"en", "en+hi"}
    assert set(run["breakdowns"]["by_doc_type"]) == {"invoice", "kyc_pack"}


def test_latency_percentiles_use_the_nearest_rank_method(tiny_dataset, settings):
    responses = {}
    for latency, document in zip((2.0, 4.0, 9.0), tiny_dataset):
        responses[document.doc_id] = make_response(
            document, perfect_answer(document), latency_s=latency
        )
    run = score_run(tiny_dataset, responses, settings, Admission(received=3))
    latency = run["latency"]
    assert latency["count"] == 3
    assert latency["p50_s"] == 4.0        # ceil(0.5 * 3) = 2nd value
    assert latency["p95_s"] == 9.0        # ceil(0.95 * 3) = 3rd value
    assert latency["max_s"] == 9.0


def test_a_failed_document_stays_in_the_denominator_and_its_time_is_separate(
    tiny_dataset, settings
):
    responses = {}
    for document in tiny_dataset:
        if document.doc_id == "tiny-inv-0002":
            failed = response_from_text("not json at all", document)
            failed.latency_s = 30.0
            responses[document.doc_id] = failed
        else:
            responses[document.doc_id] = make_response(document, perfect_answer(document))
    run = score_run(tiny_dataset, responses, settings, Admission(received=3))
    assert run["counts"]["documents_processing_failure"] == 1
    assert run["counts"]["documents_admitted_to_processing"] == 3
    assert run["latency"]["count"] == 2
    assert run["latency"]["failure_times"]["count"] == 1
    assert run["latency"]["failure_times"]["max_s"] == 30.0
    assert run["exclusions"]["documents_excluded_from_field_accuracy"] == 1


def test_the_alias_table_is_applied_to_every_system_identically(tiny_invoice, settings):
    answer = perfect_answer(tiny_invoice)
    answer["fields"]["InvoiceId"] = answer["fields"].pop("invoice_number")
    answer["fields"]["Invoice Date"] = answer["fields"].pop("invoice_date")
    score = score_document(tiny_invoice, make_response(tiny_invoice, answer), settings)
    by_path = {i.path: i for i in score.instances}
    assert by_path["invoice_number"].correct is True
    assert by_path["invoice_date"].correct is True
    assert len(score.aliased_keys) == 2
