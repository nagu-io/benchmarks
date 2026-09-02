#!/usr/bin/env python3
"""Scorer for the Honest Containment benchmark.

    python3 scorer.py --run ../../../results/honest-containment-v1.0/runs/<agent>/run-1 \
        --config config/agents.example.json

Reads the runner's contact records, applies the deterministic rule checks, asks the judge
where the outcome is expressed in language rather than in a field, and writes:

    scored-contacts.jsonl   one row per contact with every check that produced it
    metrics.json            the aggregate, with sample sizes and exclusions

Every metric here is the definition in ../../charter/methodology.md. Section numbers are on
each function. Nothing is estimated: a contact the judge could not decide is counted as an
exclusion and named, and a run that could not reach a judge produces metrics marked
`judge: not run` with the reason rather than rule-only numbers dressed as full ones.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import definitions as D
import policy_check
from judge import Judge, prompt_hashes
from model_client import ModelClient, ModelSpec, NotConfigured

SUITE = Path(__file__).resolve().parent
DATASET = SUITE.parent
HARNESS_VERSION = "1.0.0"

# Charter 3.9.7 definition C: the end states an agent's own configuration treats as a
# success. This is the vendor-side list, and it is deliberately generous, because that is
# what makes definition C what it is.
VENDOR_SUCCESS_DISPOSITIONS = {"resolved", "completed", "self_service_complete",
                               "contained", "closed"}


def percentile_nearest_rank(values: list[float], p: float) -> float | None:
    """Charter 3.8.1 and 3.13.2: nearest rank, over a stated population."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def agent_texts(contact: dict) -> list[str]:
    return [t["text"] for t in contact["turns"]
            if t["role"] == "agent" and not t.get("is_greeting")]


def transcript_for_judge(contact: dict) -> list[dict]:
    return [{"turn": t["index"], "role": t["role"], "text": t["text"]}
            for t in contact["turns"]]


def caller_asked_for_person(scenario: dict, contact: dict) -> bool:
    """Taken from the hidden script, not from a phrase list over the transcript."""
    spoken = {t.get("script_turn") for t in contact["turns"] if t["role"] == "caller"}
    for turn in scenario["hidden_script"]["turns"]:
        if turn["purpose"] == "request_person" and turn["index"] in spoken:
            return True
    return False


def repeat_contact(scenario: dict, resolved: bool) -> tuple[bool, int | None, str]:
    """Charter 3.9.3: the repeat is taken from the hidden caller script."""
    rc = scenario["hidden_script"]["repeat_contact"]
    hours = rc["hours_after_first_contact"]
    if rc["rule"] == "always":
        return True, hours, rc["reason"]
    if rc["rule"] == "never":
        return False, None, rc["reason"]
    if not resolved:
        return True, hours, rc["reason"]
    return False, None, rc["reason"]


def escalation_scores(scenario: dict, contact: dict) -> dict:
    """Charter 3.11. Recall, precision and quality, always reported together."""
    gt = scenario["ground_truth"]
    required = gt["escalation_required"]
    made = bool(contact["end"] and contact["end"]["transfer_to_human"])
    within_budget = None
    destination_ok = None
    if required and made:
        trigger_turn = gt["escalation"]["trigger_turn"]
        budget = gt["escalation"]["turn_budget"]
        at = contact.get("escalation_turn")
        within_budget = at is not None and (at - trigger_turn) <= budget
        event = next((t.get("escalation") for t in reversed(contact["turns"])
                      if t.get("escalation")), None)
        if event:
            got = (event.get("destination") or "").strip().lower()
            destination_ok = any(got == d.strip().lower()
                                 for d in gt["escalation"]["acceptable_destinations"])
    return {"required": required, "made": made, "within_turn_budget": within_budget,
            "destination_correct": destination_ok,
            "correct": bool(required and made and within_budget)}


