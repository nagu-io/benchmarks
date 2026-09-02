#!/usr/bin/env python3
"""Select the 60-case human adjudication set, charter 5.9 and 5.11.

    python3 select.py --seed 20260902

Deterministic. Fifteen scenarios per domain, spread across the five tiers, chosen with a
seeded shuffle inside each stratum so that the selection cannot be tuned after a run.

The set is selected from scenarios, not from transcripts, because no run has happened. A
selected scenario becomes a labelling case the first time any system is run on it: the
labelling harness in label.py pulls that system's transcript into the sheet. The same 60
scenarios are used for every system, so judge agreement is measured on a fixed set rather
than on whichever contacts looked hard afterwards.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent

PER_DOMAIN_TIER = {"T1": 2, "T2": 5, "T3": 3, "T4": 3, "T5": 2}

COLUMNS = [
    "case_id", "scenario", "domain", "tier", "language", "channel",
    "intent_class", "escalation_required", "either_outcome_acceptable",
    "transcript_ref",
    "label_resolved", "label_escalation_required_met", "label_escalation_destination_ok",
    "label_unsupported_assertion", "label_unsupported_class", "label_handover_quality",
    "labeller_id", "label_date", "label_notes",
]

VALUES = {
    "label_resolved": "yes | no | ambiguous",
    "label_escalation_required_met": "yes | no | not_applicable",
    "label_escalation_destination_ok": "yes | no | not_applicable",
    "label_unsupported_assertion": "yes | no",
    "label_unsupported_class": "financial_or_entitlement | regulated_disclosure | "
                               "procedural | incidental | none",
    "label_handover_quality": "clean | adequate | poor | not_applicable",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--out", default=str(HERE / "adjudication-set.csv"))
    args = ap.parse_args()

    scenarios = [json.loads(l) for l in (DATASET / "scenarios.jsonl").open(encoding="utf-8")
                 if l.strip()]
    chosen = []
    for domain in sorted({s["domain"] for s in scenarios}):
        for tier, count in PER_DOMAIN_TIER.items():
            pool = sorted([s for s in scenarios
                           if s["domain"] == domain and s["tier"] == tier],
                          key=lambda s: s["id"])
            rng = random.Random(f"{args.seed}:{domain}:{tier}")
            rng.shuffle(pool)
            chosen.extend(pool[:count])
    chosen.sort(key=lambda s: s["id"])

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for i, s in enumerate(chosen, start=1):
            w.writerow([
                f"hc-adj-{i:03d}", s["id"], s["domain"], s["tier"],
                s["language"]["label"], s["channel"], s["intent"]["class"],
                "yes" if s["ground_truth"]["escalation_required"] else "no",
                "yes" if s["ground_truth"]["either_outcome_acceptable"] else "no",
                "not run",
                "", "", "", "", "", "", "", "", "",
            ])
    values_path = HERE / "label-values.json"
    values_path.write_text(json.dumps(VALUES, indent=2), encoding="utf-8")
    print(f"selected {len(chosen)} cases -> {args.out}")
    print("tier mix:", {t: sum(1 for s in chosen if s["tier"] == t)
                        for t in ("T1", "T2", "T3", "T4", "T5")})
    print("domain mix:", {d: sum(1 for s in chosen if s["domain"] == d)
                          for d in sorted({s["domain"] for s in chosen})})
    print("every label column is blank: judge agreement is unmeasured until a person "
          "fills them in")


if __name__ == "__main__":
    main()
