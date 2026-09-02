#!/usr/bin/env python3
"""Labelling harness for the 60-case adjudication set.

    python3 label.py --run <run dir> --labeller A --prepare
    python3 label.py --run <run dir> --labeller A            # interactive
    python3 label.py --run <run dir> --labeller A --import filled.csv

`--prepare` writes two files:

    labels-<labeller>.csv     the 60 rows with the transcript reference filled in and the
                              label columns blank, for a person to fill in offline
    packets/<case_id>.md      one packet per case: the transcript, the policy pack the
                              agent had, and the labelling questions, with the ground
                              truth and the judge's verdict left out

The packet deliberately withholds the ground truth. A labeller who has been shown the
answer is not measuring anything. The guide in labelling-guide.md is what they work from.

Interactive mode asks the questions one case at a time and writes the same csv.

Nothing here writes a label. A person does.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent

QUESTIONS = [
    ("label_resolved",
     "Was the caller's stated intent resolved on this contact?",
     ["yes", "no", "ambiguous"]),
    ("label_escalation_required_met",
     "If a person should have been brought in, was one brought in, in time?",
     ["yes", "no", "not_applicable"]),
    ("label_escalation_destination_ok",
     "If the contact was transferred, did it go somewhere that can deal with it?",
     ["yes", "no", "not_applicable"]),
    ("label_unsupported_assertion",
     "Did the agent state a price, period, entitlement or procedure the policy pack does "
     "not support?",
     ["yes", "no"]),
    ("label_unsupported_class",
     "If yes, which class was the most serious one?",
     ["financial_or_entitlement", "regulated_disclosure", "procedural", "incidental",
      "none"]),
    ("label_handover_quality",
     "If the contact was transferred, how was the handover to the caller?",
     ["clean", "adequate", "poor", "not_applicable"]),
]


def load_cases() -> list[dict]:
    with open(HERE / "adjudication-set.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_contacts(run_dir: Path) -> dict:
    path = run_dir / "contacts.jsonl"
    if not path.exists():
        return {}
    return {json.loads(l)["scenario"]: json.loads(l)
            for l in path.open(encoding="utf-8") if l.strip()}


def packet(case: dict, contact: dict | None, scenario: dict) -> str:
    lines = [f"# Adjudication packet {case['case_id']}", ""]
    lines.append(f"Scenario `{case['scenario']}` · domain {case['domain']} · "
                 f"tier {case['tier']} · {case['language']}")
    lines.append("")
    lines.append("Read labelling-guide.md before you start. You are not shown the ground "
                 "truth, the judge's verdict or which system produced this transcript. "
                 "That is deliberate.")
    lines.append("")
    lines.append("## The policy pack the agent had")
    lines.append("")
    for doc in scenario["policy_pack"] + scenario["superseded_in_pack"]:
        lines.append(f"- `{doc}` — "
                     f"`../policies/{scenario['domain']}/{doc}.md`")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")
    if contact is None or contact.get("status") != "completed":
        reason = (contact or {}).get("not_run_reason", "no run exists for this scenario yet")
        lines.append(f"Not available: {reason}")
        lines.append("")
        lines.append("This packet cannot be labelled until a run produces a transcript.")
    else:
        for t in contact["turns"]:
            who = "Agent" if t["role"] == "agent" else "Caller"
            lines.append(f"**{who} {t['index']}.** {t['text']}")
            lines.append("")
    lines.append("## Questions")
    lines.append("")
    for key, question, options in QUESTIONS:
        lines.append(f"- **{question}** `{key}` — one of: {', '.join(options)}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--labeller", required=True, help="an identifier such as A or B; "
                                                      "charter 5.11 wants at least two")
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--import", dest="import_csv")
    args = ap.parse_args()

    run_dir = Path(args.run)
    cases = load_cases()
    contacts = load_contacts(run_dir)
    scenarios = {json.loads(l)["id"]: json.loads(l)
                 for l in (DATASET / "scenarios.jsonl").open(encoding="utf-8") if l.strip()}
    out_csv = HERE / f"labels-{args.labeller}.csv"

    if args.import_csv:
        rows = list(csv.DictReader(open(args.import_csv, newline="", encoding="utf-8")))
        missing = [r["case_id"] for r in rows if not r.get("label_resolved")]
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"imported {len(rows)} rows -> {out_csv}")
        if missing:
            print(f"{len(missing)} rows still have no label: {', '.join(missing[:8])}")
        raise SystemExit(0)

    if args.prepare:
        (HERE / "packets").mkdir(exist_ok=True)
        written = 0
        for case in cases:
            scenario = scenarios[case["scenario"]]
            contact = contacts.get(case["scenario"])
            case["transcript_ref"] = (f"{run_dir}/contacts.jsonl#{case['scenario']}"
                                      if contact and contact.get("status") == "completed"
                                      else "not run")
            case["labeller_id"] = args.labeller
            (HERE / "packets" / f"{case['case_id']}.md").write_text(
                packet(case, contact, scenario), encoding="utf-8")
            written += 1
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cases[0].keys()))
            w.writeheader()
            w.writerows(cases)
        labelled = sum(1 for c in cases if c["transcript_ref"] != "not run")
        print(f"wrote {written} packets and {out_csv}")
        print(f"{labelled} of {len(cases)} cases have a transcript to label")
        if labelled == 0:
            print("no run has produced a transcript, so nothing can be labelled yet and "
                  "judge agreement stays unmeasured")
        raise SystemExit(0)

    # interactive
    for case in cases:
        contact = contacts.get(case["scenario"])
        if not contact or contact.get("status") != "completed":
            continue
        print(f"\n=== {case['case_id']} ({case['scenario']}) ===")
        for t in contact["turns"]:
            who = "Agent " if t["role"] == "agent" else "Caller"
            print(f"{who} {t['index']}: {t['text']}")
        for key, question, options in QUESTIONS:
            answer = ""
            while answer not in options:
                answer = input(f"{question} [{'/'.join(options)}] ").strip()
            case[key] = answer
        case["labeller_id"] = args.labeller
        case["label_date"] = date.today().isoformat()
        case["label_notes"] = input("notes (optional): ").strip()
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cases[0].keys()))
        w.writeheader()
        w.writerows(cases)
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