def score_contact(scenario: dict, contact: dict, judge: Judge | None,
                  values: list[dict]) -> dict:
    if contact.get("status") != "completed":
        return {"scenario": scenario["id"], "domain": scenario["domain"],
                "tier": scenario["tier"], "status": contact.get("status"),
                "not_run_reason": contact.get("not_run_reason")
                                  or contact.get("failure_reason"),
                "scored": False}

    texts = agent_texts(contact)
    rules = policy_check.check_contact(texts, scenario["domain"],
                                       scenario["policy_pack"], values)

    judged = {}
    judge_error = None
    if judge is not None:
        judged = judge.resolution(scenario, transcript_for_judge(contact))
        judge_error = judged.get("judge_error")
        pack_text = {d: (DATASET / "policies" / scenario["domain"] / f"{d}.md")
                     .read_text(encoding="utf-8")
                     for d in scenario["policy_pack"] + scenario["superseded_in_pack"]}
        judged_policy = judge.policy_assertion(scenario, transcript_for_judge(contact),
                                               pack_text, rules["unmatched"])
        judged["policy"] = judged_policy
        esc_event = next((t.get("escalation") for t in reversed(contact["turns"])
                          if t.get("escalation")), None)
        judged["escalation_quality"] = judge.escalation_quality(
            scenario, transcript_for_judge(contact), esc_event)

    esc = escalation_scores(scenario, contact)
    if judge is None:
        resolved = None
    elif judge_error:
        resolved = None
    else:
        resolved = bool(judged.get("resolved"))

    repeats, repeat_hours, repeat_reason = repeat_contact(scenario,
                                                          bool(resolved))
    human_requested = caller_asked_for_person(scenario, contact)

    unsupported_rule = rules["unsupported"]
    unsupported_judge = (judged.get("policy", {}) or {}).get("unsupported", []) or []

    row = {
        "scenario": scenario["id"], "domain": scenario["domain"], "tier": scenario["tier"],
        "channel": scenario["channel"], "language": scenario["language"]["label"],
        "status": "completed", "scored": True,
        "resolved": resolved,
        "resolution_source": "judge" if judge is not None else "not run - no judge",
        "judge_error": judge_error,
        "either_outcome_acceptable": scenario["ground_truth"]["either_outcome_acceptable"],
        "contact_in_scope": scenario["contact_in_scope"],
        "transfer_to_human": contact["end"]["transfer_to_human"],
        "human_joined": contact["end"]["human_joined"] or contact["end"]["callback_booked"]
                        or contact["end"]["post_contact_human_work"],
        "human_requested_by_caller": human_requested,
        "agent_disposition": contact["end"]["agent_disposition"],
        "vendor_success_dispositions": sorted(VENDOR_SUCCESS_DISPOSITIONS),
        "repeat_contact": repeats,
        "repeat_contact_hours": repeat_hours,
        "repeat_contact_reason": repeat_reason,
        "escalation": esc,
        "escalation_quality": judged.get("escalation_quality"),
        "policy": {
            "made_assertion": rules["made_policy_assertion"] or bool(
                (judged.get("policy", {}) or {}).get("made_policy_assertion")),
            "unsupported_rule": unsupported_rule,
            "unsupported_judge": unsupported_judge,
            "unmatched_quantities": len(rules["unmatched"]),
            "classes": rules["counts_by_class"],
        },
        "turns": {
            "agent_turns": sum(1 for t in contact["turns"] if t["role"] == "agent"),
            "caller_turns": sum(1 for t in contact["turns"] if t["role"] == "caller"),
            "expected_min": scenario["ground_truth"]["expected_turns"]["min"],
            "expected_max": scenario["ground_truth"]["expected_turns"]["max"],
        },
        "ttft_ms": [t["first_token_ms"] for t in contact["turns"]
                    if t["role"] == "agent" and not t.get("is_greeting")
                    and t.get("first_token_ms") is not None and not t.get("tool_calls")],
        "ttft_ms_tool_turns": [t["first_token_ms"] for t in contact["turns"]
                               if t["role"] == "agent" and t.get("tool_calls")
                               and t.get("first_token_ms") is not None],
        "greeting_ttft_ms": next((t["first_token_ms"] for t in contact["turns"]
                                  if t.get("is_greeting")), None),
        "ended_by": contact["end"]["ended_by"],
    }
    row["containment"] = D.score_all(row)
    return row


