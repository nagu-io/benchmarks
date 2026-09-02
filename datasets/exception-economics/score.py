#!/usr/bin/env python3
"""Exception Economics scorer v1.0.0.

Computes, per `10-benchmarks/charter/methodology.md`:

  automation rate                    charter 3.14
  wrong-automation rework minutes    charter 3.15, per 1,000 automated items
  reviewer minutes per exception     charter 3.16, mean and median by entry code
  reviewer minutes per 1,000 items   the same figure over items admitted
  net cost per item                  charter 3.15.6, at three confidence thresholds
  the threshold that minimises net cost, from a sweep

No model API is used and none is needed. Every figure above is arithmetic over
labelled ground truth and the labour model in `labour-model.yaml`. What this suite
scores is a decision policy over labelled items: for each item, does the policy
automate it or route it to a person, and when it automates, is it right. That is a
property of a policy and a threshold, not of a language model, which is why it runs
in an environment with no network and no keys.

Two sources of a decision policy:

  1. The reference policy carried in the dataset. Synthetic, generated with each item.
     It is a property of the dataset and it is not a measurement of any system. Every
     table this scorer prints says so.

  2. A real system's predictions, supplied with --predictions. The interface is one
     JSON object per line:

         {"item_id": "EE-0001",
          "proposed_outcome": "recon:matched:PO-446576",
          "confidence": 0.91,
          "processing_failure": false,
          "validation_failure": false,
          "policy_flag": false}

     `proposed_outcome` uses the encoding in `outcomes.py`. The three boolean fields
     are optional and default to false. An item absent from the predictions file is
     reported as a processing failure, never silently dropped (charter 3.1.2).

Usage:
    python3 score.py
    python3 score.py --thresholds 0.80 0.90 0.95 --out ../../results/…/scores.json
    python3 score.py --predictions runs/vendor-a.jsonl --label "Vendor A"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

import yaml

from outcomes import classify_error

HERE = Path(__file__).resolve().parent
SCORER_VERSION = "1.0.0"
CHARTER_VERSION = "1.0.0"

ENTRY_CODES = ["LOWCONF", "VALFAIL", "FLAG", "FAIL", "DRIFT", "AUDIT"]
EXCLUDED_LIFECYCLES = {"pre_processing_rejected", "upstream_failure", "in_flight"}

REFERENCE_POLICY_LABEL = "reference decision policy (synthetic, dataset property)"


# --------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------

def load_items(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_labour_model(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_predictions(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            out[row["item_id"]] = row
    return out


def stable_uniform(*parts: str) -> float:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) / float(1 << 64)


# --------------------------------------------------------------------------------
# Labour model lookups
# --------------------------------------------------------------------------------

def tier_multiplier(labour: dict, tier: int) -> float:
    return float(labour["reviewer_minutes"]["tier_multiplier"][f"t{tier}"])


def exception_type_for(work_type: str, entry_code: str) -> str:
    prefix = {"ticket_triage": "ticket", "kyc_case": "kyc",
              "invoice_po_recon": "recon"}[work_type]
    suffix = {"LOWCONF": "low_confidence", "VALFAIL": "validation_failure",
              "FLAG": "policy_flag", "FAIL": "processing_failure",
              "DRIFT": "drift_review", "AUDIT": "low_confidence"}[entry_code]
    return f"{prefix}_{suffix}"


def reviewer_minutes_for(labour: dict, work_type: str, tier: int,
                         entry_code: str) -> tuple[float, bool]:
    spec = labour["reviewer_minutes"]["exception_types"][
        exception_type_for(work_type, entry_code)]
    minutes = float(spec["base_minutes"]) * tier_multiplier(labour, tier)
    return minutes, bool(spec.get("senior", False))


def rework_for(labour: dict, error_class: str) -> tuple[float | None, str]:
    spec = labour["rework_minutes"]["error_classes"][error_class]
    if spec["detection_route"] == "none_within_window":
        return None, spec["detection_route"]
    minutes = (float(spec["detect_minutes"]) + float(spec["correct_minutes"])
               + float(spec["downstream_minutes"]))
    return minutes, spec["detection_route"]


# --------------------------------------------------------------------------------
# Scoring one threshold
# --------------------------------------------------------------------------------

def decision_for(item: dict, predictions: dict | None) -> dict:
    """The decision policy's output for this item, from predictions if supplied and
    from the dataset's reference policy otherwise."""
    if predictions is None:
        rp = item["reference_policy"]
        return {
            "proposed_outcome": rp["proposed_outcome"],
            "confidence": rp["confidence"],
            "processing_failure": bool(rp["processing_failure"]),
            "validation_failure": bool(rp["validation_failure"]),
            "policy_flag": bool(rp["policy_flag"]),
            "missing": False,
        }
    row = predictions.get(item["item_id"])
    if row is None:
        # Charter 3.1.2: nothing is silently dropped. An item with no prediction is a
        # processing failure and is counted as one.
        return {"proposed_outcome": None, "confidence": None,
                "processing_failure": True, "validation_failure": False,
                "policy_flag": False, "missing": True}
    return {
        "proposed_outcome": row.get("proposed_outcome"),
        "confidence": row.get("confidence"),
        "processing_failure": bool(row.get("processing_failure", False))
                              or row.get("proposed_outcome") is None,
        "validation_failure": bool(row.get("validation_failure", False)),
        "policy_flag": bool(row.get("policy_flag", False)),
        "missing": False,
    }


