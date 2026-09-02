#!/usr/bin/env python3
"""Ninety-day drift simulation for the Exception Economics suite.

Charter 3.17 requires two drift figures and treats neither as complete without the
other:

  frozen-set drift          the same frozen labelled set used at acceptance, which
                            isolates change in the system
  live-distribution drift   a fresh labelled sample from the last thirty days of
                            input, which isolates change in the input

This simulation produces both, and it is a simulation everywhere it appears
(charter 3.17.4). It shifts the input distribution in the documented steps held in
`manifest.json` and re-scores at each step. It changes nothing about the decision
policy, so:

  * frozen-set drift is zero at every step by construction, because the same policy
    scores the same frozen items. That zero is a property of this simulation, not a
    finding about any system's stability. A real frozen-set drift figure requires a
    real system measured twice, ninety days apart.

  * live-distribution drift is the figure this simulation actually produces. It
    measures how sensitive a fixed decision policy is to input that moves underneath
    it, which is the question the suite exists to ask.

Each step draws a live sample of `drift_sample_size` items:

  * the shifted portion, `shifted_share` of the sample, is drawn from the shifted
    population, allocated across the three shift drivers in proportion to their size
    in that population;
  * the rest is drawn from the baseline population, allocated across work types by
    the step's `seasonal_weights`.

Both draws are seeded from the dataset seed, the step day and the split name, so the
whole curve is reproducible from a seed and identical on any machine.

Usage:
    python3 drift.py
    python3 drift.py --out ../../results/exception-economics-v1.0/drift.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

from score import (
    CHARTER_VERSION,
    SCORER_VERSION,
    load_items,
    load_labour_model,
    score,
)

HERE = Path(__file__).resolve().parent
SIMULATION_VERSION = "1.0.0"

TRACKED_RATES = [
    ("automation_rate", "rates", "automation_rate"),
    ("wrong_automation_rate_of_automated", "rates",
     "wrong_automation_rate_of_automated"),
]
TRACKED_LEVELS = [
    ("reviewer_minutes_per_1000_items", "reviewer_minutes", "per_1000_items_admitted"),
    ("rework_minutes_per_1000_automated", "rework", "minutes_per_1000_automated"),
    ("net_cost_per_item_inr", "cost", "net_cost_per_item_inr"),
    ("net_cost_per_item_usd", "cost", "net_cost_per_item_usd"),
]


def step_stream(seed: int, day: int, name: str) -> random.Random:
    key = f"{seed}|drift|{day}|{name}"
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def largest_remainder(total: int, weights: dict) -> dict:
    raw = {k: total * w for k, w in weights.items()}
    floors = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(floors.values())
    order = sorted(raw, key=lambda k: (-(raw[k] - floors[k]), str(k)))
    for k in order[:remainder]:
        floors[k] += 1
    return floors


def draw_live_sample(items: list[dict], step: dict, size: int, seed: int) -> list[dict]:
    """Draw one step's live sample. Deterministic from the seed and the step day."""
    baseline = [i for i in items if i["population"] == "baseline"]
    shifted = [i for i in items if i["population"] == "shifted"]

    n_shifted = int(round(size * float(step["shifted_share"])))
    n_baseline = size - n_shifted

    sample: list[dict] = []

    if n_shifted:
        by_driver: dict[str, list[dict]] = {}
        for item in shifted:
            by_driver.setdefault(item["shift_driver"], []).append(item)
        weights = {d: len(v) / len(shifted) for d, v in by_driver.items()}
        counts = largest_remainder(n_shifted, weights)
        rng = step_stream(seed, step["day"], "shifted")
        for driver in sorted(by_driver):
            pool = sorted(by_driver[driver], key=lambda i: i["item_id"])
            take = min(counts.get(driver, 0), len(pool))
            sample.extend(rng.sample(pool, k=take))

    by_work: dict[str, list[dict]] = {}
    for item in baseline:
        by_work.setdefault(item["work_type"], []).append(item)
    counts = largest_remainder(n_baseline, dict(step["seasonal_weights"]))
    rng = step_stream(seed, step["day"], "baseline")
    for work_type in sorted(by_work):
        pool = sorted(by_work[work_type], key=lambda i: i["item_id"])
        take = min(counts.get(work_type, 0), len(pool))
        sample.extend(rng.sample(pool, k=take))

    sample.sort(key=lambda i: i["item_id"])
    return sample


def dig(result: dict, section: str, field: str):
    return result[section][field]