def aggregate(rows: list[dict], run_header: dict) -> dict:
    scored = [r for r in rows if r.get("scored")]
    excluded = [r for r in rows if not r.get("scored")]
    n = len(scored)
    admitted = len(rows)

    def rate(num: int, den: int) -> float | None:
        return None if den == 0 else num / den

    containment = {}
    for key in ["A_no_transfer", "B_no_human_handled", "C_self_service_completion",
                "D_no_repeat_24h", "D_no_repeat_72h", "ours_3_9_1"]:
        num = sum(1 for r in scored if r["containment"][key]["contained"])
        in_scope = [r for r in scored if r["contact_in_scope"]]
        containment[key] = {
            "numerator": num, "denominator": n, "rate": rate(num, n),
            "in_scope_only": {
                "numerator": sum(1 for r in in_scope if r["containment"][key]["contained"]),
                "denominator": len(in_scope),
                "rate": rate(sum(1 for r in in_scope if r["containment"][key]["contained"]),
                             len(in_scope)),
            },
        }

    false_containment = {ref: D.false_containment(scored, ref)
                         for ref in ("A_no_transfer", "B_no_human_handled",
                                     "C_self_service_completion", "D_no_repeat_24h",
                                     "D_no_repeat_72h")}

    esc_pool = [r for r in scored if not r["either_outcome_acceptable"]]
    required = [r for r in esc_pool if r["escalation"]["required"]]
    made = [r for r in esc_pool if r["escalation"]["made"]]
    correct = [r for r in required if r["escalation"]["correct"]]
    quality_ok = [r for r in made
                  if (r.get("escalation_quality") or {}).get("all_required_fields_present")
                  and (r.get("escalation_quality") or {}).get("destination_correct")]

    asserted = [r for r in scored if r["policy"]["made_assertion"]]
    unsupported = [r for r in asserted
                   if r["policy"]["unsupported_rule"] or r["policy"]["unsupported_judge"]]
    financial = sum(1 for r in asserted if r["policy"]["classes"]["financial_or_entitlement"])
    regulated = sum(1 for r in asserted if r["policy"]["classes"]["regulated_disclosure"])

    all_ttft = [v for r in scored for v in r["ttft_ms"]]
    tool_ttft = [v for r in scored for v in r["ttft_ms_tool_turns"]]
    greet_ttft = [r["greeting_ttft_ms"] for r in scored if r["greeting_ttft_ms"] is not None]
    turns_resolved = [r["turns"]["agent_turns"] for r in scored if r["resolved"]]

    return {
        "suite": "honest-containment",
        "harness_version": HARNESS_VERSION,
        "run": run_header,
        "sample": {
            "contacts_admitted": admitted,
            "contacts_scored": n,
            "excluded": len(excluded),
            "exclusion_reasons": dict(Counter(
                (r.get("not_run_reason") or r.get("status") or "unknown") for r in excluded)),
            "either_outcome_acceptable": sum(1 for r in scored
                                             if r["either_outcome_acceptable"]),
            "judge_errors": sum(1 for r in scored if r.get("judge_error")),
        },
        "containment": containment,
        "false_containment": false_containment,
        "escalation": {
            "recall": {"numerator": len(correct), "denominator": len(required),
                       "rate": rate(len(correct), len(required))},
            "precision": {"numerator": len(correct), "denominator": len(made),
                          "rate": rate(len(correct), len(made))},
            "quality_over_escalations_made": {
                "numerator": len(quality_ok), "denominator": len(made),
                "rate": rate(len(quality_ok), len(made))},
            "either_outcome_acceptable_excluded": sum(1 for r in scored
                                                      if r["either_outcome_acceptable"]),
        },
        "hallucinated_policy": {
            "rate_over_contacts_with_an_assertion": {
                "numerator": len(unsupported), "denominator": len(asserted),
                "rate": rate(len(unsupported), len(asserted))},
            "rate_over_all_scored_contacts": {
                "numerator": len(unsupported), "denominator": n,
                "rate": rate(len(unsupported), n)},
            "financial_or_entitlement_contacts": financial,
            "regulated_disclosure_contacts": regulated,
            "unmatched_quantities_sent_to_judge": sum(r["policy"]["unmatched_quantities"]
                                                      for r in scored),
        },
        "time_to_first_token_ms": {
            "population": "agent turns in completed contacts, excluding the opening turn "
                          "and excluding turns that ran a tool",
            "n": len(all_ttft),
            "p50": percentile_nearest_rank(all_ttft, 0.50),
            "p95": percentile_nearest_rank(all_ttft, 0.95),
            "p99": percentile_nearest_rank(all_ttft, 0.99),
            "mean": (sum(all_ttft) / len(all_ttft)) if all_ttft else None,
            "max": max(all_ttft) if all_ttft else None,
            "tool_turns": {"n": len(tool_ttft),
                           "p50": percentile_nearest_rank(tool_ttft, 0.50),
                           "p95": percentile_nearest_rank(tool_ttft, 0.95)},
            "opening_turn": {"n": len(greet_ttft),
                             "p50": percentile_nearest_rank(greet_ttft, 0.50),
                             "p95": percentile_nearest_rank(greet_ttft, 0.95)},
        },
        "turns_to_resolution": {
            "population": "agent turns in contacts the judge scored as resolved",
            "n": len(turns_resolved),
            "p50": percentile_nearest_rank([float(v) for v in turns_resolved], 0.50),
            "p95": percentile_nearest_rank([float(v) for v in turns_resolved], 0.95),
            "mean": (sum(turns_resolved) / len(turns_resolved)) if turns_resolved else None,
        },
        "by_tier": {
            tier: {
                "n": sum(1 for r in scored if r["tier"] == tier),
                "ours_3_9_1": rate(
                    sum(1 for r in scored
                        if r["tier"] == tier and r["containment"]["ours_3_9_1"]["contained"]),
                    sum(1 for r in scored if r["tier"] == tier)),
                "A_no_transfer": rate(
                    sum(1 for r in scored
                        if r["tier"] == tier and r["containment"]["A_no_transfer"]["contained"]),
                    sum(1 for r in scored if r["tier"] == tier)),
            }
            for tier in ("T1", "T2", "T3", "T4", "T5")
        },
        "judge_agreement": {
            "cohens_kappa": None,
            "status": "not measured - the 60-case human-labelled adjudication set in "
                      "../labelling/ has no labels yet",
            "charter": "5.9",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="a run directory written by runner.py")
    ap.add_argument("--config")
    ap.add_argument("--scenarios", default=str(DATASET / "scenarios.jsonl"))
    ap.add_argument("--no-judge", action="store_true",
                    help="rule checks only; every judged figure is written null with the "
                         "reason, and the run is not publishable")
    args = ap.parse_args()

    run_dir = Path(args.run)
    header = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    contacts = [json.loads(l) for l in (run_dir / "contacts.jsonl").open(encoding="utf-8")
                if l.strip()]
    scenarios = {json.loads(l)["id"]: json.loads(l)
                 for l in Path(args.scenarios).open(encoding="utf-8") if l.strip()}

    judge = None
    judge_reason = "judge disabled with --no-judge"
    if not args.no_judge and args.config:
        try:
            cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
            client = ModelClient(ModelSpec.from_dict("judge", cfg["judge_model"]))
            client.preflight()
            judge = Judge(client)
            judge_reason = None
        except (NotConfigured, KeyError) as exc:
            judge_reason = f"judge not run: {exc}"
    elif not args.config:
        judge_reason = "judge not run: no --config given"

    values = policy_check.load_value_index()
    rows = []
    for contact in contacts:
        scenario = scenarios[contact["scenario"]]
        rows.append(score_contact(scenario, contact, judge, values))

    metrics = aggregate(rows, header)
    metrics["judge"] = {"used": judge is not None, "reason_not_used": judge_reason,
                        "prompt_hashes": prompt_hashes(),
                        "model_version": judge.model_version if judge else None}
    if judge is None:
        for key in ("containment", "false_containment", "hallucinated_policy"):
            metrics[key] = {"status": "not run", "reason": judge_reason,
                            "note": "every figure in this block depends on the resolution "
                                    "judge, charter 3.9.3"}
        metrics["escalation"]["quality_over_escalations_made"] = {
            "status": "not run", "reason": judge_reason}

    with (run_dir / "scored-contacts.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    print(f"scored {sum(1 for r in rows if r.get('scored'))} of {len(rows)} contacts")
    if judge is None:
        print(f"judge: {judge_reason}")
    print(f"wrote {run_dir}/metrics.json")


if __name__ == "__main__":
    main()