def score(items: list[dict], labour: dict, threshold: float,
          predictions: dict | None = None, audit_seed: str = "20260902") -> dict:
    """Score one confidence threshold. Pure arithmetic over ground truth."""
    audit_rate = float(labour["scoring"]["audit_sample_rate"]["value"])
    inr_min = float(labour["reviewer_cost"]["inr_per_hour"]["value"]) / 60.0
    usd_min = float(labour["reviewer_cost"]["usd_per_hour"]["value"]) / 60.0
    senior_mult = float(labour["reviewer_cost"]["senior_reviewer_multiplier"]["value"])
    machine_inr = float(labour["machine_cost"]["per_item_inr"]["value"])
    machine_usd = float(labour["machine_cost"]["per_item_usd"]["value"])

    excluded = {name: 0 for name in sorted(EXCLUDED_LIFECYCLES)}
    admitted = []
    for item in items:
        if item["lifecycle"] in EXCLUDED_LIFECYCLES:
            excluded[item["lifecycle"]] += 1
        else:
            admitted.append(item)

    automated = 0
    automated_wrong = 0
    audited = 0
    audit_corrected = 0
    audit_minutes_total = 0.0
    manual_handling_minutes = 0.0
    missing_predictions = 0

    entry_counts = {code: 0 for code in ENTRY_CODES}
    reviewer_minutes_by_code: dict[str, list[float]] = {c: [] for c in ENTRY_CODES}
    reviewer_cost_inr = 0.0
    reviewer_cost_usd = 0.0

    rework_minutes_total = 0.0
    rework_by_class: dict[str, dict] = {}
    open_exposure: dict[str, int] = {}

    by_tier: dict[int, dict] = {}
    by_work_type: dict[str, dict] = {}
    by_population: dict[str, dict] = {}

    def bump(bucket: dict, key, field: str, amount: float = 1.0) -> None:
        row = bucket.setdefault(key, {"admitted": 0, "automated": 0,
                                      "automated_wrong": 0, "exceptions": 0,
                                      "reviewer_minutes": 0.0,
                                      "rework_minutes": 0.0,
                                      "open_exposure": 0})
        row[field] += amount

    for item in admitted:
        tier = item["tier"]
        work_type = item["work_type"]
        population = item["population"]
        for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                            (by_population, population)):
            bump(bucket, key, "admitted")

        decision = decision_for(item, predictions)
        if decision["missing"]:
            missing_predictions += 1

        if decision["processing_failure"]:
            entry_code = "FAIL"
        elif decision["validation_failure"]:
            entry_code = "VALFAIL"
        elif decision["policy_flag"]:
            entry_code = "FLAG"
        elif decision["confidence"] is not None and decision["confidence"] >= threshold:
            entry_code = None
        else:
            entry_code = "LOWCONF"

        wrong = False
        error_class = None
        if entry_code is None:
            error_class = classify_error(work_type, item["ground_truth"]["outcome"],
                                         decision["proposed_outcome"],
                                         item["attributes"])
            wrong = error_class is not None

            # Sampled audit. Charter 3.4.2 and 3.14.3: an audited item stays automated
            # if the audit changed nothing, and becomes an exception if it did.
            in_audit = stable_uniform(audit_seed, "audit", item["item_id"]) < audit_rate
            if in_audit:
                audited += 1
                audit_minutes_total += float(
                    labour["audit_minutes"]["per_audited_item"][work_type])
                if wrong:
                    audit_corrected += 1
                    entry_code = "AUDIT"

        if entry_code is None:
            automated += 1
            for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                                (by_population, population)):
                bump(bucket, key, "automated")
            if wrong:
                automated_wrong += 1
                for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                                    (by_population, population)):
                    bump(bucket, key, "automated_wrong")
                minutes, route = rework_for(labour, error_class)
                row = rework_by_class.setdefault(
                    error_class, {"items": 0, "minutes": 0.0, "detection_route": route,
                                  "priced": minutes is not None})
                row["items"] += 1
                if minutes is None:
                    open_exposure[error_class] = open_exposure.get(error_class, 0) + 1
                    for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                                        (by_population, population)):
                        bump(bucket, key, "open_exposure")
                else:
                    row["minutes"] += minutes
                    rework_minutes_total += minutes
                    for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                                        (by_population, population)):
                        bump(bucket, key, "rework_minutes", minutes)
            continue

        # The item is an exception.
        entry_counts[entry_code] += 1
        minutes, senior = reviewer_minutes_for(labour, work_type, tier, entry_code)
        reviewer_minutes_by_code[entry_code].append(minutes)
        multiplier = senior_mult if senior else 1.0
        reviewer_cost_inr += minutes * inr_min * multiplier
        reviewer_cost_usd += minutes * usd_min * multiplier
        for bucket, key in ((by_tier, tier), (by_work_type, work_type),
                            (by_population, population)):
            bump(bucket, key, "exceptions")
            bump(bucket, key, "reviewer_minutes", minutes)
        if entry_code == "FAIL":
            manual_handling_minutes += float(
                labour["manual_handling_minutes"][work_type])

    n_admitted = len(admitted)
    exceptions = sum(entry_counts.values())
    all_reviewer_minutes = [m for code in ENTRY_CODES
                            for m in reviewer_minutes_by_code[code]]
    reviewer_minutes_total = sum(all_reviewer_minutes)

    rework_cost_inr = rework_minutes_total * inr_min
    rework_cost_usd = rework_minutes_total * usd_min
    machine_cost_inr_total = machine_inr * n_admitted
    machine_cost_usd_total = machine_usd * n_admitted

    net_inr = (reviewer_cost_inr + rework_cost_inr + machine_cost_inr_total)
    net_usd = (reviewer_cost_usd + rework_cost_usd + machine_cost_usd_total)

    def per_code_stats(code: str) -> dict:
        values = reviewer_minutes_by_code[code]
        return {
            "exceptions": len(values),
            "mean_minutes": round(statistics.fmean(values), 2) if values else None,
            "median_minutes": round(statistics.median(values), 2) if values else None,
            "total_minutes": round(sum(values), 1),
        }

    return {
        "threshold": threshold,
        "scorer_version": SCORER_VERSION,
        "charter_version": CHARTER_VERSION,
        "counts": {
            "items_received": len(items),
            "items_admitted": n_admitted,
            "excluded": excluded,
            "automated": automated,
            "automated_wrong": automated_wrong,
            "exceptions": exceptions,
            "audited": audited,
            "audit_corrected": audit_corrected,
            "missing_predictions": missing_predictions,
            "entry_codes": dict(entry_counts),
        },
        "rates": {
            "automation_rate": automated / n_admitted if n_admitted else None,
            "exception_rate": exceptions / n_admitted if n_admitted else None,
            "identity_holds": abs((automated + exceptions) - n_admitted) == 0,
            "wrong_automation_rate_of_automated":
                automated_wrong / automated if automated else None,
            "audit_rate_of_automated":
                audited / (automated + audit_corrected) if (automated + audit_corrected) else None,
        },
        "reviewer_minutes": {
            "total": round(reviewer_minutes_total, 1),
            "mean_per_exception":
                round(statistics.fmean(all_reviewer_minutes), 2)
                if all_reviewer_minutes else None,
            "median_per_exception":
                round(statistics.median(all_reviewer_minutes), 2)
                if all_reviewer_minutes else None,
            "per_1000_items_admitted":
                round(reviewer_minutes_total / n_admitted * 1000, 1) if n_admitted else None,
            "by_entry_code": {code: per_code_stats(code) for code in ENTRY_CODES},
        },
        "audit_minutes": {
            "total": round(audit_minutes_total, 1),
            "note": ("Reported separately from reviewer minutes and excluded from net "
                     "cost, per charter 3.16.5. An audit is a measurement device."),
        },
        "manual_handling_minutes": {
            "total": round(manual_handling_minutes, 1),
            "note": ("Time to complete by hand the items the system could not process. "
                     "Reported separately and not included in net cost, which follows "
                     "the charter's composition of reviewer time plus rework plus "
                     "machine cost."),
        },
        "rework": {
            "minutes_total": round(rework_minutes_total, 1),
            "minutes_per_1000_automated":
                round(rework_minutes_total / automated * 1000, 1) if automated else None,
            "by_error_class": {
                k: {"items": v["items"], "minutes": round(v["minutes"], 1),
                    "detection_route": v["detection_route"], "priced": v["priced"]}
                for k, v in sorted(rework_by_class.items())
            },
            "open_exposure": {
                "items": sum(open_exposure.values()),
                "by_class": dict(sorted(open_exposure.items())),
                "note": ("Wrong automations in error classes with no detection route "
                         "inside the measurement window. Counted, named and never "
                         "assigned a minute figure, per charter 3.15.3."),
            },
        },
        "cost": {
            "basis": ("Two independent placeholder reviewer rates. No exchange rate is "
                      "applied and none should be inferred. Machine cost per item is "
                      "zero because no system has been run against this dataset."),
            "reviewer_rate_inr_per_hour":
                labour["reviewer_cost"]["inr_per_hour"]["value"],
            "reviewer_rate_usd_per_hour":
                labour["reviewer_cost"]["usd_per_hour"]["value"],
            "rate_status": "placeholder — replace",
            "reviewer_cost_inr": round(reviewer_cost_inr, 2),
            "reviewer_cost_usd": round(reviewer_cost_usd, 2),
            "rework_cost_inr": round(rework_cost_inr, 2),
            "rework_cost_usd": round(rework_cost_usd, 2),
            "machine_cost_inr": round(machine_cost_inr_total, 2),
            "machine_cost_usd": round(machine_cost_usd_total, 2),
            "net_cost_inr": round(net_inr, 2),
            "net_cost_usd": round(net_usd, 2),
            "net_cost_per_item_inr": round(net_inr / n_admitted, 4) if n_admitted else None,
            "net_cost_per_item_usd": round(net_usd / n_admitted, 4) if n_admitted else None,
            "net_labour_minutes_per_item":
                round((reviewer_minutes_total + rework_minutes_total) / n_admitted, 3)
                if n_admitted else None,
        },
        "breakdowns": {
            "by_tier": {str(k): finish_bucket(v) for k, v in sorted(by_tier.items())},
            "by_work_type": {k: finish_bucket(v) for k, v in sorted(by_work_type.items())},
            "by_population": {k: finish_bucket(v) for k, v in sorted(by_population.items())},
        },
    }


