#!/usr/bin/env python3
"""Structural ceilings: what each containment definition can reach on this dataset.

    python3 ceilings.py

This is arithmetic over the ground truth, not a measurement. It answers a question a
reader asks before any system is run: if an agent did everything the policy pack requires,
what would each definition say about it? The five answers differ, and they differ before
any agent has spoken. That difference is the point of the suite.

The assumed agent resolves every resolvable contact, escalates exactly when the ground
truth requires it, quotes only what the pack supports, and never refuses a request for a
person. No such agent has been run. This is a property of the dataset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import definitions as D

DATASET = Path(__file__).resolve().parent.parent


def perfect_contact(scenario: dict) -> dict:
    """The scored row a policy-perfect agent would produce for this scenario."""
    gt = scenario["ground_truth"]
    escalates = gt["escalation_required"]
    rc = scenario["hidden_script"]["repeat_contact"]
    repeats = rc["rule"] == "always"
    hours = rc["hours_after_first_contact"] if repeats else None
    asked_for_person = any(t["purpose"] == "request_person"
                           for t in scenario["hidden_script"]["turns"])
    return {
        "scenario": scenario["id"], "tier": scenario["tier"], "domain": scenario["domain"],
        "contact_in_scope": scenario["contact_in_scope"],
        "resolved": True,
        "transfer_to_human": escalates,
        "human_joined": escalates,
        "human_requested_by_caller": asked_for_person,
        "agent_disposition": "transferred" if escalates else "resolved",
        "vendor_success_dispositions": ["resolved", "completed", "self_service_complete",
                                        "contained", "closed"],
        "repeat_contact": repeats,
        "repeat_contact_hours": hours,
        "either_outcome_acceptable": gt["either_outcome_acceptable"],
    }


def main() -> None:
    scenarios = [json.loads(l) for l in (DATASET / "scenarios.jsonl").open(encoding="utf-8")
                 if l.strip()]
    rows = []
    for s in scenarios:
        row = perfect_contact(s)
        row["containment"] = D.score_all(row)
        rows.append(row)
    n = len(rows)
    keys = ["A_no_transfer", "B_no_human_handled", "C_self_service_completion",
            "D_no_repeat_24h", "D_no_repeat_72h", "A_and_D_no_repeat_72h", "ours_3_9_1"]
    out = {
        "dataset_version": json.loads((DATASET / "manifest.json").read_text())["dataset_version"],
        "contacts": n,
        "assumption": "an agent that follows every policy in the pack, escalates exactly "
                      "when the ground truth requires it, and asserts nothing the pack does "
                      "not support",
        "not_a_result": "No system has been run. These are properties of the dataset, "
                        "computed from the ground truth.",
        "ceilings": {},
        "false_containment_at_the_ceiling": {},
    }
    for key in keys:
        num = sum(1 for r in rows if r["containment"][key]["contained"])
        out["ceilings"][key] = {"contained": num, "of": n, "share": round(num / n, 4)}
    for ref in keys[:-1]:
        out["false_containment_at_the_ceiling"][ref] = D.false_containment(rows, ref)
    print(json.dumps(out, indent=2))
    (DATASET / "structural-ceilings.json").write_text(json.dumps(out, indent=2),
                                                      encoding="utf-8")


if __name__ == "__main__":
    main()
