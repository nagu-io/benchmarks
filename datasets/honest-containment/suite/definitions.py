"""The five containment definitions, in one file.

Charter section 3.9 governs every line here. Four of the five are definitions in common
use across the contact-centre and voice-agent industry: they are described here as common
practice, and they are not attributed to any named vendor, because they are conventions
rather than any one company's property. The fifth is ours, charter 3.9.1.

Every definition takes the same scored contact and returns a bool plus the reason, so a
reader can see exactly which condition moved a contact between two columns.
"""

from __future__ import annotations

from dataclasses import dataclass

# The window a vendor picks for definition D. Both are in common use, so both are scored
# and both are printed; the report never quotes one without saying which.
D_WINDOWS_HOURS = (24, 72)

# Our window, charter 3.9.1, in hours.
OURS_WINDOW_HOURS = 7 * 24


@dataclass(frozen=True)
class Definition:
    key: str
    name: str
    statement: str
    counts_that_ours_does_not: str


DEFINITIONS = [
    Definition(
        "A_no_transfer", "no transfer to a human",
        "A contact is contained when it was not transferred to a human during the "
        "contact. Nothing else is tested: not whether the caller's intent was met, not "
        "whether the caller came back, not whether the caller asked for a person and was "
        "refused.",
        "a hang-up, an unresolved contact, and a refused request for a person"),
    Definition(
        "B_no_human_handled", "no transfer and no human handling",
        "A contact is contained when no human joined it at any point, which extends "
        "definition A to callbacks, warm transfers completed after the contact and work a "
        "person did on the contact afterwards.",
        "an unresolved contact that the caller repeats the next day"),
    Definition(
        "C_self_service_completion", "session ended in a self-service end state",
        "A contact is contained when the agent reached an end state its own configuration "
        "treats as a completion. The end state is the agent's own disposition code, so the "
        "system under test is also the system that decides whether it succeeded.",
        "an end state the agent declared without the ground truth supporting it"),
    Definition(
        "D_no_repeat", "no repeat contact inside the vendor's chosen window",
        "A contact is contained when no further contact arrives from the same caller "
        "inside a window the vendor chooses, commonly 24 or 72 hours. Resolution is not "
        "tested at all: the absence of a second contact stands in for it. Both windows are "
        "scored here and both are printed, because the window is the whole metric.",
        "a repeat on day four, and an unresolved contact the caller gave up on"),
    Definition(
        "ours_3_9_1", "resolved, no human requested or joined, no repeat within seven days",
        "A contact is contained when all three hold: the stated intent was resolved "
        "against the scenario's ground truth; the caller did not ask for a person and no "
        "person joined, took a callback or did work on the contact afterwards; and no "
        "further contact came from the same caller about the same intent within seven "
        "calendar days.",
        "—"),
]

DEFINITION_KEYS = [d.key for d in DEFINITIONS]


def contained_A(c: dict) -> tuple[bool, str]:
    if c["transfer_to_human"]:
        return False, "transferred to a human"
    return True, "no transfer"


def contained_B(c: dict) -> tuple[bool, str]:
    if c["human_joined"]:
        return False, "a human joined, took a callback or worked the contact afterwards"
    return True, "no human handling"


def contained_C(c: dict) -> tuple[bool, str]:
    if c["agent_disposition"] in c["vendor_success_dispositions"]:
        return True, f"agent disposition {c['agent_disposition']} is a configured success"
    return False, f"agent disposition {c['agent_disposition']} is not a configured success"


def contained_D(c: dict, window_hours: int) -> tuple[bool, str]:
    hours = c["repeat_contact_hours"]
    if c["repeat_contact"] and hours is not None and hours <= window_hours:
        return False, f"repeat contact after {hours} hours, inside the {window_hours}-hour window"
    return True, f"no repeat contact inside the {window_hours}-hour window"


