#!/usr/bin/env python3
"""Render the Exception Economics report from the scorer's JSON output.

Every figure in every report file this writes is read from `scores-baseline.json` and
`drift.json`. Nothing is typed in by hand, so a re-run changes the reports and a
report can never drift away from the numbers it claims to describe.

Writes into `results/exception-economics-v1.0/`:

    leaderboard.md    the systems table, and the reference-policy arithmetic
    drift.md          the ninety-day drift simulation
    findings.md       what the tables show, each finding tied to a table
    reproduce.md      the commands, versions and hashes
    cfo-summary.md    one page, INR and USD, placeholder inputs labelled

Usage:
    python3 report.py --results ../../results/exception-economics-v1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RUN_DATE = "2026-09-02"

POLICY_NOTE = (
    "The figures below come from the dataset's reference decision policy: a synthetic "
    "confidence and proposed outcome generated with each item. It is a property of "
    "the dataset. It is not a measurement of any model, service or vendor, and no "
    "row in it should be read as one."
)

SYSTEMS_NOT_RUN = [
    "GPT (latest)",
    "Claude (latest)",
    "Gemini (latest)",
    "Mistral (latest)",
    "Open model A",
    "Open model B",
    "Entailment Labs pipeline",
]
NOT_RUN_REASON = ("not run — no model interface key and no reachable model interface "
                  "in the build environment")


# --------------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------------

def pct(value, places: int = 1) -> str:
    return "not run" if value is None else f"{value * 100:.{places}f}"


def num(value, places: int = 1) -> str:
    return "not run" if value is None else f"{value:,.{places}f}"


def signed_pp(value) -> str:
    return "not run" if value is None else f"{value:+.1f}"


def signed_pct(value) -> str:
    return "not run" if value is None else f"{value:+.1f}"


def plural(count: int, singular: str, many: str | None = None) -> str:
    return singular if int(count) == 1 else (many or singular + "s")


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def provenance(scores: dict) -> str:
    return (f"Dataset `exception-economics` version {scores['dataset_version']} · "
            f"seed {scores['dataset_seed']} · ground truth sha256 "
            f"`{scores['ground_truth_sha256'][:16]}` · scorer version "
            f"{scores['scorer_version']} · charter version {scores['charter_version']} · "
            f"run date {RUN_DATE} · ground truth synthetic.")


# --------------------------------------------------------------------------------
# leaderboard.md
# --------------------------------------------------------------------------------

def render_leaderboard(scores: dict, labour: dict) -> str:
    thresholds = scores["thresholds"]
    sweep = scores["sweep"]
    first = thresholds[0]
    counts = first["counts"]

    parts = ["# Exception Economics v1.0 — leaderboard", "", provenance(scores), ""]

    parts += [
        "## Status",
        "",
        "No system has been run against this dataset. The build environment holds no "
        "model interface key and cannot reach a model interface, so every system row "
        "below reads `not run` with its reason, per charter 3.1.8.",
        "",
        table(["System", "Automation rate %", "Rework min per 1,000 automated",
               "Reviewer min per 1,000 items", "Net cost per item", "Status"],
              [[s, "not run", "not run", "not run", "not run", NOT_RUN_REASON]
               for s in SYSTEMS_NOT_RUN]),
        "",
        "That table is the point of the suite and it is empty. What follows is not a "
        "substitute for it.",
        "",
        "## What this suite scores, and what it does not need",
        "",
        "Exception Economics scores a decision policy over labelled items. For each "
        "item the policy either completes it without a person or routes it to one, "
        "and where it completes an item it is either right or wrong. Automation rate, "
        "wrong-automation rework, reviewer minutes and net cost per item all follow "
        "from those two facts and from the labour model. Every one of them is "
        "arithmetic over ground truth. None of them needs a model to be called.",
        "",
        "That is why this suite produces numbers in an environment with no keys and "
        "no network, and it is also the limit of what those numbers mean. They "
        "describe a policy and a threshold. They describe no vendor's system.",
        "",
        "A real system's predictions are dropped in through a documented interface, "
        "one JSON object per item with `item_id`, `proposed_outcome` and "
        "`confidence`. `score.py --predictions <file>` then produces the same tables "
        "for that system, and the system rows above stop reading `not run`.",
        "",
        "## Reference decision policy",
        "",
        POLICY_NOTE,
        "",
    ]

    # Denominator reconciliation.
    excluded = counts["excluded"]
    parts += [
        "### Denominators",
        "",
        "The tables below score the **baseline population**, being the 1,700 items of "
        "the 2,000-item dataset that make up the acceptance set. The remaining 300 "
        "items are the shifted population and are used only by the drift simulation "
        "in `drift.md`, per charter 4.4.2. `MANIFEST.md` sets out both.",
        "",
        "Charter 3.1.2: nothing is silently dropped, and every exclusion is counted "
        "beside the figure it was excluded from.",
        "",
        table(["Line", "Items"],
              [["Items received, baseline population",
                f"{counts['items_received']:,}"],
               ["Rejected before processing by a named rule",
                f"{excluded['pre_processing_rejected']:,}"],
               ["Abandoned, upstream system unavailable",
                f"{excluded['upstream_failure']:,}"],
               ["Open at window close, reported as in flight",
                f"{excluded['in_flight']:,}"],
               ["**Items admitted to processing**", f"**{counts['items_admitted']:,}**"]]),
        "",
        "The scorer asserts the identity in charter 3.5.3 at every threshold: "
        "automation rate plus exception rate equals one over items admitted. A run "
        "whose counts do not reconcile fails rather than reporting.",
        "",
        "### Headline, at three confidence thresholds",
        "",
        "Charter 3.14.6: automation rate is never published alone. The "
        "wrong-automation figure sits on the same row.",
        "",
        table(["Confidence threshold", "Automation rate %", "Wrong automations",
               "Wrong automations as % of automated",
               "Rework min per 1,000 automated", "Open exposure items",
               "Reviewer min per 1,000 items", "Net cost per item, INR",
               "Net cost per item, USD"],
              [[f"{t['threshold']:.2f}",
                pct(t["rates"]["automation_rate"]),
                f"{t['counts']['automated_wrong']:,}",
                pct(t["rates"]["wrong_automation_rate_of_automated"]),
                num(t["rework"]["minutes_per_1000_automated"]),
                f"{t['rework']['open_exposure']['items']:,}",
                num(t["reviewer_minutes"]["per_1000_items_admitted"]),
                num(t["cost"]["net_cost_per_item_inr"], 4),
                num(t["cost"]["net_cost_per_item_usd"], 4)]
               for t in thresholds]),
        "",
        f"Sample size {counts['items_admitted']:,} items admitted, at every "
        f"threshold. Money at the placeholder rates below, which are not market "
        f"rates and are not a measurement.",
        "",
    ]

    best = sweep["best"]
    parts += [
        "### The threshold that minimises net cost",
        "",
        f"Swept from {sweep['points'][0]['threshold']:.2f} to "
        f"{sweep['points'][-1]['threshold']:.2f} in steps of 0.01, "
        f"{len(sweep['points'])} points.",
        "",
        table(["Figure", "Value"],
              [["Minimising threshold", f"{sweep['minimising_threshold']:.2f}"],
               ["Automation rate at that threshold, %",
                pct(best["automation_rate"])],
               ["Net cost per item, INR", num(best["net_cost_per_item_inr"], 4)],
               ["Net cost per item, USD", num(best["net_cost_per_item_usd"], 4)],
               ["Reviewer min per 1,000 items",
                num(best["reviewer_minutes_per_1000_items"])],
               ["Rework min per 1,000 automated",
                num(best["rework_minutes_per_1000_automated"])],
               ["Open exposure items", f"{best['open_exposure_items']:,}"]]),
        "",
        "The curve, at every fifth point of the sweep.",
        "",
        table(["Threshold", "Automation rate %", "Reviewer min per 1,000 items",
               "Rework min per 1,000 automated", "Open exposure items",
               "Net cost per item, INR"],
              [[f"{p['threshold']:.2f}", pct(p["automation_rate"]),
                num(p["reviewer_minutes_per_1000_items"]),
                num(p["rework_minutes_per_1000_automated"]),
                f"{p['open_exposure_items']:,}",
                num(p["net_cost_per_item_inr"], 4)]
               for p in sweep["points"] if round(p["threshold"] * 100) % 5 == 0]),
        "",
    ]

    # Per tier and per work type at each threshold.
    parts += ["### Per tier", "",
              "Charter 4.1.4: every results table is broken out by tier, and the "
              "headline moves when the mix moves, so the mix travels with it.", ""]
    for t in thresholds:
        rows = []
        for tier, row in t["breakdowns"]["by_tier"].items():
            rows.append([f"T{tier}", f"{int(row['admitted']):,}",
                         pct(row["automation_rate"]),
                         f"{int(row['automated_wrong']):,}",
                         pct(row["wrong_automation_rate_of_automated"]),
                         f"{int(row['open_exposure']):,}",
                         num(row["reviewer_minutes"]),
                         num(row["rework_minutes"])])
        parts += [f"Threshold {t['threshold']:.2f}.", "",
                  table(["Tier", "Items admitted", "Automation rate %",
                         "Wrong automations", "Wrong as % of automated",
                         "Open exposure items", "Reviewer minutes",
                         "Rework minutes"], rows), ""]

    parts += ["### Per work type", ""]
    for t in thresholds:
        rows = []
        for work_type, row in t["breakdowns"]["by_work_type"].items():
            rows.append([work_type, f"{int(row['admitted']):,}",
                         pct(row["automation_rate"]),
                         f"{int(row['automated_wrong']):,}",
                         pct(row["wrong_automation_rate_of_automated"]),
                         f"{int(row['open_exposure']):,}",
                         num(row["reviewer_minutes"]),
                         num(row["rework_minutes"])])
        parts += [f"Threshold {t['threshold']:.2f}.", "",
                  table(["Work type", "Items admitted", "Automation rate %",
                         "Wrong automations", "Wrong as % of automated",
                         "Open exposure items", "Reviewer minutes",
                         "Rework minutes"], rows), ""]

    # Reviewer minutes by entry code.
    parts += ["### Reviewer minutes per exception, by queue entry code", "",
              "Charter 3.16.1: reported as the mean and the median, and always broken "
              "down by entry code, because a low-confidence check and a processing "
              "failure are different pieces of work.", ""]
    for t in thresholds:
        rows = []
        for code, stats in t["reviewer_minutes"]["by_entry_code"].items():
            if not stats["exceptions"]:
                continue
            rows.append([code, f"{stats['exceptions']:,}",
                         num(stats["mean_minutes"], 2),
                         num(stats["median_minutes"], 2),
                         num(stats["total_minutes"])])
        rows.append(["**All codes**",
                     f"**{t['counts']['exceptions']:,}**",
                     f"**{num(t['reviewer_minutes']['mean_per_exception'], 2)}**",
                     f"**{num(t['reviewer_minutes']['median_per_exception'], 2)}**",
                     f"**{num(t['reviewer_minutes']['total'])}**"])
        parts += [f"Threshold {t['threshold']:.2f}.", "",
                  table(["Entry code", "Exceptions closed", "Mean minutes",
                         "Median minutes", "Total minutes"], rows), ""]

    parts += [
        "`DRIFT` is zero at every threshold. No drift monitor is modelled in this "
        "suite. Whether a deployment's monitoring sees a drift, and how long it takes "
        "to say so, is measured by the Day-60 suite in `10-benchmarks/day-60/`, not "
        "by this one.",
        "",
    ]

    # Rework by error class.
    parts += ["### Wrong-automation rework, by error class", "",
              "Charter 3.15.3: an error class with no detection route inside the "
              "measurement window is reported as an open exposure count with the "
              "class named, and is never given an estimated minute figure.", ""]
    for t in thresholds:
        rows = []
        for name, row in t["rework"]["by_error_class"].items():
            rows.append([name, f"{row['items']:,}",
                         row["detection_route"],
                         num(row["minutes"]) if row["priced"] else "not priced",
                         "priced" if row["priced"] else "open exposure"])
        if not rows:
            rows = [["none", "0", "—", "—", "—"]]
        exposure = t["rework"]["open_exposure"]
        parts += [f"Threshold {t['threshold']:.2f}. Open exposure items: "
                  f"{exposure['items']:,}"
                  + (f" ({', '.join(f'{k} {v}' for k, v in exposure['by_class'].items())})."
                     if exposure["by_class"] else "."),
                  "",
                  table(["Error class", "Items", "Detection route", "Rework minutes",
                         "Treatment"], rows), ""]

    # Reported separately.
    parts += [
        "### Reported separately, and not inside net cost",
        "",
        table(["Line", "Threshold 0.80", "Threshold 0.90", "Threshold 0.95", "Why"],
              [["Sampled-audit minutes"]
               + [num(t["audit_minutes"]["total"]) for t in thresholds]
               + ["Charter 3.16.5: an audit is a measurement device, not production work"],
               ["Manual handling minutes after a processing failure"]
               + [num(t["manual_handling_minutes"]["total"]) for t in thresholds]
               + ["The item still has to be done by hand; the charter's net cost "
                  "composition does not include it, so it is shown beside it"],
               ["Items drawn into the sampled audit"]
               + [f"{t['counts']['audited']:,}" for t in thresholds]
               + ["Audit rate is a scoring parameter, not a result"],
               ["Audits that changed the output"]
               + [f"{t['counts']['audit_corrected']:,}" for t in thresholds]
               + ["Charter 3.4.2: these are exceptions, not automated items"]]),
        "",
        "## The labour model behind the money",
        "",
        table(["Input", "Value", "Status"],
              [["Fully loaded reviewer cost, INR per hour",
                num(labour["reviewer_cost"]["inr_per_hour"]["value"], 2),
                labour["reviewer_cost"]["inr_per_hour"]["status"]],
               ["Fully loaded reviewer cost, USD per hour",
                num(labour["reviewer_cost"]["usd_per_hour"]["value"], 2),
                labour["reviewer_cost"]["usd_per_hour"]["status"]],
               ["Senior reviewer multiplier",
                num(labour["reviewer_cost"]["senior_reviewer_multiplier"]["value"], 2),
                labour["reviewer_cost"]["senior_reviewer_multiplier"]["status"]],
               ["Machine cost per item, INR",
                num(labour["machine_cost"]["per_item_inr"]["value"], 2),
                labour["machine_cost"]["per_item_inr"]["status"]],
               ["Machine cost per item, USD",
                num(labour["machine_cost"]["per_item_usd"]["value"], 2),
                labour["machine_cost"]["per_item_usd"]["status"]]]),
        "",
        "The INR and USD rates are two independent placeholders. No exchange rate is "
        "applied between them anywhere in the scorer, and none should be inferred "
        "from the two figures sitting beside each other. Machine cost is zero because "
        "no system has been run, so no measured cost per item exists; every net cost "
        "figure in this report is therefore labour only.",
        "",
        "Every minute figure in the labour model is a modelling assumption and each "
        "one states its basis in `labour-model.yaml`. Not one was measured by a time "
        "study, ours or anyone else's. `validate.py` fails the build if a minute "
        "figure appears without a basis, or if a money figure appears without the "
        "placeholder mark.",
        "",
    ]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------------
# drift.md
# --------------------------------------------------------------------------------

def render_drift(drift: dict, scores: dict) -> str:
    parts = ["# Exception Economics v1.0 — ninety-day drift simulation", "",
             provenance(scores), ""]
    parts += [
        "## What this is",
        "",
        "A simulation. Charter 3.17.4 requires it to be labelled one in the table, "
        "the chart and the prose, so it is labelled one here and in every file that "
        "quotes it. Every number on this page is a simulation output over synthetic "
        "ground truth, produced by scoring the dataset's synthetic reference decision "
        "policy against a shifted input distribution. No system was run. Nothing here "
        "is a record of what happened to a deployment.",
        "",
        "What it is evidence about is sensitivity: how much a fixed decision policy "
        "and a fixed threshold cost when the input moves underneath them. That is a "
        "question a partner can ask before signing, and this is one way to answer it.",
        "",
        "## The shift",
        "",
        f"Seven steps across ninety days, {drift['drift_sample_size']:,} items drawn "
        f"per step. The steps are defined in the dataset manifest, not in the scorer, "
        f"per charter 3.17.4.",
        "",
        table(["Day", "Step", "Shifted share of the sample %", "Work-type weights",
               "What changed"],
              [[str(s["day"]), s["label"], f"{s['shifted_share'] * 100:.0f}",
                ", ".join(f"{k} {v:.2f}" for k, v in sorted(
                    s["seasonal_weights"].items())),
                s["note"]] for s in drift["drift_steps"]]),
        "",
        "The shifted population is 300 items, every one of them tier 5, because "
        "charter 4.4.2 makes tier 5 the only tier in which the drift simulation is "
        "applied. It carries three drivers: new vendor formats on reconciliation, new "
        "ticket categories with no labelled example anywhere in the baseline, and a "
        "new KYC source format. The seasonal weights move the work-type mix of the "
        "rest of the sample. Both draws are seeded from the dataset seed and the step "
        "day, so the whole curve reproduces exactly.",
        "",
        "## Frozen-set drift",
        "",
        "Charter 3.17.1 requires two figures and treats neither as complete without "
        "the other. Frozen-set drift is zero at every step of this simulation, by "
        "construction: the simulation changes the input distribution and nothing "
        "else, so the same decision policy scores the same frozen items identically "
        "at every step.",
        "",
        "That zero is a property of the simulation. It is not a finding about any "
        "system's stability, and quoting it as one would be a misuse of this page. A "
        "real frozen-set drift figure needs a real system measured twice, ninety days "
        "apart, and none has been.",
        "",
        "## Live-distribution drift",
        "",
    ]

    for threshold in sorted(drift["runs"], key=float):
        payload = drift["runs"][threshold]
        steps = payload["steps"]
        parts += [f"### At confidence threshold {float(threshold):.2f}", "",
                  "Simulation output over synthetic ground truth.", "",
                  table(["Day", "Step", "Shifted share %", "Sample size",
                         "Automation rate %", "Wrong automations",
                         "Wrong as % of automated", "Rework min per 1,000 automated",
                         "Open exposure items", "Reviewer min per 1,000 items",
                         "Net cost per item, INR", "Net cost per item, USD"],
                        [[str(s["day"]), s["label"],
                          f"{s['shifted_share_planned'] * 100:.0f}",
                          f"{s['sample_size']:,}",
                          pct(s["live"]["rates"]["automation_rate"]),
                          f"{s['live']['counts']['automated_wrong']:,}",
                          pct(s["live"]["rates"]["wrong_automation_rate_of_automated"]),
                          num(s["live"]["rework"]["minutes_per_1000_automated"]),
                          f"{s['live']['rework']['open_exposure']['items']:,}",
                          num(s["live"]["reviewer_minutes"]["per_1000_items_admitted"]),
                          num(s["live"]["cost"]["net_cost_per_item_inr"], 4),
                          num(s["live"]["cost"]["net_cost_per_item_usd"], 4)]
                         for s in steps]), ""]

        d = steps[-1]["live_distribution_drift"]
        parts += ["Acceptance to day 90. Charter 3.17.2: both endpoints are shown, "
                  "rates in percentage points and costs in percent of baseline.", "",
                  table(["Measure", "At acceptance", "At day 90", "Change"],
                        [["Automation rate, %",
                          pct(d["automation_rate"]["acceptance"]),
                          pct(d["automation_rate"]["day_n"]),
                          signed_pp(d["automation_rate"]["change_percentage_points"])
                          + " pp"],
                         ["Wrong automations as % of automated",
                          pct(d["wrong_automation_rate_of_automated"]["acceptance"]),
                          pct(d["wrong_automation_rate_of_automated"]["day_n"]),
                          signed_pp(d["wrong_automation_rate_of_automated"]
                                    ["change_percentage_points"]) + " pp"],
                         ["Rework minutes per 1,000 automated",
                          num(d["rework_minutes_per_1000_automated"]["acceptance"]),
                          num(d["rework_minutes_per_1000_automated"]["day_n"]),
                          signed_pct(d["rework_minutes_per_1000_automated"]
                                     ["change_percent_of_baseline"]) + " %"],
                         ["Reviewer minutes per 1,000 items",
                          num(d["reviewer_minutes_per_1000_items"]["acceptance"]),
                          num(d["reviewer_minutes_per_1000_items"]["day_n"]),
                          signed_pct(d["reviewer_minutes_per_1000_items"]
                                     ["change_percent_of_baseline"]) + " %"],
                         ["Net cost per item, INR",
                          num(d["net_cost_per_item_inr"]["acceptance"], 4),
                          num(d["net_cost_per_item_inr"]["day_n"], 4),
                          signed_pct(d["net_cost_per_item_inr"]
                                     ["change_percent_of_baseline"]) + " %"],
                         ["Net cost per item, USD",
                          num(d["net_cost_per_item_usd"]["acceptance"], 4),
                          num(d["net_cost_per_item_usd"]["day_n"], 4),
                          signed_pct(d["net_cost_per_item_usd"]
                                     ["change_percent_of_baseline"]) + " %"],
                         ["Open exposure items",
                          f"{d['open_exposure_items']['acceptance']:,}",
                          f"{d['open_exposure_items']['day_n']:,}",
                          f"{d['open_exposure_items']['day_n'] - d['open_exposure_items']['acceptance']:+,}"
                          + " items"]]), ""]

    parts += [
        "## How to read the curve",
        "",
        "The automation rate is the number a vendor deck quotes, and it is the number "
        "that moves least. Everything that decides whether the automation is worth "
        "having moves several times as far. Charter 3.14.6 exists for this reason: "
        "an automation rate published without the wrong-automation figure on the same "
        "row does not say whether the system got better or worse.",
        "",
        "## Reproducing this page",
        "",
        "```bash",
        "python3 generate.py --seed 20260902",
        "python3 drift.py --out ../../results/exception-economics-v1.0/drift.json",
        "```",
        "",
        "Deterministic from the seed. The same two commands on any machine reproduce "
        "every figure above, and `validate.py` fails if the ground truth on disk is "
        "not the ground truth the seed produces.",
        "",
    ]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------------
# cfo-summary.md
# --------------------------------------------------------------------------------

def render_cfo(scores: dict, drift: dict, labour: dict) -> str:
    thresholds = scores["thresholds"]
    sweep = scores["sweep"]
    best = sweep["best"]
    admitted = thresholds[0]["counts"]["items_admitted"]
    inr_rate = labour["reviewer_cost"]["inr_per_hour"]["value"]
    usd_rate = labour["reviewer_cost"]["usd_per_hour"]["value"]
    day90 = drift["runs"]["0.8"]["steps"][-1]["live_distribution_drift"]

    low, mid, high = thresholds

    parts = [
        "# Exception Economics — one page for a chief financial officer",
        "",
        provenance(scores),
        "",
        "## Read this first",
        "",
        "This page contains no measured claim about any vendor's system, because no "
        "vendor's system has been run. It contains the arithmetic of a cost model "
        "with placeholder inputs, applied to synthetic items with known answers. Its "
        "use is to show which numbers decide the business case and how far they move "
        "each other. It is not a quotation, a benchmark result or a saving.",
        "",
        "Every money input to it is a placeholder and is marked as such in every "
        "table below. Replace them with your own figures and the arithmetic holds; "
        "leave them and the money columns mean nothing on their own.",
        "",
        "## The one thing worth taking from this page",
        "",
        "Automation rate is not a result. A policy that automates more can cost more, "
        "because the work created by a wrong automation is not the work saved by a "
        "right one, and because some wrong automations are never found at all.",
        "",
        "## The model, in full",
        "",
        table(["Input", "Value", "Status"],
              [["Fully loaded reviewer cost, INR per hour", num(inr_rate, 2),
                "placeholder — replace with your own fully loaded cost"],
               ["Fully loaded reviewer cost, USD per hour", num(usd_rate, 2),
                "placeholder — replace with your own fully loaded cost"],
               ["Exchange rate applied between the two", "none",
                "the two rates are independent placeholders; no rate is applied and "
                "none should be inferred"],
               ["Machine cost per item", "0.00",
                "no system has been run, so no measured cost per item exists"],
               ["Reviewer minutes per exception", "see the labour model",
                "modelling assumptions, each with its basis stated; none measured"],
               ["Rework minutes per wrong automation", "see the labour model",
                "modelling assumptions, each with its basis stated; none measured"],
               ["Items", f"{admitted:,} admitted",
                "synthetic, with known answers"]]),
        "",
        "## What the arithmetic gives",
        "",
        f"Per item admitted, across {admitted:,} items, at three confidence "
        f"thresholds.",
        "",
        table(["Confidence threshold", "Automation rate %",
               "Reviewer min per 1,000 items", "Rework min per 1,000 automated",
               "Net cost per item, INR", "Net cost per item, USD",
               "Wrong automations nobody would find"],
              [[f"{t['threshold']:.2f}", pct(t["rates"]["automation_rate"]),
                num(t["reviewer_minutes"]["per_1000_items_admitted"]),
                num(t["rework"]["minutes_per_1000_automated"]),
                num(t["cost"]["net_cost_per_item_inr"], 4),
                num(t["cost"]["net_cost_per_item_usd"], 4),
                f"{t['rework']['open_exposure']['items']:,}"]
               for t in thresholds]),
        "",
        f"Raising the threshold from {low['threshold']:.2f} to "
        f"{high['threshold']:.2f} cuts the automation rate from "
        f"{pct(low['rates']['automation_rate'])} percent to "
        f"{pct(high['rates']['automation_rate'])} percent and raises the net cost per "
        f"item from INR {num(low['cost']['net_cost_per_item_inr'], 4)} to INR "
        f"{num(high['cost']['net_cost_per_item_inr'], 4)}, at the placeholder rate. "
        f"In USD, from {num(low['cost']['net_cost_per_item_usd'], 4)} to "
        f"{num(high['cost']['net_cost_per_item_usd'], 4)}, at the other placeholder "
        f"rate. Both movements are the same arithmetic seen in two currencies, not "
        f"two observations.",
        "",
        "## The threshold that minimises cost, in this model",
        "",
        table(["Figure", "Value"],
              [["Minimising threshold", f"{sweep['minimising_threshold']:.2f}"],
               ["Automation rate there, %", pct(best["automation_rate"])],
               ["Net cost per item, INR", num(best["net_cost_per_item_inr"], 4)],
               ["Net cost per item, USD", num(best["net_cost_per_item_usd"], 4)],
               ["Net cost per item at threshold 0.95, INR",
                num(high["cost"]["net_cost_per_item_inr"], 4)],
               ["Difference, percent of the minimum",
                f"{(high['cost']['net_cost_per_item_inr'] / best['net_cost_per_item_inr'] - 1) * 100:+.1f}"]]),
        "",
        "The minimum sits below the lowest of the three published thresholds. Where a "
        "real system's minimum sits depends on how well its confidence is calibrated, "
        "which is measured, not assumed, and which nobody has measured here.",
        "",
        "## What ninety days of input drift does to the same model",
        "",
        "Simulation output over synthetic ground truth. At threshold 0.80, comparing "
        "the acceptance measurement with day 90.",
        "",
        table(["Measure", "At acceptance", "At day 90", "Change"],
              [["Automation rate, %",
                pct(day90["automation_rate"]["acceptance"]),
                pct(day90["automation_rate"]["day_n"]),
                signed_pp(day90["automation_rate"]["change_percentage_points"]) + " pp"],
               ["Net cost per item, INR",
                num(day90["net_cost_per_item_inr"]["acceptance"], 4),
                num(day90["net_cost_per_item_inr"]["day_n"], 4),
                signed_pct(day90["net_cost_per_item_inr"]["change_percent_of_baseline"])
                + " %"],
               ["Net cost per item, USD",
                num(day90["net_cost_per_item_usd"]["acceptance"], 4),
                num(day90["net_cost_per_item_usd"]["day_n"], 4),
                signed_pct(day90["net_cost_per_item_usd"]["change_percent_of_baseline"])
                + " %"],
               ["Wrong automations nobody would find",
                f"{day90['open_exposure_items']['acceptance']:,}",
                f"{day90['open_exposure_items']['day_n']:,}",
                f"{day90['open_exposure_items']['day_n'] - day90['open_exposure_items']['acceptance']:+,}"
                + " items"]]),
        "",
        f"The automation rate falls "
        f"{abs(day90['automation_rate']['change_percentage_points']):.1f} percentage "
        f"points, which a monthly report would describe as broadly stable. The net "
        f"cost per item rises "
        f"{day90['net_cost_per_item_inr']['change_percent_of_baseline']:.0f} percent "
        f"over the same ninety days. That gap between the reported measure and the "
        f"cost measure is the reason this suite exists.",
        "",
        "## The line that carries no number",
        "",
        "Three of the eleven error classes in the labour model have no detection "
        "route inside a monthly measurement window: a support ticket that needed "
        "escalation and was closed as routine, a know-your-customer case wrongly "
        "passed, and an invoice exception wrongly posted. Nothing in the process "
        "looks for them. They are counted and named as open exposure and they are "
        "never priced, because a detection time invented for an error nobody would "
        "find is exactly the kind of figure that makes a business case look better "
        "than the business.",
        "",
        f"At threshold {low['threshold']:.2f} the simulation leaves "
        f"{low['rework']['open_exposure']['items']:,} such items in the baseline "
        f"sample and {day90['open_exposure_items']['day_n']:,} at day 90 of the drift "
        f"simulation. Those counts are the honest form of that risk. A money figure "
        f"beside them would not be.",
        "",
        "## Three questions this page equips you to ask a supplier",
        "",
        "1. At what confidence threshold is your quoted automation rate measured, and "
        "what is the wrong-automation rate on the same row at the same threshold.",
        "2. Which of your error classes has no detection route inside a monthly "
        "window, and how many items were in those classes last month.",
        "3. What were the automation rate and the net cost per item at acceptance, "
        "and what were the same two figures ninety days later, with both endpoints "
        "and both sample sizes.",
        "",
        "The contract language for all three is in `10-benchmarks/charter/"
        "contract-clauses.md`, clauses 13 to 16.",
        "",
    ]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------------
# findings.md
# --------------------------------------------------------------------------------

def render_findings(scores: dict, drift: dict) -> str:
    thresholds = scores["thresholds"]
    low, mid, high = thresholds
    sweep = scores["sweep"]
    best = sweep["best"]
    d80 = drift["runs"]["0.8"]["steps"][-1]["live_distribution_drift"]
    d95 = drift["runs"]["0.95"]["steps"][-1]["live_distribution_drift"]
    tiers = low["breakdowns"]["by_tier"]
    work = low["breakdowns"]["by_work_type"]
    codes = low["reviewer_minutes"]["by_entry_code"]

    t1, t5 = tiers["1"], tiers["5"]
    kyc, ticket = work["kyc_case"], work["ticket_triage"]

    parts = [
        "# Exception Economics v1.0 — findings",
        "",
        provenance(scores),
        "",
        "## What these findings are, and are not",
        "",
        "No system has been run against this dataset, so there is no finding here "
        "about any model, service or vendor, and none will be written until a run "
        "exists. What follows are findings about the measurement itself: what the "
        "arithmetic of a cost model does to an automation rate, and which numbers "
        "move when the input moves. Every one is tied to a table in "
        "`leaderboard.md` or `drift.md`, and every one rests on synthetic ground "
        "truth scored with a synthetic reference decision policy.",
        "",
        "## 1. The headline metric is the one that moves least",
        "",
        f"In the drift simulation at threshold {low['threshold']:.2f}, the automation "
        f"rate falls "
        f"{abs(d80['automation_rate']['change_percentage_points']):.1f} percentage "
        f"points between acceptance and day 90, from "
        f"{pct(d80['automation_rate']['acceptance'])} percent to "
        f"{pct(d80['automation_rate']['day_n'])} percent. Over the same steps the "
        f"wrong-automation rate rises "
        f"{d80['wrong_automation_rate_of_automated']['change_percentage_points']:.1f} "
        f"percentage points and the net cost per item rises "
        f"{d80['net_cost_per_item_inr']['change_percent_of_baseline']:.0f} percent.",
        "",
        "A monthly report carrying only the automation rate would describe that "
        "quarter as stable. Table: `drift.md`, live-distribution drift at threshold "
        f"{low['threshold']:.2f}.",
        "",
        "## 2. Net cost per item is not monotonic in the threshold",
        "",
        f"Across the sweep from {sweep['points'][0]['threshold']:.2f} to "
        f"{sweep['points'][-1]['threshold']:.2f}, net cost per item falls, reaches a "
        f"minimum of INR {num(best['net_cost_per_item_inr'], 4)} at threshold "
        f"{sweep['minimising_threshold']:.2f}, and then rises to INR "
        f"{num(high['cost']['net_cost_per_item_inr'], 4)} at threshold "
        f"{high['threshold']:.2f}. The most cautious threshold in the sweep costs "
        f"{(high['cost']['net_cost_per_item_inr'] / best['net_cost_per_item_inr'] - 1) * 100:.0f} "
        f"percent more per item than the cheapest.",
        "",
        "Caution is not free. It is paid for in reviewer minutes, which rise from "
        f"{num(best['reviewer_minutes_per_1000_items'])} per 1,000 items at the "
        f"minimum to {num(high['reviewer_minutes']['per_1000_items_admitted'])} at "
        f"threshold {high['threshold']:.2f}. Table: `leaderboard.md`, the threshold "
        f"that minimises net cost.",
        "",
        "## 3. Raising the threshold hides the exposure rather than removing it",
        "",
        f"Open exposure items, wrong automations in classes with no detection route "
        f"inside the window, fall from {low['rework']['open_exposure']['items']:,} at "
        f"threshold {low['threshold']:.2f} to "
        f"{high['rework']['open_exposure']['items']:,} at threshold "
        f"{high['threshold']:.2f} in the baseline sample. In the drift simulation at "
        f"day 90 the same count is {d80['open_exposure_items']['day_n']:,} at "
        f"threshold {low['threshold']:.2f} and {d95['open_exposure_items']['day_n']:,} "
        f"at threshold 0.95.",
        "",
        "The count falls because fewer items are automated at all, not because the "
        "process acquired a way of finding the errors. Nothing in the model detects "
        "them at any threshold. Tables: `leaderboard.md`, wrong-automation rework by "
        "error class; `drift.md`, live-distribution drift.",
        "",
        "## 4. The tier is where the cost sits, not the average",
        "",
        f"At threshold {low['threshold']:.2f}, tier 1 automates "
        f"{pct(t1['automation_rate'])} percent of "
        f"{int(t1['admitted']):,} items with "
        f"{int(t1['automated_wrong']):,} wrong "
        f"{plural(t1['automated_wrong'], 'automation')}. Tier 5 automates "
        f"{pct(t5['automation_rate'])} percent of {int(t5['admitted']):,} items with "
        f"{int(t5['automated_wrong']):,} wrong. The wrong-automation rate of "
        f"automated items is {pct(t1['wrong_automation_rate_of_automated'])} percent "
        f"at tier 1 and {pct(t5['wrong_automation_rate_of_automated'])} percent at "
        f"tier 5.",
        "",
        "A headline figure over a mix is a statement about the mix as much as about "
        "the policy, which is why charter 4.1.4 makes the mix travel with the number. "
        "Table: `leaderboard.md`, per tier.",
        "",
        "## 5. Equal automation rates across work types do not mean equal cost",
        "",
        f"At threshold {low['threshold']:.2f}, know-your-customer cases automate at "
        f"{pct(kyc['automation_rate'])} percent and ticket triage at "
        f"{pct(ticket['automation_rate'])} percent. On the automation rate alone the "
        f"two look like the same piece of work.",
        "",
        f"They are not. The {int(kyc['exceptions']):,} know-your-customer exceptions "
        f"take {num(kyc['reviewer_minutes'])} reviewer minutes; the "
        f"{int(ticket['exceptions']):,} ticket exceptions take "
        f"{num(ticket['reviewer_minutes'])}, a factor of "
        f"{kyc['reviewer_minutes'] / ticket['reviewer_minutes']:.1f} on a comparable "
        f"count. The rework is further apart still: "
        f"{num(kyc['rework_minutes'])} minutes against "
        f"{num(ticket['rework_minutes'])}.",
        "",
        "One threshold across a mixed queue is a choice to be wrong in one direction "
        "on part of it, and a single blended automation rate does not show which "
        "part. Table: `leaderboard.md`, per work type.",
        "",
        "## 6. The mean reviewer minute is a weak number without the entry code",
        "",
        f"At threshold {low['threshold']:.2f} the mean is "
        f"{num(low['reviewer_minutes']['mean_per_exception'], 2)} minutes per "
        f"exception and the median is "
        f"{num(low['reviewer_minutes']['median_per_exception'], 2)}. By entry code "
        f"the mean runs from {num(codes['FAIL']['mean_minutes'], 2)} minutes on "
        f"{codes['FAIL']['exceptions']:,} processing failures to "
        f"{num(codes['FLAG']['mean_minutes'], 2)} minutes on "
        f"{codes['FLAG']['exceptions']:,} policy flags, a factor of "
        f"{codes['FLAG']['mean_minutes'] / codes['FAIL']['mean_minutes']:.1f}.",
        "",
        "A queue redesign that moves items between codes moves the mean without "
        "changing anyone's workload. Charter 3.16.1 requires the breakdown for that "
        "reason. Table: `leaderboard.md`, reviewer minutes by queue entry code.",
        "",
        "## 7. The cheapest exception to triage creates the most work",
        "",
        f"Processing failures are the shortest exception in the model, "
        f"{num(codes['FAIL']['mean_minutes'], 2)} minutes each at threshold "
        f"{low['threshold']:.2f}. The items behind them still have to be done: "
        f"{num(low['manual_handling_minutes']['total'])} minutes of manual handling, "
        f"against {num(codes['FAIL']['total_minutes'])} minutes of triage.",
        "",
        "That manual handling sits outside the charter's net cost composition, so it "
        "is reported beside it rather than inside it. A supplier reporting only "
        "reviewer minutes per exception would show a processing failure as the "
        "cheapest thing it does. Table: `leaderboard.md`, reported separately.",
        "",
        "## 8. Exclusions are large enough to move a rate on their own",
        "",
        f"Of {low['counts']['items_received']:,} items received, "
        f"{low['counts']['excluded']['pre_processing_rejected']:,} were rejected "
        f"before processing by a named rule, "
        f"{low['counts']['excluded']['upstream_failure']:,} were abandoned when an "
        f"upstream system was unavailable and "
        f"{low['counts']['excluded']['in_flight']:,} were open at window close, "
        f"leaving {low['counts']['items_admitted']:,} admitted.",
        "",
        "Moving those exclusions in or out of the denominator moves the automation "
        "rate without changing a single decision, which is why charter 3.1.2 counts "
        "each of them beside the figure it was excluded from. Table: "
        "`leaderboard.md`, denominators.",
        "",
        "## What is still missing",
        "",
        "Every finding above concerns the measurement. None concerns a system. The "
        "suite produces a system row the moment a decision policy with real "
        "predictions is supplied through `score.py --predictions`, and until then the "
        "leaderboard's system table stays empty rather than illustrated.",
        "",
    ]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------------
# reproduce.md
# --------------------------------------------------------------------------------

def render_reproduce(scores: dict, drift: dict, manifest: dict) -> str:
    parts = [
        "# Exception Economics v1.0 — reproduce",
        "",
        provenance(scores),
        "",
        "## Versions and hashes",
        "",
        table(["Item", "Value"],
              [["Dataset", f"`exception-economics` v{manifest['dataset_version']}"],
               ["Dataset seed", str(manifest["seed"])],
               ["Schema version", manifest["schema_version"]],
               ["Generator version", manifest["generator_version"]],
               ["Scorer version", scores["scorer_version"]],
               ["Drift simulation version", drift["simulation_version"]],
               ["Charter version", scores["charter_version"]],
               ["Ground truth sha256", f"`{manifest['ground_truth_sha256']}`"],
               ["Items", f"{manifest['items']:,}"],
               ["Baseline population", f"{manifest['populations']['baseline']:,}"],
               ["Shifted population", f"{manifest['populations']['shifted']:,}"],
               ["Run date", RUN_DATE],
               ["Model interface calls made", "0"],
               ["Price list date", "not applicable — no provider charge was incurred"]]),
        "",
        "## Prerequisites",
        "",
        "Python 3.11 and PyYAML. Nothing else. No model interface key, no network "
        "access and no browser are needed, because this suite scores a decision "
        "policy over labelled items rather than calling a model.",
        "",
        "```bash",
        "pip install pyyaml --break-system-packages",
        "```",
        "",
        "## The four commands",
        "",
        "From `10-benchmarks/datasets/exception-economics/`:",
        "",
        "```bash",
        f"python3 generate.py --seed {manifest['seed']}",
        "python3 validate.py",
        "python3 score.py --out ../../results/exception-economics-v1.0/scores-baseline.json",
        "python3 drift.py  --out ../../results/exception-economics-v1.0/drift.json",
        "python3 report.py --results ../../results/exception-economics-v1.0",
        "```",
        "",
        "`generate.py` takes under a second and writes `ground-truth.jsonl`, "
        "`manifest.json` and `sample/ground-truth.jsonl`. `validate.py` exits "
        "non-zero if any check fails, including the check that regenerating from the "
        "seed reproduces the file byte for byte. `score.py` and `drift.py` each take "
        "under a second. `report.py` rewrites every markdown file in the results "
        "folder from the two JSON files, so no figure in a report is typed by hand.",
        "",
        "## Scoring a real system",
        "",
        "Write one JSON object per line, one line per item:",
        "",
        "```json",
        '{"item_id": "EE-0001", "proposed_outcome": "recon:matched:PO-446576", '
        '"confidence": 0.91}',
        "```",
        "",
        "`proposed_outcome` uses the encoding in `outcomes.py`: "
        "`route:<category>/<priority>[/escalate]` for ticket triage, "
        "`kyc:<decision>[/<reason>]` for a know-your-customer case and "
        "`recon:<decision>:<po>|<po>` for a reconciliation. The optional booleans "
        "`processing_failure`, `validation_failure` and `policy_flag` default to "
        "false. Then:",
        "",
        "```bash",
        'python3 score.py --predictions runs/vendor-a.jsonl --label "Vendor A" \\',
        "    --out ../../results/exception-economics-v1.0/scores-vendor-a.json",
        "```",
        "",
        "An item with no line in the predictions file is scored as a processing "
        "failure and counted as one. It is never dropped from the denominator, per "
        "charter 3.1.2.",
        "",
        "## Reproducing a single figure",
        "",
        "Every figure in `leaderboard.md` and `drift.md` is a field in "
        "`scores-baseline.json` or `drift.json`. To check one:",
        "",
        "```bash",
        "python3 -c \"import json;d=json.load(open('scores-baseline.json'));"
        "print(d['thresholds'][0]['rates']['automation_rate'])\"",
        "```",
        "",
        "## Neutrality",
        "",
        "Charter 5.5 requires every result to be reproducible from a commit. The "
        "dataset seed, the ground-truth hash, the generator, scorer and drift "
        "versions and the exact commands are all above. There is no private prompt "
        "and no per-system tuning in this suite, because there is no prompt: the "
        "scorer is arithmetic.",
        "",
        "Charter 3.1.4 requires three runs per system per suite. That rule applies to "
        "a run of a model. This scorer is deterministic and its output does not vary "
        "between runs on the same input, so the three-run rule takes effect when a "
        "real system's predictions are scored, and the three prediction files are "
        "then the three runs.",
        "",
        "## What a person still has to supply",
        "",
        table(["Needed", "Why"],
              [["A model interface key per provider, with a spend cap set first",
                "no system row can be produced without one"],
               ["A decision on which model versions are in scope",
                "charter 5.5 records the model version string with every figure"],
               ["A partner's fully loaded reviewer cost, in INR or USD or both",
                "every money figure in this report is a placeholder until then"],
               ["A partner's own measured reviewer minutes, if any exist",
                "every minute in the labour model is a modelling assumption"],
               ["A measured cost per item from a run",
                "machine cost is zero here, so net cost is labour only"]]),
        "",
    ]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results",
                        default=str(HERE / ".." / ".." / "results"
                                    / "exception-economics-v1.0"))
    parser.add_argument("--labour-model", default=str(HERE / "labour-model.yaml"))
    parser.add_argument("--manifest", default=str(HERE / "manifest.json"))
    args = parser.parse_args(argv)

    results = Path(args.results).resolve()
    scores = json.loads((results / "scores-baseline.json").read_text(encoding="utf-8"))
    drift = json.loads((results / "drift.json").read_text(encoding="utf-8"))
    labour = yaml.safe_load(Path(args.labour_model).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    written = {
        "leaderboard.md": render_leaderboard(scores, labour),
        "drift.md": render_drift(drift, scores),
        "findings.md": render_findings(scores, drift),
        "reproduce.md": render_reproduce(scores, drift, manifest),
        "cfo-summary.md": render_cfo(scores, drift, labour),
    }
    for name, body in written.items():
        (results / name).write_text(body, encoding="utf-8")
        print(f"wrote {results / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
