#!/usr/bin/env python3
"""Outcome encoding and error classification, shared by the generator and the scorer.

One module, so that the class a wrong automation is priced under is decided by the
same code whether the decision came from the reference policy in `generate.py` or
from a real system's predictions dropped in through `score.py --predictions`.

Outcome strings. Every decision is one string, so that a prediction file only has to
carry a string and the scorer can compare it to ground truth without knowing the
work type's internal shape.

    ticket_triage      route:<category>/<priority>[/escalate]
    kyc_case           kyc:<decision>[/<reason_code>]
    invoice_po_recon   recon:<decision>:<po>|<po>|...

Error classes are the keys of `rework_minutes.error_classes` in `labour-model.yaml`.
Three of them carry no minutes at all, because they have no detection route inside a
measurement window. Classifying an item into one of those three is the point: it puts
the item into the open exposure count instead of into a comfortable cost figure.
"""

from __future__ import annotations

TICKET_ERROR_CLASSES = [
    "ticket_wrong_category",
    "ticket_wrong_priority",
    "ticket_missed_escalation",
]
KYC_ERROR_CLASSES = [
    "kyc_false_pass",
    "kyc_false_reject",
    "kyc_wrong_refer_reason",
]
RECON_ERROR_CLASSES = [
    "recon_wrong_match",
    "recon_overpayment",
    "recon_underpayment",
    "recon_duplicate_post",
    "recon_missed_exception",
]

ALL_ERROR_CLASSES = TICKET_ERROR_CLASSES + KYC_ERROR_CLASSES + RECON_ERROR_CLASSES


# --------------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------------

def ticket_outcome(category: str, priority: str, escalate: bool) -> str:
    return f"route:{category}/{priority}" + ("/escalate" if escalate else "")


def kyc_outcome(decision: str, reason: str | None) -> str:
    return f"kyc:{decision}" + (f"/{reason}" if reason else "")


def recon_outcome(decision: str, purchase_orders: list[str]) -> str:
    return f"recon:{decision}:" + "|".join(purchase_orders)


def parse_ticket(outcome: str) -> dict:
    body = outcome.split(":", 1)[1]
    parts = body.split("/")
    return {"category": parts[0], "priority": parts[1],
            "escalate": len(parts) > 2 and parts[2] == "escalate"}


def parse_kyc(outcome: str) -> dict:
    body = outcome.split(":", 1)[1]
    parts = body.split("/")
    return {"decision": parts[0], "reason": parts[1] if len(parts) > 1 else None}


def parse_recon(outcome: str) -> dict:
    _, decision, pos = outcome.split(":", 2)
    return {"decision": decision, "purchase_orders": [p for p in pos.split("|") if p]}


PARSERS = {
    "ticket_triage": parse_ticket,
    "kyc_case": parse_kyc,
    "invoice_po_recon": parse_recon,
}


# --------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------