def finish_bucket(row: dict) -> dict:
    out = dict(row)
    out["reviewer_minutes"] = round(row["reviewer_minutes"], 1)
    out["rework_minutes"] = round(row["rework_minutes"], 1)
    out["automation_rate"] = (row["automated"] / row["admitted"]
                              if row["admitted"] else None)
    out["wrong_automation_rate_of_automated"] = (
        row["automated_wrong"] / row["automated"] if row["automated"] else None)
    return out


# --------------------------------------------------------------------------------
# Sweep
# --------------------------------------------------------------------------------

def sweep(items: list[dict], labour: dict, predictions: dict | None = None,
          audit_seed: str = "20260902") -> dict:
    cfg = labour["scoring"]["threshold_sweep"]
    start, stop, step = float(cfg["start"]), float(cfg["stop"]), float(cfg["step"])
    points = []
    t = start
    while t <= stop + 1e-9:
        result = score(items, labour, round(t, 4), predictions, audit_seed)
        points.append({
            "threshold": round(t, 2),
            "automation_rate": result["rates"]["automation_rate"],
            "net_cost_per_item_inr": result["cost"]["net_cost_per_item_inr"],
            "net_cost_per_item_usd": result["cost"]["net_cost_per_item_usd"],
            "net_labour_minutes_per_item": result["cost"]["net_labour_minutes_per_item"],
            "reviewer_minutes_per_1000_items":
                result["reviewer_minutes"]["per_1000_items_admitted"],
            "rework_minutes_per_1000_automated":
                result["rework"]["minutes_per_1000_automated"],
            "open_exposure_items": result["rework"]["open_exposure"]["items"],
        })
        t += step
    best = min(points, key=lambda p: (p["net_cost_per_item_inr"], p["threshold"]))
    return {"points": points, "minimising_threshold": best["threshold"], "best": best}