def contained_ours(c: dict) -> tuple[bool, str]:
    if not c["resolved"]:
        return False, "the stated intent was not resolved against the ground truth"
    if c["human_requested_by_caller"]:
        return False, "the caller asked for a person"
    if c["human_joined"]:
        return False, "a human joined or worked the contact"
    hours = c["repeat_contact_hours"]
    if c["repeat_contact"] and hours is not None and hours <= OURS_WINDOW_HOURS:
        return False, f"repeat contact about the same intent after {hours} hours"
    return True, "resolved, no person requested or joined, no repeat within seven days"


# Phrasings heard in the market, and which of the four they are. A vendor rarely says
# "definition A"; it says one of these. Each maps onto a definition above, and the one
# compound phrasing is scored as the conjunction it is.
COMMON_PHRASINGS = [
    ("no transfer to a human", "A_no_transfer", "the definition exactly"),
    ("the session ended without the agent asking for a person", "A_no_transfer",
     "the same test, observed from the agent's side rather than the telephony record"),
    ("no human touched the contact", "B_no_human_handled", "the definition exactly"),
    ("resolved per the disposition code the agent wrote", "C_self_service_completion",
     "the definition exactly"),
    ("no repeat contact within 24 hours, or within 72 hours", "D_no_repeat",
     "the definition exactly; the window is the whole metric and is always printed"),
    ("no transfer and no repeat contact", "A_and_D_no_repeat_72h",
     "the conjunction of A and D, scored here as its own column so that the compound "
     "phrasing is not read as either half"),
]


def contained_A_and_D(c: dict, window_hours: int = 72) -> tuple[bool, str]:
    """The compound phrasing: no transfer, and no repeat inside the window."""
    a_ok, a_why = contained_A(c)
    d_ok, d_why = contained_D(c, window_hours)
    if a_ok and d_ok:
        return True, f"{a_why}, and {d_why}"
    return False, a_why if not a_ok else d_why


def score_all(c: dict) -> dict:
    """Every definition applied to one scored contact."""
    out = {}
    for key, fn in (("A_no_transfer", contained_A), ("B_no_human_handled", contained_B),
                    ("C_self_service_completion", contained_C)):
        ok, why = fn(c)
        out[key] = {"contained": ok, "reason": why}
    for w in D_WINDOWS_HOURS:
        ok, why = contained_D(c, w)
        out[f"D_no_repeat_{w}h"] = {"contained": ok, "reason": why}
    ok, why = contained_A_and_D(c, 72)
    out["A_and_D_no_repeat_72h"] = {"contained": ok, "reason": why}
    ok, why = contained_ours(c)
    out["ours_3_9_1"] = {"contained": ok, "reason": why}
    return out


def false_containment(rows: list[dict], reference: str) -> dict:
    """Charter 3.10. Always reported against a named reference definition.

    Numerator broken down by which of the three conditions in 3.9.1 failed, because the
    three failures cost a BPO different amounts.
    """
    ref_contained = [r for r in rows if r["containment"][reference]["contained"]]
    denominator = len(ref_contained)
    breakdown = {"not_resolved": 0, "person_requested_not_provided": 0,
                 "repeat_within_seven_days": 0}
    numerator = 0
    for r in ref_contained:
        if r["containment"]["ours_3_9_1"]["contained"]:
            continue
        numerator += 1
        if not r["resolved"]:
            breakdown["not_resolved"] += 1
        if r["human_requested_by_caller"] and not r["human_joined"]:
            breakdown["person_requested_not_provided"] += 1
        hours = r["repeat_contact_hours"]
        if r["repeat_contact"] and hours is not None and hours <= OURS_WINDOW_HOURS:
            breakdown["repeat_within_seven_days"] += 1
    return {
        "reference": reference,
        "numerator": numerator,
        "denominator": denominator,
        "rate": None if denominator == 0 else numerator / denominator,
        "breakdown": breakdown,
        "ambiguous_excluded": sum(1 for r in rows if r.get("either_outcome_acceptable")),
    }
