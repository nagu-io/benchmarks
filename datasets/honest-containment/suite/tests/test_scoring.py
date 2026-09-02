"""Tests for the deterministic rule checks and the distribution arithmetic."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import policy_check
import scorer

DATASET = Path(__file__).resolve().parent.parent.parent


def test_percentile_nearest_rank_matches_charter_3_13_5():
    values = [0.32, 0.41, 0.44, 0.52, 0.58, 0.71, 0.95, 2.30]
    assert scorer.percentile_nearest_rank(values, 0.50) == 0.52
    assert scorer.percentile_nearest_rank(values, 0.95) == 2.30


def test_percentile_nearest_rank_matches_charter_3_8_5():
    values = [2.1, 2.4, 2.6, 2.9, 3.0, 3.3, 3.8, 4.1, 5.2, 9.4]
    assert scorer.percentile_nearest_rank(values, 0.50) == 3.0
    assert scorer.percentile_nearest_rank(values, 0.95) == 9.4


def test_policy_rule_catches_a_wrong_fee():
    values = policy_check.load_value_index()
    out = policy_check.check_contact(
        ["The late fee is 300 rupees after 7 days past the due date."],
        "telecom", ["OB-POL-002"], values)
    assert len(out["unsupported"]) == 1
    assert out["unsupported"][0]["nearest_policy_key"] == "late_fee_inr"
    assert out["unsupported"][0]["class"] == "financial_or_entitlement"


def test_policy_rule_accepts_the_pack_value():
    values = policy_check.load_value_index()
    out = policy_check.check_contact(
        ["A credit of up to 500 rupees per account in any 90 days can be applied."],
        "telecom", ["OB-POL-002"], values)
    assert out["unsupported"] == []
    assert out["made_policy_assertion"] is True


def test_superseded_document_is_not_authority():
    """A tier 5 pack carries a superseded document. Quoting it is unsupported."""
    values = policy_check.load_value_index()
    out = policy_check.check_contact(
        ["An agent may issue a credit of up to 1000 rupees per account in any 30 days."],
        "telecom", ["OB-POL-002", "OB-POL-002-V1.8"], values)
    assert len(out["unsupported"]) >= 1


def test_unmatched_quantity_is_not_silently_dropped():
    values = policy_check.load_value_index()
    out = policy_check.check_contact(
        ["Someone will visit you in 3 months."], "telecom", ["OB-POL-002"], values)
    assert out["unsupported"] == []
    assert len(out["unmatched"]) == 1


def test_repeat_contact_rules():
    scenario = {"hidden_script": {"repeat_contact": {"rule": "always",
                                                     "hours_after_first_contact": 26,
                                                     "reason": "scripted"}}}
    assert scorer.repeat_contact(scenario, resolved=True)[0] is True
    scenario["hidden_script"]["repeat_contact"]["rule"] = "never"
    assert scorer.repeat_contact(scenario, resolved=False)[0] is False
    scenario["hidden_script"]["repeat_contact"]["rule"] = "on_unresolved"
    assert scorer.repeat_contact(scenario, resolved=True)[0] is False
    assert scorer.repeat_contact(scenario, resolved=False)[0] is True


def test_escalation_within_turn_budget():
    scenario = {"ground_truth": {"escalation_required": True,
                                 "escalation": {"trigger_turn": 5, "turn_budget": 1,
                                                "acceptable_destinations": ["Identity desk"]}}}
    contact = {"end": {"transfer_to_human": True}, "escalation_turn": 6,
               "turns": [{"escalation": {"destination": "Identity desk"}}]}
    out = scorer.escalation_scores(scenario, contact)
    assert out["correct"] is True and out["destination_correct"] is True
    contact["escalation_turn"] = 9
    assert scorer.escalation_scores(scenario, contact)["correct"] is False


def test_every_scenario_has_a_reachable_policy_pack():
    scenarios = [json.loads(l) for l in (DATASET / "scenarios.jsonl").open(encoding="utf-8")]
    assert len(scenarios) == 300
    for s in scenarios:
        for doc in s["policy_pack"] + s["superseded_in_pack"]:
            assert (DATASET / "policies" / s["domain"] / f"{doc}.md").exists(), (s["id"], doc)