# --------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------

def pct(value) -> str:
    return "not run" if value is None else f"{value * 100:.1f}"


def num(value, places: int = 2) -> str:
    return "not run" if value is None else f"{value:,.{places}f}"


def render_markdown(results: list[dict], swept: dict, label: str,
                    manifest: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"Decision policy scored: {label}")
    add("")
    add(f"Dataset version {manifest['dataset_version']} · seed {manifest['seed']} · "
        f"ground truth sha256 {manifest.get('ground_truth_sha256', 'unknown')[:16]} · "
        f"scorer {SCORER_VERSION} · charter {CHARTER_VERSION}")
    add("")
    add("| Threshold | Items admitted | Automation rate % | Wrong automations | "
        "Rework min per 1,000 automated | Open exposure items | "
        "Reviewer min per 1,000 items | Net cost per item, INR | Net cost per item, USD |")
    add("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        add(f"| {r['threshold']:.2f} | {r['counts']['items_admitted']:,} | "
            f"{pct(r['rates']['automation_rate'])} | "
            f"{r['counts']['automated_wrong']:,} | "
            f"{num(r['rework']['minutes_per_1000_automated'], 1)} | "
            f"{r['rework']['open_exposure']['items']:,} | "
            f"{num(r['reviewer_minutes']['per_1000_items_admitted'], 1)} | "
            f"{num(r['cost']['net_cost_per_item_inr'], 4)} | "
            f"{num(r['cost']['net_cost_per_item_usd'], 4)} |")
    add("")
    add(f"Net cost per item is minimised at threshold {swept['minimising_threshold']:.2f} "
        f"over the sweep {swept['points'][0]['threshold']:.2f} to "
        f"{swept['points'][-1]['threshold']:.2f}.")
    return "\n".join(lines)


