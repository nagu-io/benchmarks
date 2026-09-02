"""Tests for the five containment definitions and false containment.

The first test reproduces the worked arithmetic in charter section 3.9.8 and 3.10.6. Those
numbers are the charter's arithmetic example, invented there to show how the three
conditions compose. They are not a result, and this test asserts only that our code applies
the formula the charter states.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import definitions as D


def contact(resolved=True, transfer=False, human=False, requested=False,
            repeat=False, hours=None, disposition="resolved"):
    return {"resolved": resolved, "transfer_to_human": transfer, "human_joined": human,
            "human_requested_by_caller": requested, "repeat_contact": repeat,
            "repeat_contact_hours": hours, "agent_disposition": disposition,
            "vendor_success_dispositions": ["resolved", "completed", "contained"],
            "either_outcome_acceptable": False}


def build_charter_example():
    """300 contacts shaped as charter 3.9.8 describes them."""
    rows = []
    # 69 contacts where a human joined
    for _ in range(69):
        rows.append(contact(resolved=True, transfer=True, human=True,
                            disposition="transferred"))
    # of the 231 with no human: 24 refused requests for a person
    for _ in range(24):
        rows.append(contact(resolved=False, requested=True, disposition="contained"))
    # 22 repeats within seven days
    for _ in range(22):
        rows.append(contact(resolved=True, repeat=True, hours=100))
    # 9 unsupported resolutions
    for _ in range(9):
        rows.append(contact(resolved=False, disposition="resolved"))
    # 176 clean
    for _ in range(176):
        rows.append(contact())
    for r in rows:
        r["containment"] = D.score_all(r)
    return rows


def test_charter_arithmetic_3_9_8():
    rows = build_charter_example()
    assert len(rows) == 300
    b = sum(1 for r in rows if r["containment"]["B_no_human_handled"]["contained"])
    ours = sum(1 for r in rows if r["containment"]["ours_3_9_1"]["contained"])
    assert b == 231, b
    assert ours == 176, ours


def test_charter_false_containment_3_10_6():
    rows = build_charter_example()
    fc = D.false_containment(rows, "B_no_human_handled")
    assert fc["denominator"] == 231
    assert fc["numerator"] == 55
    assert round(fc["rate"] * 100, 1) == 23.8
    assert fc["breakdown"] == {"not_resolved": 33,
                               "person_requested_not_provided": 24,
                               "repeat_within_seven_days": 22}


def test_hang_up_is_contained_under_A_and_not_under_ours():
    c = contact(resolved=False, disposition="caller_ended")
    c["containment"] = D.score_all(c)
    assert c["containment"]["A_no_transfer"]["contained"] is True
    assert c["containment"]["ours_3_9_1"]["contained"] is False


def test_refused_request_for_a_person_is_contained_under_A_B_and_C():
    c = contact(resolved=False, requested=True, disposition="resolved")
    c["containment"] = D.score_all(c)
    for key in ("A_no_transfer", "B_no_human_handled", "C_self_service_completion"):
        assert c["containment"][key]["contained"] is True, key
    assert c["containment"]["ours_3_9_1"]["contained"] is False


def test_repeat_window_moves_the_answer():
    c = contact(resolved=True, repeat=True, hours=48)
    c["containment"] = D.score_all(c)
    assert c["containment"]["D_no_repeat_24h"]["contained"] is True
    assert c["containment"]["D_no_repeat_72h"]["contained"] is False
    assert c["containment"]["ours_3_9_1"]["contained"] is False


def test_correct_escalation_is_not_containment_under_any_definition_except_D():
    c = contact(resolved=True, transfer=True, human=True, disposition="transferred")
    c["containment"] = D.score_all(c)
    assert c["containment"]["A_no_transfer"]["contained"] is False
    assert c["containment"]["B_no_human_handled"]["contained"] is False
    assert c["containment"]["C_self_service_completion"]["contained"] is False
    assert c["containment"]["ours_3_9_1"]["contained"] is False
    assert c["containment"]["D_no_repeat_24h"]["contained"] is True