def run(items: list[dict], labour: dict, manifest: dict, threshold: float,
        audit_seed: str) -> dict:
    seed = int(manifest["seed"])
    size = int(manifest.get("drift_sample_size", 600))
    steps = manifest["drift_steps"]
    frozen = [i for i in items if i["population"] == "baseline"]

    rows = []
    for step in steps:
        sample = draw_live_sample(items, step, size, seed)
        live = score(sample, labour, threshold, None, audit_seed)
        frozen_result = score(frozen, labour, threshold, None, audit_seed)
        mix: dict[str, int] = {}
        for item in sample:
            mix[item["work_type"]] = mix.get(item["work_type"], 0) + 1
        tier_mix: dict[str, int] = {}
        for item in sample:
            key = str(item["tier"])
            tier_mix[key] = tier_mix.get(key, 0) + 1
        rows.append({
            "day": step["day"],
            "label": step["label"],
            "note": step["note"],
            "shifted_share_planned": step["shifted_share"],
            "sample_size": len(sample),
            "shifted_items_in_sample":
                sum(1 for i in sample if i["population"] == "shifted"),
            "work_type_mix": dict(sorted(mix.items())),
            "tier_mix": dict(sorted(tier_mix.items())),
            "live": live,
            "frozen": frozen_result,
        })

    base_live = rows[0]["live"]
    base_frozen = rows[0]["frozen"]
    for row in rows:
        deltas = {}
        for name, section, field in TRACKED_RATES:
            start = dig(base_live, section, field)
            now = dig(row["live"], section, field)
            deltas[name] = {
                "acceptance": start, "day_n": now,
                "change_percentage_points":
                    None if start is None or now is None
                    else round((now - start) * 100, 2),
            }
        for name, section, field in TRACKED_LEVELS:
            start = dig(base_live, section, field)
            now = dig(row["live"], section, field)
            deltas[name] = {
                "acceptance": start, "day_n": now,
                "change_percent_of_baseline":
                    None if not start else round((now - start) / start * 100, 2),
            }
        deltas["open_exposure_items"] = {
            "acceptance": base_live["rework"]["open_exposure"]["items"],
            "day_n": row["live"]["rework"]["open_exposure"]["items"],
        }
        row["live_distribution_drift"] = deltas

        frozen_deltas = {}
        for name, section, field in TRACKED_RATES:
            start = dig(base_frozen, section, field)
            now = dig(row["frozen"], section, field)
            frozen_deltas[name] = {
                "acceptance": start, "day_n": now,
                "change_percentage_points":
                    None if start is None or now is None
                    else round((now - start) * 100, 2),
            }
        row["frozen_set_drift"] = frozen_deltas

    return {
        "threshold": threshold,
        "steps": rows,
        "frozen_set_note": (
            "Zero at every step by construction. This simulation changes the input "
            "distribution and nothing else, so the same decision policy scores the "
            "same frozen items identically at every step. A real frozen-set drift "
            "figure needs a real system measured twice, ninety days apart, and none "
            "has been."),
    }


def render_markdown(runs: dict, manifest: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("Simulation output over synthetic ground truth, scored with the dataset's "
        "synthetic reference decision policy. Not a measurement of any system.")
    add("")
    for threshold, payload in sorted(runs.items()):
        add(f"### Threshold {float(threshold):.2f}")
        add("")
        add("| Day | Step | Shifted share of sample % | Sample size | "
            "Automation rate % | Wrong automations | Rework min per 1,000 automated | "
            "Open exposure items | Reviewer min per 1,000 items | "
            "Net cost per item, INR |")
        add("|---|---|---|---|---|---|---|---|---|---|")
        for row in payload["steps"]:
            live = row["live"]
            add(f"| {row['day']} | {row['label']} | "
                f"{row['shifted_share_planned'] * 100:.0f} | "
                f"{row['sample_size']:,} | "
                f"{live['rates']['automation_rate'] * 100:.1f} | "
                f"{live['counts']['automated_wrong']:,} | "
                f"{live['rework']['minutes_per_1000_automated']:,.1f} | "
                f"{live['rework']['open_exposure']['items']:,} | "
                f"{live['reviewer_minutes']['per_1000_items_admitted']:,.1f} | "
                f"{live['cost']['net_cost_per_item_inr']:,.4f} |")
        add("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", default=str(HERE / "ground-truth.jsonl"))
    parser.add_argument("--labour-model", default=str(HERE / "labour-model.yaml"))
    parser.add_argument("--manifest", default=str(HERE / "manifest.json"))
    parser.add_argument("--thresholds", type=float, nargs="*", default=None)
    parser.add_argument("--audit-seed", default="20260902")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    items = load_items(Path(args.items))
    labour = load_labour_model(Path(args.labour_model))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    thresholds = args.thresholds or [float(t) for t in
                                     labour["scoring"]["confidence_thresholds"]]

    runs = {str(t): run(items, labour, manifest, t, args.audit_seed)
            for t in thresholds}

    payload = {
        "suite": "exception-economics",
        "artefact": "ninety-day drift simulation",
        "simulation": True,
        "simulation_version": SIMULATION_VERSION,
        "scorer_version": SCORER_VERSION,
        "charter_version": CHARTER_VERSION,
        "dataset_version": manifest["dataset_version"],
        "dataset_seed": manifest["seed"],
        "ground_truth_sha256": manifest.get("ground_truth_sha256"),
        "synthetic_ground_truth": True,
        "decision_policy": "reference decision policy (synthetic, dataset property)",
        "decision_policy_is_a_model_run": False,
        "drift_sample_size": manifest.get("drift_sample_size"),
        "drift_steps": manifest["drift_steps"],
        "runs": runs,
    }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}")

    print(render_markdown(runs, manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
