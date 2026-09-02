#!/usr/bin/env python3
"""Build the Honest Containment report tables from whatever runs exist.

    python3 report.py --results ../../../results/honest-containment-v1.0 --write

Writes leaderboard.md, definitions-spread.md and results.csv. A system with no scored run
gets a row reading `not run` and the reason, in every column. Nothing is estimated,
interpolated or illustrated (charter 3.1.8).

The prose at the top of each generated file is in this script, so the report is rebuilt by
a command rather than edited by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

import definitions as D

SUITE = Path(__file__).resolve().parent
DATASET = SUITE.parent

SYSTEM_ORDER = ["voice-platform-a", "voice-platform-b", "general-llm", "entailment-agent"]

METRIC_COLUMNS = [
    ("ours_3_9_1", "containment, charter 3.9.1"),
    ("A_no_transfer", "A no transfer"),
    ("B_no_human_handled", "B no human handled"),
    ("C_self_service_completion", "C self-service end state"),
    ("D_no_repeat_24h", "D no repeat, 24 h"),
    ("D_no_repeat_72h", "D no repeat, 72 h"),
    ("A_and_D_no_repeat_72h", "A and D, no transfer and no repeat"),
]


def pct(block) -> str:
    if not isinstance(block, dict) or block.get("rate") is None:
        return "not run"
    return f"{block['rate'] * 100:.1f} ({block['numerator']}/{block['denominator']})"


def find_runs(results: Path) -> dict:
    out: dict[str, list[dict]] = {}
    runs_dir = results / "runs"
    if not runs_dir.exists():
        return out
    for system_dir in sorted(runs_dir.iterdir()):
        if not system_dir.is_dir():
            continue
        for run_dir in sorted(system_dir.glob("run-*")):
            header_path, metrics_path = run_dir / "run.json", run_dir / "metrics.json"
            if not header_path.exists():
                continue
            header = json.loads(header_path.read_text(encoding="utf-8"))
            metrics = (json.loads(metrics_path.read_text(encoding="utf-8"))
                       if metrics_path.exists() else None)
            out.setdefault(system_dir.name, []).append({"header": header, "metrics": metrics,
                                                        "dir": str(run_dir)})
    return out


def system_row(name: str, runs: list[dict], config: dict) -> dict:
    display = (config.get("agents", {}).get(name, {}) or {}).get("display_name", name)
    usable = [r for r in runs
              if r["metrics"] and r["header"].get("status") == "completed"
              and r["header"].get("publishable", True)]
    if not usable:
        reason = "not run"
        if runs:
            reason = runs[0]["header"].get("not_run_reason") or "not run"
        elif not runs:
            reason = "not run - no run directory"
        return {"system": name, "display_name": display, "runs": len(usable),
                "status": "not run", "reason": reason}
    return {"system": name, "display_name": display, "runs": len(usable),
            "status": "completed", "metrics": usable}


def leaderboard_md(rows: list[dict], meta: dict) -> str:
    out = []
    a = out.append
    a("# Honest Containment leaderboard")
    a("")
    a(f"Suite `honest-containment` · dataset version {meta['dataset_version']} · "
      f"harness version {meta['harness_version']} · built {meta['built']}")
    a("")
    a("Every figure in this table is produced by a run. No run has happened, so every "
      "figure reads `not run` with its reason. Charter section 3.1.8 governs this file: a "
      "row with no run is never estimated, extrapolated, illustrated or filled with a "
      "plausible-looking figure.")
    a("")
    a("The definitions behind every column are in `definitions-spread.md` and in "
      "`../../charter/methodology.md` sections 3.9 to 3.13. A rate is meaningless without "
      "its denominator, so each cell carries one once a run exists.")
    a("")
    a("## Containment, five definitions")
    a("")
    a("Sorted on containment under charter 3.9.1. Our own system sits where the sort puts "
      "it, charter 5.6.")
    a("")
    header = ["system", "runs"] + [label for _, label in METRIC_COLUMNS] + ["spread"]
    a("| " + " | ".join(header) + " |")
    a("|" + "---|" * len(header))
    for r in rows:
        if r["status"] != "completed":
            a("| " + " | ".join([r["display_name"], "0"]
                                + ["not run"] * len(METRIC_COLUMNS) + ["not run"]) + " |")
        else:
            cells = [r["display_name"], str(r["runs"])]
            for key, _ in METRIC_COLUMNS:
                cells.append(pct(r["metrics"][0]["metrics"]["containment"].get(key, {})))
            cells.append("see definitions-spread.md")
            a("| " + " | ".join(cells) + " |")
    a("")
    a("`spread` is the distance between the highest of the four common definitions and "
      "ours, in percentage points, for the same contacts. It is the column this suite "
      "exists for.")
    a("")
    a("### Why each row reads not run")
    a("")
    a("| system | reason |")
    a("|---|---|")
    for r in rows:
        if r["status"] != "completed":
            a(f"| {r['display_name']} | {r['reason']} |")
    a("")
    a("## False containment, escalation, policy, latency")
    a("")
    cols = ["system", "false containment vs B", "escalation recall", "escalation precision",
            "escalation quality", "hallucinated policy", "financial class",
            "time to first token p50 ms", "p95 ms", "turns to resolution p50"]
    a("| " + " | ".join(cols) + " |")
    a("|" + "---|" * len(cols))
    for r in rows:
        if r["status"] != "completed":
            a("| " + " | ".join([r["display_name"]] + ["not run"] * (len(cols) - 1)) + " |")
        else:
            m = r["metrics"][0]["metrics"]
            fc = m["false_containment"].get("B_no_human_handled", {})
            esc, hp = m["escalation"], m["hallucinated_policy"]
            ttft = m["time_to_first_token_ms"]
            a("| " + " | ".join([
                r["display_name"],
                "not run" if fc.get("rate") is None else f"{fc['rate']*100:.1f}",
                pct(esc["recall"]), pct(esc["precision"]),
                pct(esc.get("quality_over_escalations_made", {})),
                pct(hp["rate_over_contacts_with_an_assertion"]),
                str(hp["financial_or_entitlement_contacts"]),
                str(ttft["p50"]), str(ttft["p95"]),
                str(m["turns_to_resolution"]["p50"])]) + " |")
    a("")
    a("## What is missing before this table carries figures")
    a("")
    a("| Item | Who supplies it |")
    a("|---|---|")
    a("| An interface key per system under test, per the environment variables in "
      "`suite/config/agents.example.json` | a person |")
    a("| A spend cap set with each provider before the run | a person |")
    a("| The API base and response paths for each voice platform, from its current "
      "documentation, with the documentation date | a person |")
    a("| A decision on which model versions are in scope | a person |")
    a("| A judge model that is not one of the models under test, charter 5.9 | a person |")
    a("| 60 labelled adjudication cases, so that judge agreement can be reported | two "
      "labellers, following `datasets/honest-containment/labelling/labelling-guide.md` |")
    a("")
    a("## Judge agreement")
    a("")
    a("Unmeasured. The 60-case adjudication set is selected and the kappa computation is "
      "written, and neither can produce a figure until a run has produced transcripts and "
      "two people have labelled them. Charter section 5.9 requires the caveat on every "
      "table that depends on the judge, and it applies to every containment, false "
      "containment and hallucinated-policy figure this suite will publish.")
    a("")
    return "\n".join(out) + "\n"


def definitions_md(rows: list[dict], meta: dict, ceilings: dict) -> str:
    out = []
    a = out.append
    a("# Containment, five definitions, and the spread between them")
    a("")
    a(f"Dataset version {meta['dataset_version']} · built {meta['built']}")
    a("")
    a("Four of these five definitions are in common use across the contact-centre and "
      "voice-agent industry. They are conventions rather than any one company's property, "
      "and none of them is attributed here to a named vendor. The fifth is ours, charter "
      "section 3.9.1.")
    a("")
    a("## The five, stated precisely")
    a("")
    for d in D.DEFINITIONS:
        letter = d.key.split("_")[0]
        label = "Ours" if letter == "ours" else f"Definition {letter}"
        a(f"### {label} — {d.name}")
        a("")
        a(f"Key in the record: `{d.key}`.")
        a("")
        a(d.statement)
        a("")
        if d.counts_that_ours_does_not != "—":
            a(f"Counts as a success what ours does not: {d.counts_that_ours_does_not}.")
            a("")
    a("### Phrasings in common use, and which definition each one is")
    a("")
    a("A supplier rarely names a definition. It uses one of these phrasings. The third "
      "column says what the phrasing tests.")
    a("")
    a("| Phrasing | Definition | Note |")
    a("|---|---|---|")
    for phrase, key, note in D.COMMON_PHRASINGS:
        a(f"| {phrase} | `{key}` | {note} |")
    a("")
    a("Two properties of the set worth stating before any figure exists. Definition D does "
      "not test resolution at all, so a contact correctly transferred to a person counts as "
      "contained under D. Definitions A, B and C do not test repeat contact, so a contact "
      "the caller has to raise again the next day counts as contained under all three.")
    a("")
    a("## Spread per system")
    a("")
    a("The spread is the distance in percentage points between the highest of the four "
      "common definitions and ours, over the same contacts. It is not an error rate. It is "
      "the amount by which the answer changes when only the definition changes.")
    a("")
    cols = ["system"] + [label for _, label in METRIC_COLUMNS] + ["spread, points"]
    a("| " + " | ".join(cols) + " |")
    a("|" + "---|" * len(cols))
    for r in rows:
        if r["status"] != "completed":
            a("| " + " | ".join([r["display_name"]] + ["not run"] * (len(cols) - 1)) + " |")
        else:
            m = r["metrics"][0]["metrics"]["containment"]
            vals = {k: m.get(k, {}).get("rate") for k, _ in METRIC_COLUMNS}
            common = [v for k, v in vals.items() if k != "ours_3_9_1" and v is not None]
            spread = (max(common) - vals["ours_3_9_1"]) * 100 if common and vals["ours_3_9_1"] \
                is not None else None
            a("| " + " | ".join([r["display_name"]]
                                + [pct(m.get(k, {})) for k, _ in METRIC_COLUMNS]
                                + ["not run" if spread is None else f"{spread:.1f}"]) + " |")
    a("")
    a("## False containment against each reference")
    a("")
    a("Charter 3.10. Always against a named reference, with the breakdown by which of the "
      "three conditions failed, because the three cost a BPO different amounts.")
    a("")
    cols = ["system", "reference", "false containment", "not resolved",
            "person requested, not provided", "repeat within seven days"]
    a("| " + " | ".join(cols) + " |")
    a("|" + "---|" * len(cols))
    for r in rows:
        for ref in ("A_no_transfer", "B_no_human_handled", "C_self_service_completion",
                    "D_no_repeat_72h"):
            if r["status"] != "completed":
                a("| " + " | ".join([r["display_name"], ref] + ["not run"] * 4) + " |")
            else:
                fc = r["metrics"][0]["metrics"]["false_containment"].get(ref, {})
                b = fc.get("breakdown", {})
                a("| " + " | ".join([
                    r["display_name"], ref,
                    "not run" if fc.get("rate") is None else f"{fc['rate']*100:.1f}",
                    str(b.get("not_resolved", "not run")),
                    str(b.get("person_requested_not_provided", "not run")),
                    str(b.get("repeat_within_seven_days", "not run"))]) + " |")
    a("")
    a("## What the dataset alone already says")
    a("")
    a("The table below is not a result and no system produced it. It is arithmetic over the "
      "ground truth: the highest containment each definition could reach on these 300 "
      "contacts if an agent followed every policy in every pack, escalated exactly when the "
      "ground truth requires it, and asserted nothing the pack does not support. It is "
      "computed by `suite/ceilings.py` and it exists because the definitions already "
      "disagree before any agent speaks.")
    a("")
    a("| Definition | Contacts contained | Of | Share |")
    a("|---|---|---|---|")
    for key, label in METRIC_COLUMNS:
        c = ceilings["ceilings"][key]
        a(f"| {label} | {c['contained']} | {c['of']} | {c['share'] * 100:.1f} percent |")
    a("")
    a(f"Read the row for definition D at 24 hours against the row for ours. On this "
      f"dataset a policy-perfect agent is contained on "
      f"{ceilings['ceilings']['D_no_repeat_24h']['share'] * 100:.1f} percent of contacts "
      f"under definition D at 24 hours and on "
      f"{ceilings['ceilings']['ours_3_9_1']['share'] * 100:.1f} percent under ours. The "
      f"agent is the same agent. The contacts are the same contacts. Only the definition "
      f"moved.")
    a("")
    a(f"The reason is in the construction: "
      f"{ceilings['contacts'] - ceilings['ceilings']['A_no_transfer']['contained']} of the "
      f"{ceilings['contacts']} contacts require a person under the policy packs, and a "
      f"correct transfer is not containment under our definition or under A, B or C, while "
      f"it is containment under D. See `why-90-percent-is-65.md` for the same point worked "
      f"through from the definitions alone.")
    a("")
    return "\n".join(out) + "\n"


def results_csv(rows: list[dict], meta: dict) -> list[list[str]]:
    header = ["system", "display_name", "dataset_version", "harness_version", "runs",
              "status", "reason"] + [k for k, _ in METRIC_COLUMNS] + [
              "false_containment_vs_B", "escalation_recall", "escalation_precision",
              "escalation_quality", "hallucinated_policy_rate",
              "hallucinated_policy_financial_contacts", "ttft_p50_ms", "ttft_p95_ms",
              "turns_to_resolution_p50", "judge_agreement_kappa"]
    lines = [header]
    for r in rows:
        if r["status"] != "completed":
            lines.append([r["system"], r["display_name"], meta["dataset_version"],
                          meta["harness_version"], "0", "not run", r["reason"]]
                         + ["not run"] * (len(header) - 7))
        else:
            m = r["metrics"][0]["metrics"]
            c = m["containment"]
            fc = m["false_containment"].get("B_no_human_handled", {})
            lines.append([r["system"], r["display_name"], meta["dataset_version"],
                          meta["harness_version"], str(r["runs"]), "completed", ""]
                         + [str(c.get(k, {}).get("rate")) for k, _ in METRIC_COLUMNS]
                         + [str(fc.get("rate")), str(m["escalation"]["recall"]["rate"]),
                            str(m["escalation"]["precision"]["rate"]),
                            str(m["escalation"].get("quality_over_escalations_made", {})
                                .get("rate")),
                            str(m["hallucinated_policy"]
                                ["rate_over_contacts_with_an_assertion"]["rate"]),
                            str(m["hallucinated_policy"]["financial_or_entitlement_contacts"]),
                            str(m["time_to_first_token_ms"]["p50"]),
                            str(m["time_to_first_token_ms"]["p95"]),
                            str(m["turns_to_resolution"]["p50"]),
                            str(m["judge_agreement"]["cohens_kappa"])])
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True)
    ap.add_argument("--config", default=str(SUITE / "config" / "agents.example.json"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    results = Path(args.results)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    ceilings_path = DATASET / "structural-ceilings.json"
    if not ceilings_path.exists():
        raise SystemExit("run suite/ceilings.py first")
    ceilings = json.loads(ceilings_path.read_text(encoding="utf-8"))

    runs = find_runs(results)
    rows = [system_row(name, runs.get(name, []), config) for name in SYSTEM_ORDER]
    meta = {"dataset_version": manifest["dataset_version"], "harness_version": "1.0.0",
            "built": date.today().isoformat()}

    lb = leaderboard_md(rows, meta)
    ds = definitions_md(rows, meta, ceilings)
    csv_rows = results_csv(rows, meta)

    if args.write:
        results.mkdir(parents=True, exist_ok=True)
        (results / "leaderboard.md").write_text(lb, encoding="utf-8")
        (results / "definitions-spread.md").write_text(ds, encoding="utf-8")
        with (results / "results.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(csv_rows)
        print(f"wrote leaderboard.md, definitions-spread.md and results.csv in {results}")
    else:
        print(lb)
    completed = sum(1 for r in rows if r["status"] == "completed")
    print(f"systems: {len(rows)}, with a publishable run: {completed}")


if __name__ == "__main__":
    main()
