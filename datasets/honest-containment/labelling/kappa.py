#!/usr/bin/env python3
"""Cohen's kappa between two label sets, charter 5.9 and 5.11.

    python3 kappa.py --a labels-A.csv --b labels-B.csv               # labeller agreement
    python3 kappa.py --a labels-A.csv --judge <run dir>              # judge agreement

Runs the moment labels exist and refuses before that, with a non-zero exit and a message
naming how many rows are blank. It never returns a figure computed on a partial set
without saying so on the same line.

Kappa = (observed agreement − expected agreement) / (1 − expected agreement), on the label
values in label-values.json, per dimension, with the confusion counts printed beside it so
a reader can see what the number is made of.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

DIMENSIONS = ["label_resolved", "label_escalation_required_met",
              "label_escalation_destination_ok", "label_unsupported_assertion",
              "label_unsupported_class", "label_handover_quality"]

# How a judge verdict maps onto a human label, so the two are comparable.
JUDGE_MAP = {
    "label_resolved": lambda r: ("yes" if r.get("resolved") else
                                 "ambiguous" if r.get("resolved") is None else "no"),
    "label_escalation_required_met": lambda r: (
        "not_applicable" if not r["escalation"]["required"]
        else "yes" if r["escalation"]["correct"] else "no"),
    "label_escalation_destination_ok": lambda r: (
        "not_applicable" if not r["escalation"]["made"]
        else "yes" if r["escalation"]["destination_correct"] else "no"),
    "label_unsupported_assertion": lambda r: (
        "yes" if (r["policy"]["unsupported_rule"] or r["policy"]["unsupported_judge"])
        else "no"),
    "label_unsupported_class": lambda r: next(
        (c for c in ("financial_or_entitlement", "regulated_disclosure", "procedural")
         if r["policy"]["classes"].get(c)), "none"),
    "label_handover_quality": lambda r: (
        (r.get("escalation_quality") or {}).get("handover_quality") or "not_applicable"),
}


def cohens_kappa(pairs: list[tuple[str, str]]) -> tuple[float | None, dict]:
    n = len(pairs)
    if n == 0:
        return None, {}
    observed = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    categories = set(ca) | set(cb)
    expected = sum((ca[c] / n) * (cb[c] / n) for c in categories)
    if expected == 1.0:
        return None, {"note": "every rater used one category; kappa is undefined"}
    kappa = (observed - expected) / (1 - expected)
    return kappa, {"n": n, "observed_agreement": round(observed, 4),
                   "expected_agreement": round(expected, 4),
                   "confusion": dict(Counter(f"{a}|{b}" for a, b in pairs))}


def read_labels(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["case_id"]: r for r in csv.DictReader(fh)}


def judge_labels(run_dir: Path, cases: dict) -> dict:
    scored = {}
    path = run_dir / "scored-contacts.jsonl"
    if not path.exists():
        raise SystemExit(f"no scored contacts at {path}; run scorer.py first")
    rows = {json.loads(l)["scenario"]: json.loads(l)
            for l in path.open(encoding="utf-8") if l.strip()}
    for case_id, case in cases.items():
        r = rows.get(case["scenario"])
        if not r or not r.get("scored"):
            continue
        scored[case_id] = {d: JUDGE_MAP[d](r) for d in DIMENSIONS}
    return scored


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b")
    ap.add_argument("--judge", help="a run directory scored by scorer.py")
    ap.add_argument("--out", default=str(HERE / "judge-agreement.json"))
    args = ap.parse_args()
    if not args.b and not args.judge:
        raise SystemExit("give --b for labeller agreement or --judge for judge agreement")

    a = read_labels(Path(args.a))
    blank = [k for k, v in a.items() if not v.get("label_resolved")]
    if blank:
        print(f"{len(blank)} of {len(a)} cases in {args.a} have no label.")
        print("Cohen's kappa is not computed on a partial set. Judge agreement is "
              "unmeasured until every case is labelled, and every table that depends on "
              "the judge says so (charter 5.9).")
        raise SystemExit(2)

    b = read_labels(Path(args.b)) if args.b else judge_labels(Path(args.judge), a)
    label_b = "labeller B" if args.b else "judge"

    result = {"a": args.a, "b": args.b or args.judge, "comparison": label_b,
              "dimensions": {}}
    for dim in DIMENSIONS:
        pairs = [(a[k][dim], b[k][dim] if args.b else b[k][dim])
                 for k in a if k in b and a[k][dim]]
        kappa, detail = cohens_kappa(pairs)
        result["dimensions"][dim] = {"cohens_kappa": None if kappa is None else round(kappa, 4),
                                     **detail}
        threshold = "" if kappa is None else (" (below the 0.8 the charter asks for)"
                                              if kappa < 0.8 else "")
        print(f"{dim:38s} kappa {kappa if kappa is None else round(kappa, 3)}"
              f" n={detail.get('n')}{threshold}")
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