# --------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", default=str(HERE / "ground-truth.jsonl"))
    parser.add_argument("--labour-model", default=str(HERE / "labour-model.yaml"))
    parser.add_argument("--manifest", default=str(HERE / "manifest.json"))
    parser.add_argument("--predictions", default=None,
                        help="JSONL of a real system's predictions. See module docstring.")
    parser.add_argument("--label", default=None,
                        help="Name of the decision policy being scored.")
    parser.add_argument("--thresholds", type=float, nargs="*", default=None)
    parser.add_argument("--population", choices=["all", "baseline", "shifted"],
                        default="baseline")
    parser.add_argument("--split", default=None,
                        choices=["public_sample", "private_holdout", "open"])
    parser.add_argument("--audit-seed", default="20260902")
    parser.add_argument("--no-sweep", action="store_true")
    parser.add_argument("--out", default=None, help="Write the full result as JSON.")
    args = parser.parse_args(argv)

    items = load_items(Path(args.items))
    labour = load_labour_model(Path(args.labour_model))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    predictions = load_predictions(Path(args.predictions)) if args.predictions else None
    label = args.label or (Path(args.predictions).stem if args.predictions
                           else REFERENCE_POLICY_LABEL)

    if args.population != "all":
        items = [i for i in items if i["population"] == args.population]
    if args.split:
        items = [i for i in items if i["split"] == args.split]

    thresholds = args.thresholds or [float(t) for t in
                                     labour["scoring"]["confidence_thresholds"]]
    results = [score(items, labour, t, predictions, args.audit_seed)
               for t in thresholds]

    for r in results:
        if not r["rates"]["identity_holds"]:
            raise SystemExit("automation rate plus exception rate does not equal one; "
                             "the counts do not reconcile (charter 3.5.3)")

    swept = ({"points": [], "minimising_threshold": None, "best": None}
             if args.no_sweep else sweep(items, labour, predictions, args.audit_seed))

    payload = {
        "suite": "exception-economics",
        "dataset_version": manifest["dataset_version"],
        "dataset_seed": manifest["seed"],
        "ground_truth_sha256": manifest.get("ground_truth_sha256"),
        "scorer_version": SCORER_VERSION,
        "charter_version": CHARTER_VERSION,
        "decision_policy": label,
        "decision_policy_is_a_model_run": predictions is not None,
        "population": args.population,
        "split": args.split,
        "synthetic_ground_truth": True,
        "labour_model_status": labour["status"],
        "thresholds": results,
        "sweep": swept,
    }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}")

    if not args.no_sweep:
        print(render_markdown(results, swept, label, manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
