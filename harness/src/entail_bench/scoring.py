"""Scoring, implementing charter/methodology.md sections 3.3, 3.4, 3.5 and 3.8.

Every metric here states its numerator, its denominator and its exclusions in
the code that computes it, and every exclusion is counted and carried through to
the report. Nothing is silently dropped (charter 3.1.2), and the run fails if
the counts do not reconcile.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from .adapters.base import Response
from .aliases import apply_aliases, apply_row_aliases, load_aliases
from .dataset import Dataset, Document
from .errors import ReconciliationError
from .fieldrules import FieldRules, load_field_rules
from .normalise import parse_amount, parse_date, parse_number
from .util import percentile_nearest_rank

# Review-queue entry codes, from 06-delivery/build-standards.md section 7.1.
QUEUE_CODES = ("LOWCONF", "VALFAIL", "FAIL", "FLAG", "DRIFT", "AUDIT")
#: Codes that put a document into the exception numerator (charter 3.5.2).
#: AUDIT is not here: an audit that changed nothing is not an exception.
EXCEPTION_CODES = ("LOWCONF", "VALFAIL", "FAIL", "FLAG", "DRIFT")


@dataclass
class ScoringSettings:
    confidence_threshold: float = 0.85
    calibration_bins: int = 10
    audit_rate: float = 0.0
    audit_seed: str = "entail-bench"
    currency_required: bool = True
    numeric_tolerance: str | None = None
    required_fields: str = "all"          # all | none
    validation: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Instance:
    """One assessed field instance."""

    doc_id: str
    path: str
    field: str
    field_class: str
    group: str                     # exact_normalised | free_text
    origin: str                    # ground_truth | returned_only
    correct: bool
    rule: str
    reason: str
    exact_strict: bool
    confidence: float | None
    expected: Any
    returned: Any
    note: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocumentScore:
    doc_id: str
    doc_type: str
    doc_subtype: str
    tier: int | None
    language: str
    page_count: int
    outcome: str                          # straight_through | exception
    queue_codes: list[str] = field(default_factory=list)
    audit_drawn: bool = False
    audit_changed: bool = False
    processing_failure: bool = False
    failure_reason: str | None = None
    instances: list[Instance] = field(default_factory=list)
    out_of_schema_keys: list[str] = field(default_factory=list)
    aliased_keys: list[str] = field(default_factory=list)
    excluded_cells: int = 0
    unreadable_ground_truth: int = 0
    validation: list[dict] = field(default_factory=list)
    latency_s: float | None = None
    backoff_s: float = 0.0
    tokens: dict = field(default_factory=dict)
    pages_billed: int | None = None
    confidence_reported: bool = False
    model_version: str | None = None

    # -- derived ------------------------------------------------------- #
    @property
    def assessed(self) -> int:
        return sum(1 for i in self.instances if i.group == "exact_normalised")

    @property
    def correct(self) -> int:
        return sum(1 for i in self.instances if i.group == "exact_normalised" and i.correct)

    def as_dict(self) -> dict:
        out = asdict(self)
        out["instances"] = [i.as_dict() for i in self.instances]
        out["assessed"] = self.assessed
        out["correct"] = self.correct
        return out


# --------------------------------------------------------------------------- #
# Scoring one document                                                         #
# --------------------------------------------------------------------------- #


def score_document(
    document: Document,
    response: Response,
    settings: ScoringSettings,
    rules: FieldRules | None = None,
) -> DocumentScore:
    rules = rules or load_field_rules()
    score = DocumentScore(
        doc_id=document.doc_id,
        doc_type=document.doc_type,
        doc_subtype=document.doc_subtype,
        tier=document.tier,
        language=document.language_key,
        page_count=document.page_count,
        outcome="exception",
        latency_s=response.latency_s,
        backoff_s=response.backoff_s or 0.0,
        tokens=response.tokens.as_dict(),
        pages_billed=response.pages_billed,
        confidence_reported=response.confidence_reported,
        model_version=response.model_version,
    )

    # A document that failed to process is excluded from field-level accuracy
    # (charter 3.3.4) and counted under the processing-failure line. It enters
    # the review queue under FAIL (charter 3.5.2) and stays in the admitted
    # denominator.
    if not response.ok:
        score.processing_failure = True
        score.failure_reason = response.error or "processing failure"
        score.queue_codes = ["FAIL"]
        score.outcome = "exception"
        return score

    returned, moved, out_of_schema = apply_aliases(dict(response.fields), document.schema)
    score.aliased_keys = moved
    score.out_of_schema_keys = out_of_schema

    for name, type_ in sorted(document.schema.items()):
        expected = document.fields.get(name)
        if _is_unreadable(expected):
            score.unreadable_ground_truth += 1
            continue
        if type_ == "line_items":
            _score_line_items(
                score, document, name, expected, returned.get(name),
                name in returned, response, settings, rules,
            )
            continue
        _score_scalar(
            score, document, name, type_, expected, returned.get(name),
            name in returned, response, settings, rules,
        )

    if settings.validation:
        score.validation = run_validation(document, returned, settings, rules)

    _decide_queue(score, document, settings)
    return score


def _is_unreadable(expected: Any) -> bool:
    """Ground truth the labeller marked unreadable, charter 3.3.4."""
    return isinstance(expected, dict) and expected.get("unreadable") is True


def _confidence_for(response: Response, *paths: str) -> float | None:
    for path in paths:
        if path in response.confidence:
            return response.confidence[path]
    return None


def _score_scalar(
    score: DocumentScore,
    document: Document,
    name: str,
    type_: str,
    expected: Any,
    returned: Any,
    present: bool,
    response: Response,
    settings: ScoringSettings,
    rules: FieldRules,
) -> None:
    field_class = rules.class_for(name, type_)
    result = rules.match(
        field_class, expected, returned,
        present=present,
        display_format=document.display_formats.get("date"),
        decimal_separator=document.display_formats.get("decimal_separator"),
        expected_currency=document.currency,
        returned_currency=_returned_currency(response),
        currency_required=settings.currency_required,
        numeric_tolerance=settings.numeric_tolerance,
    )
    score.instances.append(Instance(
        doc_id=document.doc_id,
        path=name,
        field=name,
        field_class=field_class,
        group=rules.group_for(field_class),
        origin="ground_truth",
        correct=result.correct,
        rule=result.rule,
        reason=result.reason,
        exact_strict=result.exact_strict,
        confidence=_confidence_for(response, name),
        expected=expected,
        returned=returned if present else None,
        note=result.note,
    ))


def _returned_currency(response: Response) -> str | None:
    value = response.fields.get("currency")
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return None


def _score_line_items(
    score: DocumentScore,
    document: Document,
    list_name: str,
    expected_rows: Any,
    returned_rows: Any,
    present: bool,
    response: Response,
    settings: ScoringSettings,
    rules: FieldRules,
) -> None:
    expected_rows = expected_rows if isinstance(expected_rows, list) else []
    returned_rows = returned_rows if isinstance(returned_rows, list) else []
    cells = _scored_cells(expected_rows, document.doc_subtype, rules)
    excluded_per_row = sum(
        1 for row in expected_rows for cell in row
        if not rules.line_cell_scored(cell, document.doc_subtype)[0]
    )
    score.excluded_cells += excluded_per_row

    for index in range(max(len(expected_rows), len(returned_rows))):
        exp_row = expected_rows[index] if index < len(expected_rows) else None
        got_row = returned_rows[index] if index < len(returned_rows) else None
        if isinstance(got_row, dict):
            got_row = apply_row_aliases(got_row, cells)

        if exp_row is None:
            # Rows the system returned that the ground truth has no counterpart
            # for. Charter 3.3.3: each is one assessed instance and is always
            # incorrect. A system cannot raise its accuracy by inventing rows.
            if not isinstance(got_row, dict):
                continue
            for cell in cells:
                if cell not in got_row:
                    continue
                score.instances.append(Instance(
                    doc_id=document.doc_id,
                    path=f"{list_name}[{index}].{cell}",
                    field=f"{list_name}.{cell}",
                    field_class=rules.class_for(cell, "string"),
                    group=rules.group_for(rules.class_for(cell, "string")),
                    origin="returned_only",
                    correct=False,
                    rule="extra",
                    reason="extra_row",
                    exact_strict=False,
                    confidence=_confidence_for(
                        response, f"{list_name}[{index}].{cell}", list_name
                    ),
                    expected=None,
                    returned=got_row.get(cell),
                ))
            continue

        for cell in cells:
            if cell not in exp_row:
                continue
            expected = exp_row.get(cell)
            has_cell = isinstance(got_row, dict) and cell in got_row
            returned = got_row.get(cell) if isinstance(got_row, dict) else None
            cell_type = _cell_type(cell)
            field_class = rules.class_for(cell, cell_type)
            result = rules.match(
                field_class, expected, returned,
                present=has_cell,
                display_format=document.display_formats.get("date"),
                decimal_separator=document.display_formats.get("decimal_separator"),
                expected_currency=document.currency,
                returned_currency=_returned_currency(response),
                currency_required=settings.currency_required,
                numeric_tolerance=settings.numeric_tolerance,
            )
            score.instances.append(Instance(
                doc_id=document.doc_id,
                path=f"{list_name}[{index}].{cell}",
                field=f"{list_name}.{cell}",
                field_class=field_class,
                group=rules.group_for(field_class),
                origin="ground_truth",
                correct=result.correct,
                rule=result.rule,
                reason=result.reason,
                exact_strict=result.exact_strict,
                confidence=_confidence_for(
                    response, f"{list_name}[{index}].{cell}", list_name
                ),
                expected=expected,
                returned=returned if has_cell else None,
                note=result.note,
            ))


def _scored_cells(rows: list, doc_subtype: str, rules: FieldRules) -> list[str]:
    seen: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for cell in row:
            if cell in seen:
                continue
            scored, _ = rules.line_cell_scored(cell, doc_subtype)
            if scored:
                seen.append(cell)
    return seen


def _cell_type(cell: str) -> str:
    return {
        "amount": "money", "unit_price": "money", "quantity": "number",
        "sl": "number", "description": "string", "uom": "string",
        "hsn_sac": "string",
    }.get(cell, "string")


# --------------------------------------------------------------------------- #
# Validation rules -> VALFAIL                                                  #
# --------------------------------------------------------------------------- #


def run_validation(
    document: Document,
    returned: dict,
    settings: ScoringSettings,
    rules: FieldRules,
) -> list[dict]:
    results: list[dict] = []

    if settings.required_fields == "all":
        missing = [k for k in document.schema if k not in returned]
        results.append({
            "rule": "required_fields_present",
            "status": "fail" if missing else "pass",
            "missing": missing[:20],
            "missing_count": len(missing),
        })

    results.append(_rule_line_sum(document, returned, rules))
    results.append(_rule_total(document, returned, rules))
    results.append(_rule_date_order(document, returned, rules))
    return [r for r in results if r]


def _tolerance(rules: FieldRules, rule_id: str) -> Decimal:
    for rule in rules.validation_rules:
        if rule.get("id") == rule_id:
            return Decimal(str(rule.get("tolerance_minor_units", 1))) / Decimal(100)
    return Decimal("0.01")


def _amount_of(returned: dict, name: str, document: Document) -> Decimal | None:
    if name not in returned:
        return None
    return parse_amount(
        str(returned.get(name)),
        decimal_separator=document.display_formats.get("decimal_separator"),
    ).value


def _rule_line_sum(document: Document, returned: dict, rules: FieldRules) -> dict:
    spec = next((r for r in rules.validation_rules if r.get("id") == "line_sum_equals_base"), {})
    list_name = next(
        (n for n in spec.get("line_field_any", []) if isinstance(returned.get(n), list)), None
    )
    base_name = next(
        (n for n in spec.get("base_field_any", []) if n in document.schema and n in returned), None
    )
    if not list_name or not base_name:
        return {"rule": "line_sum_equals_base", "status": "not_applicable",
                "reason": "the returned record has no line list or no stated base"}
    total = Decimal(0)
    for row in returned[list_name]:
        if not isinstance(row, dict) or "amount" not in row:
            return {"rule": "line_sum_equals_base", "status": "not_applicable",
                    "reason": "a returned row carries no amount"}
        value = parse_amount(
            str(row["amount"]),
            decimal_separator=document.display_formats.get("decimal_separator"),
        ).value
        if value is None:
            return {"rule": "line_sum_equals_base", "status": "not_applicable",
                    "reason": "a returned line amount is not a number"}
        total += value
    base = _amount_of(returned, base_name, document)
    if base is None:
        return {"rule": "line_sum_equals_base", "status": "fail",
                "reason": f"{base_name} was returned but is not a number"}
    ok = abs(total - base) <= _tolerance(rules, "line_sum_equals_base")
    return {"rule": "line_sum_equals_base", "status": "pass" if ok else "fail",
            "base_field": base_name, "line_sum": str(total), "base_value": str(base)}


def _rule_total(document: Document, returned: dict, rules: FieldRules) -> dict:
    formula = rules.total_formulas.get(document.doc_subtype)
    if not formula:
        return {"rule": "total_equals_components", "status": "not_applicable",
                "reason": f"no published component formula for {document.doc_subtype}"}
    target_name = formula["target"]
    if target_name not in returned:
        return {"rule": "total_equals_components", "status": "not_applicable",
                "reason": f"{target_name} was not returned"}
    target = _amount_of(returned, target_name, document)
    if target is None:
        return {"rule": "total_equals_components", "status": "fail",
                "reason": f"{target_name} was returned but is not a number"}
    total = Decimal(0)
    for name in formula.get("plus", []):
        if name not in document.schema:
            continue
        value = _amount_of(returned, name, document)
        if value is None:
            return {"rule": "total_equals_components", "status": "not_applicable",
                    "reason": f"component {name} is absent or not a number"}
        total += value
    for name in formula.get("minus", []):
        if name not in document.schema:
            continue
        value = _amount_of(returned, name, document)
        if value is None:
            return {"rule": "total_equals_components", "status": "not_applicable",
                    "reason": f"component {name} is absent or not a number"}
        total -= value
    ok = abs(total - target) <= _tolerance(rules, "total_equals_components")
    return {"rule": "total_equals_components", "status": "pass" if ok else "fail",
            "target_field": target_name, "components": str(total), "target_value": str(target)}


def _rule_date_order(document: Document, returned: dict, rules: FieldRules) -> dict:
    checked = 0
    failures: list[str] = []
    fmt = document.display_formats.get("date")
    for later_name, earlier_name in rules.date_order_pairs:
        if later_name not in document.schema or earlier_name not in document.schema:
            continue
        later = parse_date(str(returned.get(later_name)), display_format=fmt).value
        earlier = parse_date(str(returned.get(earlier_name)), display_format=fmt).value
        if later is None or earlier is None:
            continue
        checked += 1
        if later < earlier:
            failures.append(f"{later_name} before {earlier_name}")
    if checked == 0:
        return {"rule": "date_order", "status": "not_applicable",
                "reason": "no date pair on this document could be parsed from the reply"}
    return {"rule": "date_order", "status": "fail" if failures else "pass",
            "checked": checked, "failures": failures}


# --------------------------------------------------------------------------- #
# The review queue -> straight-through and exception                           #
# --------------------------------------------------------------------------- #


def audit_draw(doc_id: str, seed: str, rate: float) -> bool:
    """Deterministic sampled-audit draw, so a re-score reproduces the run."""
    if rate <= 0:
        return False
    digest = hashlib.sha256(f"{seed}:{doc_id}".encode("utf-8")).hexdigest()
    return (int(digest[:16], 16) / float(1 << 64)) < rate


def _decide_queue(score: DocumentScore, document: Document, settings: ScoringSettings) -> None:
    codes: list[str] = []

    if score.confidence_reported:
        low = [
            i for i in score.instances
            if i.confidence is not None and i.confidence < settings.confidence_threshold
        ]
        if low:
            codes.append("LOWCONF")

    if any(v.get("status") == "fail" for v in score.validation):
        codes.append("VALFAIL")

    score.audit_drawn = audit_draw(document.doc_id, settings.audit_seed, settings.audit_rate)
    if score.audit_drawn:
        # Charter 3.4.2: an audited document is straight-through only if the
        # audit changed nothing. In the benchmark the audit reviewer changes
        # the output exactly when a scored field is wrong.
        score.audit_changed = any(
            not i.correct for i in score.instances if i.group == "exact_normalised"
        )

    score.queue_codes = codes
    entered_review = bool([c for c in codes if c in EXCEPTION_CODES]) or score.audit_changed
    score.outcome = "exception" if entered_review else "straight_through"
    if score.audit_changed and "AUDIT" not in score.queue_codes:
        score.queue_codes.append("AUDIT")


# --------------------------------------------------------------------------- #
# Run-level aggregation                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class Admission:
    """Charter 3.4.3: received, less rejected before processing by a named rule."""

    received: int
    rejected: list[dict] = field(default_factory=list)
    not_attempted: list[dict] = field(default_factory=list)

    @property
    def admitted(self) -> int:
        return self.received - len(self.rejected) - len(self.not_attempted)

    def as_dict(self) -> dict:
        return {
            "documents_received": self.received,
            "documents_rejected_before_processing": len(self.rejected),
            "rejected_detail": self.rejected,
            "documents_not_attempted": len(self.not_attempted),
            "not_attempted_detail": self.not_attempted,
            "documents_admitted_to_processing": self.admitted,
        }


def score_run(
    dataset: Dataset,
    responses: dict[str, Response],
    settings: ScoringSettings,
    admission: Admission,
    rules: FieldRules | None = None,
) -> dict:
    rules = rules or load_field_rules()
    scores: list[DocumentScore] = []
    for document in dataset:
        response = responses.get(document.doc_id)
        if response is None:
            continue
        scores.append(score_document(document, response, settings, rules))

    summary = summarise(scores, settings, admission, dataset)
    summary["documents"] = [s.as_dict() for s in scores]
    summary["scoring_settings"] = settings.as_dict()
    summary["match_rules"] = {
        "field_rules_version": rules.version,
        "field_rules_sha256": rules.source_sha256,
        "alias_table_version": load_aliases().version,
        "alias_table_sha256": load_aliases().source_sha256,
    }
    return summary


def summarise(
    scores: list[DocumentScore],
    settings: ScoringSettings,
    admission: Admission,
    dataset: Dataset | None = None,
) -> dict:
    from .calibration import calibration_report

    admitted = admission.admitted
    attempted = len(scores)
    failures = [s for s in scores if s.processing_failure]
    stp = [s for s in scores if s.outcome == "straight_through"]
    exceptions = [s for s in scores if s.outcome == "exception"]

    reconcile(admission, scores)

    instances = [i for s in scores for i in s.instances]
    scored = [i for i in instances if i.group == "exact_normalised"]
    free_text = [i for i in instances if i.group == "free_text"]

    latencies = [s.latency_s for s in scores if not s.processing_failure and s.latency_s is not None]
    failure_times = [s.latency_s for s in failures if s.latency_s is not None]
    backoffs = {s.doc_id: (s.backoff_s or 0.0) for s in scores}
    latencies_no_backoff = [
        (s.latency_s or 0.0) - (s.backoff_s or 0.0)
        for s in scores if not s.processing_failure and s.latency_s is not None
    ]

    by_code: dict[str, int] = {code: 0 for code in QUEUE_CODES}
    for s in exceptions:
        for code in s.queue_codes:
            by_code[code] = by_code.get(code, 0) + 1

    audit_drawn = [s for s in scores if s.audit_drawn]
    audit_clean = [s for s in audit_drawn if not s.audit_changed]

    confidence_reported = any(s.confidence_reported for s in scores)

    result = {
        "counts": {
            **admission.as_dict(),
            "documents_attempted": attempted,
            "documents_straight_through": len(stp),
            "documents_exception": len(exceptions),
            "documents_processing_failure": len(failures),
            "documents_audited": len(audit_drawn),
            "documents_audited_unchanged": len(audit_clean),
            "queue_re_entries": 0,
            "queue_re_entries_basis":
                "The benchmark harness processes each document once, so a "
                "re-entry cannot occur; production reporting counts them here",
            "partner_training_queue_entries": 0,
            "partner_training_queue_entries_basis":
                "Not generated by the benchmark harness.",
        },
        "field_accuracy": _accuracy_block(scored, "exact and normalised classes"),
        "free_text_accuracy": _accuracy_block(free_text, "free-text class"),
        "combined_accuracy": _accuracy_block(
            scored + free_text, "every class, printed so nothing is hidden"
        ),
        "exclusions": {
            "out_of_schema_returns": sum(len(s.out_of_schema_keys) for s in scores),
            "out_of_schema_basis":
                "Fields outside the published schema for the document type, "
                "excluded under charter 3.3.4 and counted here",
            "unreadable_ground_truth_instances":
                sum(s.unreadable_ground_truth for s in scores),
            "line_item_cells_excluded": sum(s.excluded_cells for s in scores),
            "line_item_cells_excluded_basis":
                "Internal minor-unit encodings and columns the page does not "
                "print, listed in field-rules.yaml",
            "documents_excluded_from_field_accuracy": len(failures),
            "documents_excluded_basis":
                "Documents that failed to process, charter 3.3.4.",
            "keys_mapped_by_alias_table": sum(len(s.aliased_keys) for s in scores),
        },
        "straight_through": {
            "definition":
                "Documents released with no human touch, divided by documents "
                "admitted to processing (charter 3.4)",
            "numerator": len(stp),
            "denominator": admitted,
            "rate": (len(stp) / admitted) if admitted else None,
            "audit_convention":
                "A document drawn into the sampled audit counts as "
                "straight-through only if the audit changed nothing",
        },
        "exception": {
            "definition":
                "Documents that entered human review, divided by documents "
                "admitted to processing (charter 3.5)",
            "numerator": len(exceptions),
            "denominator": admitted,
            "rate": (len(exceptions) / admitted) if admitted else None,
            "by_code": by_code,
            "confidence_threshold": settings.confidence_threshold,
            "audit_rate": (len(audit_drawn) / admitted) if admitted else None,
        },
        "latency": _latency_block(latencies, latencies_no_backoff, failure_times, backoffs),
        "calibration": calibration_report(scored, bins=settings.calibration_bins,
                                          confidence_reported=confidence_reported),
        "tokens": _token_block(scores),
        "identity_check": _identity_check(len(stp), len(exceptions), admitted),
        "breakdowns": {
            "by_tier": _breakdown(scores, lambda s: f"T{s.tier}", settings, admitted),
            "by_language": _breakdown(scores, lambda s: s.language, settings, admitted),
            "by_doc_type": _breakdown(scores, lambda s: s.doc_type, settings, admitted),
            "by_doc_subtype": _breakdown(scores, lambda s: s.doc_subtype, settings, admitted),
        },
        "by_field": _by_field(scored + free_text),
        "confidence_reported": confidence_reported,
    }
    if dataset is not None:
        result["tier_mix"] = dataset.summary()["tier_mix"]
        result["language_mix"] = dataset.summary()["language_mix"]
    return result


def _accuracy_block(instances: list[Instance], label: str) -> dict:
    from .normalise import FREE_TEXT_TOLERANCE_RULE

    assessed = len(instances)
    correct = sum(1 for i in instances if i.correct)
    strict = sum(1 for i in instances if i.exact_strict)
    reasons: dict[str, int] = {}
    for i in instances:
        if not i.correct:
            reasons[i.reason] = reasons.get(i.reason, 0) + 1
    block = {
        "population": label,
        "numerator_correct": correct,
        "denominator_assessed": assessed,
        "rate": (correct / assessed) if assessed else None,
        "exact_strict_matches": strict,
        "exact_strict_rate": (strict / assessed) if assessed else None,
        "returned_only_instances": sum(1 for i in instances if i.origin == "returned_only"),
        "incorrect_by_reason": dict(sorted(reasons.items())),
    }
    if label.startswith("free-text"):
        block["tolerance_rule"] = FREE_TEXT_TOLERANCE_RULE
    return block


def _latency_block(
    completed: list[float],
    completed_no_backoff: list[float],
    failure_times: list[float],
    backoffs: dict[str, float],
) -> dict:
    total_backoff = sum(backoffs.values())
    return {
        "definition":
            "Elapsed time from admission to processing until the output is "
            "written or the document enters the review queue (charter 3.8)",
        "population": "documents that completed",
        "count": len(completed),
        "p50_s": percentile_nearest_rank(completed, 50),
        "p95_s": percentile_nearest_rank(completed, 95),
        "p99_s": percentile_nearest_rank(completed, 99),
        "mean_s": (sum(completed) / len(completed)) if completed else None,
        "max_s": max(completed) if completed else None,
        "method": "nearest rank",
        "excluding_backoff": {
            "count": len(completed_no_backoff),
            "p50_s": percentile_nearest_rank(completed_no_backoff, 50),
            "p95_s": percentile_nearest_rank(completed_no_backoff, 95),
            "p99_s": percentile_nearest_rank(completed_no_backoff, 99),
            "total_backoff_s": total_backoff,
            "basis":
                "Backoff is a property of the account, not of the model, so the "
                "figures are reported with and without it (charter 3.8.4)",
        },
        "failure_times": {
            "count": len(failure_times),
            "p50_s": percentile_nearest_rank(failure_times, 50),
            "max_s": max(failure_times) if failure_times else None,
            "basis": "Documents that failed to process, reported separately.",
        },
        "queue_age": "Queue age is not measured by the harness; it belongs to operations",
    }


def _token_block(scores: list[DocumentScore]) -> dict:
    def total(key: str) -> int | None:
        values = [s.tokens.get(key) for s in scores if s.tokens.get(key) is not None]
        return sum(values) if values else None

    return {
        "input": total("input"),
        "output": total("output"),
        "reasoning": total("reasoning"),
        "pages_billed": sum(s.pages_billed or 0 for s in scores) or None,
        "documents_with_token_counts":
            sum(1 for s in scores if s.tokens.get("input") is not None),
    }


def _identity_check(stp: int, exceptions: int, admitted: int) -> dict:
    """Charter 3.5.3: straight-through rate plus exception rate equals one."""
    if not admitted:
        return {"holds": None, "reason": "no documents admitted"}
    total = (stp + exceptions) / admitted
    return {
        "holds": abs(total - 1.0) < 1e-9,
        "straight_through_plus_exception": total,
        "basis":
            "Both rates use the same denominator, documents admitted to "
            "processing; a supplier's figures that fail this identity are using "
            "two different denominators",
    }


def _breakdown(
    scores: list[DocumentScore],
    key,
    settings: ScoringSettings,
    admitted_total: int,
) -> dict:
    groups: dict[str, list[DocumentScore]] = {}
    for s in scores:
        groups.setdefault(str(key(s)), []).append(s)
    out: dict[str, dict] = {}
    for name, members in sorted(groups.items()):
        instances = [i for m in members for i in m.instances if i.group == "exact_normalised"]
        free = [i for m in members for i in m.instances if i.group == "free_text"]
        stp = sum(1 for m in members if m.outcome == "straight_through")
        latencies = [m.latency_s for m in members
                     if not m.processing_failure and m.latency_s is not None]
        out[name] = {
            "documents": len(members),
            "field_accuracy": _accuracy_block(instances, "exact and normalised classes"),
            "free_text_accuracy": _accuracy_block(free, "free-text class"),
            "straight_through": {
                "numerator": stp, "denominator": len(members),
                "rate": stp / len(members) if members else None,
            },
            "exception": {
                "numerator": len(members) - stp, "denominator": len(members),
                "rate": (len(members) - stp) / len(members) if members else None,
            },
            "processing_failures": sum(1 for m in members if m.processing_failure),
            "latency_p50_s": percentile_nearest_rank(latencies, 50),
            "latency_p95_s": percentile_nearest_rank(latencies, 95),
        }
    return out


def _by_field(instances: list[Instance]) -> dict:
    groups: dict[str, list[Instance]] = {}
    for i in instances:
        groups.setdefault(i.field, []).append(i)
    out: dict[str, dict] = {}
    for name, members in sorted(groups.items()):
        correct = sum(1 for m in members if m.correct)
        out[name] = {
            "class": members[0].field_class,
            "rule": members[0].rule,
            "numerator_correct": correct,
            "denominator_assessed": len(members),
            "rate": correct / len(members) if members else None,
        }
    return out


def reconcile(admission: Admission, scores: list[DocumentScore]) -> None:
    """Charter 3.1.2. The run fails if the counts do not reconcile."""
    attempted = len(scores)
    if attempted != admission.admitted:
        raise ReconciliationError(
            f"documents attempted ({attempted}) does not equal documents admitted "
            f"({admission.admitted}). Received {admission.received}, rejected "
            f"{len(admission.rejected)}, not attempted {len(admission.not_attempted)}."
        )
    stp = sum(1 for s in scores if s.outcome == "straight_through")
    exceptions = sum(1 for s in scores if s.outcome == "exception")
    if stp + exceptions != attempted:
        raise ReconciliationError(
            f"straight-through ({stp}) plus exceptions ({exceptions}) does not "
            f"equal documents attempted ({attempted})"
        )