def classify_error(work_type: str, ground_truth_outcome: str,
                   proposed_outcome: str, attributes: dict) -> str | None:
    """Which rework class a wrong automation falls into. Returns None when the
    proposed outcome matches the ground truth, that is when nothing went wrong.

    Deterministic: the same three inputs always give the same class, whoever produced
    the proposed outcome."""
    if proposed_outcome == ground_truth_outcome:
        return None

    if work_type == "ticket_triage":
        truth = parse_ticket(ground_truth_outcome)
        pred = parse_ticket(proposed_outcome)
        if truth["escalate"] and not pred["escalate"]:
            return "ticket_missed_escalation"
        if truth["category"] != pred["category"]:
            return "ticket_wrong_category"
        if truth["priority"] != pred["priority"]:
            return "ticket_wrong_priority"
        # Escalated when the ground truth did not require it. The receiving queue
        # sends it back, which is the same piece of work as a wrong category.
        return "ticket_wrong_category"

    if work_type == "kyc_case":
        truth = parse_kyc(ground_truth_outcome)
        pred = parse_kyc(proposed_outcome)
        if truth["decision"] in ("refer", "reject") and pred["decision"] == "pass":
            return "kyc_false_pass"
        if truth["decision"] == "pass" and pred["decision"] != "pass":
            return "kyc_false_reject"
        # Both non-pass. The applicant is stopped either way, so the cost is the
        # reason code being wrong in the file, not the decision.
        return "kyc_wrong_refer_reason"

    if work_type == "invoice_po_recon":
        truth = parse_recon(ground_truth_outcome)
        pred = parse_recon(proposed_outcome)
        if truth["decision"] == pred["decision"]:
            # Same decision, different purchase orders.
            return "recon_wrong_match"
        if pred["decision"] == "matched":
            if truth["decision"] == "exception_hold":
                return "recon_missed_exception"
            if truth["decision"] == "reject":
                return "recon_duplicate_post"
            if truth["decision"] == "partial_match_hold":
                # A part delivery posted in full overpays the supplier; a credit note
                # ignored on a full posting underpays. Decided from the item's own
                # recorded attributes so that the class does not depend on who
                # produced the prediction.
                if attributes.get("credit_note_attached"):
                    return "recon_underpayment"
                return "recon_overpayment"
        return "recon_wrong_match"

    raise ValueError(f"unknown work type: {work_type}")


# --------------------------------------------------------------------------------
# Wrong-outcome construction, used by the generator only
# --------------------------------------------------------------------------------

TICKET_CATEGORY_POOL: list[str] = []
RECON_DECISIONS = ["matched", "partial_match_hold", "exception_hold", "reject"]
KYC_REFER_REASONS = [
    "name_mismatch", "address_unverified", "document_expired", "screening_hit",
    "source_of_funds_unclear", "beneficial_owner_unresolved",
]
TICKET_PRIORITIES = ["p1", "p2", "p3", "p4"]


def wrong_outcome(work_type: str, ground_truth: dict, attributes: dict,
                  rng, category_pool: list[str]) -> str:
    """Produce a plausible wrong outcome for the reference decision policy.

    The class it lands in is not chosen here. It is read back out by
    `classify_error`, so the generator and the scorer cannot disagree about it."""
    if work_type == "ticket_triage":
        truth = ground_truth
        roll = rng.random()
        if truth["escalation_required"] and roll < 0.55:
            return ticket_outcome(truth["category"], truth["priority"], False)
        if roll < 0.80:
            others = [c for c in category_pool if c != truth["category"]]
            return ticket_outcome(rng.choice(others), truth["priority"],
                                  truth["escalation_required"])
        others = [p for p in TICKET_PRIORITIES if p != truth["priority"]]
        return ticket_outcome(truth["category"], rng.choice(others),
                              truth["escalation_required"])

    if work_type == "kyc_case":
        truth = ground_truth
        roll = rng.random()
        if truth["decision"] in ("refer", "reject") and roll < 0.50:
            return kyc_outcome("pass", None)
        if truth["decision"] == "pass":
            return kyc_outcome(rng.choice(["refer", "reject"]),
                               rng.choice(KYC_REFER_REASONS))
        others = [r for r in KYC_REFER_REASONS if r != truth["reason_code"]]
        return kyc_outcome(truth["decision"], rng.choice(others))

    if work_type == "invoice_po_recon":
        truth = ground_truth
        pos = truth["matched_purchase_orders"]
        roll = rng.random()
        if truth["decision"] != "matched" and roll < 0.62:
            # The most consequential reconciliation error: something that should have
            # been held was posted.
            return recon_outcome("matched", pos)
        if roll < 0.80 and pos:
            # Same decision, wrong purchase order.
            swapped = list(pos)
            swapped[0] = f"PO-{(int(swapped[0].split('-')[1]) + 7) % 500000:06d}"
            return recon_outcome(truth["decision"], swapped)
        others = [d for d in RECON_DECISIONS if d != truth["decision"]]
        return recon_outcome(rng.choice(others), pos)

    raise ValueError(f"unknown work type: {work_type}")
