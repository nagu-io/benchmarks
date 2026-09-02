#!/usr/bin/env python3
"""Validation for the Exception Economics dataset v1.0.0.

Exits non-zero if anything is wrong. Checks, in order:

  1.  counts, populations, splits and the manifest agree with the file on disk
  2.  every tier assignment is verifiable from the item's own recorded parameters
      (charter 4.1.2 and 4.1.3), not merely asserted by the label
  3.  every identifier is format-shaped and invalid by construction (charter 6.3)
  4.  the shifted population is tier 5 only and uses only unseen categories, and no
      baseline item uses one (charter 4.4)
  5.  the error class stored on each item is the one `outcomes.classify_error`
      derives, so the generator and the scorer cannot disagree about pricing
  6.  every labour-model key the dataset refers to exists
  7.  every money figure in the labour model is marked a placeholder, and every
      minute figure states its basis (the rule that stops a modelled minute being
      read as a measured one)
  8.  error classes with no detection route carry no minutes at all (charter 3.15.3)
  9.  the ground-truth file hash matches the manifest
  10. regeneration from the seed reproduces the file byte for byte

Usage:
    python3 validate.py
    python3 validate.py --skip-regenerate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

import generate as gen
from outcomes import classify_error

HERE = Path(__file__).resolve().parent

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, message: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", default=str(HERE / "ground-truth.jsonl"))
    parser.add_argument("--labour-model", default=str(HERE / "labour-model.yaml"))
    parser.add_argument("--manifest", default=str(HERE / "manifest.json"))
    parser.add_argument("--skip-regenerate", action="store_true")
    args = parser.parse_args(argv)

    items_path = Path(args.items)
    items = [json.loads(line) for line in items_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    labour = yaml.safe_load(Path(args.labour_model).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    # 1. Counts -----------------------------------------------------------------
    check(len(items) == gen.TOTAL_ITEMS,
          f"expected {gen.TOTAL_ITEMS} items, found {len(items)}")
    check(manifest["items"] == len(items), "manifest item count disagrees with the file")
    populations = {}
    for item in items:
        populations[item["population"]] = populations.get(item["population"], 0) + 1
    check(populations.get("baseline") == gen.BASELINE_ITEMS,
          f"baseline population is {populations.get('baseline')}, "
          f"expected {gen.BASELINE_ITEMS}")
    check(populations.get("shifted") == gen.SHIFTED_ITEMS,
          f"shifted population is {populations.get('shifted')}, "
          f"expected {gen.SHIFTED_ITEMS}")
    ids = [i["item_id"] for i in items]
    check(len(set(ids)) == len(ids), "item ids are not unique")

    splits = {}
    for item in items:
        splits[item["split"]] = splits.get(item["split"], 0) + 1
    for name, size in gen.SPLIT_PLAN.items():
        check(splits.get(name) == size,
              f"split {name} has {splits.get(name)} items, expected {size}")

    # 2. Tier assignment verifiable from recorded parameters ---------------------
    for item in items:
        tier = item["tier"]
        params = item["tier_parameters"]
        lo, hi = gen.SOURCE_COUNT[tier]
        check(lo <= params["sources_to_reconcile"] <= hi,
              f"{item['item_id']}: sources {params['sources_to_reconcile']} outside "
              f"tier {tier} range {lo}-{hi}")
        check(params["key_availability"] == gen.KEY_AVAILABILITY[tier],
              f"{item['item_id']}: key availability does not match tier {tier}")
        check(params["match_cardinality"] == gen.MATCH_CARDINALITY[tier],
              f"{item['item_id']}: match cardinality does not match tier {tier}")
        check(params["ground_truth_basis"] == gen.GROUND_TRUTH_BASIS[tier],
              f"{item['item_id']}: ground truth basis does not match tier {tier}")
        check(params["tolerance_rules"] == gen.TOLERANCE_RULES[tier],
              f"{item['item_id']}: tolerance rules do not match tier {tier}")
        check(params["rule_order_dependent"] == (tier >= 4),
              f"{item['item_id']}: rule order dependence does not match tier {tier}")

    # 3. Identifiers invalid by construction ------------------------------------
    for item in items:
        attrs = item["attributes"]
        if "identity_number" in attrs:
            pan = attrs["identity_number"]
            check(len(pan) == 10 and pan[3] == "X",
                  f"{item['item_id']}: identity number {pan} is not invalid by "
                  f"construction (position 4 must be X)")
        if "vendor_tax_id" in attrs:
            gstin = attrs["vendor_tax_id"]
            check(gstin.startswith("00"),
                  f"{item['item_id']}: tax id {gstin} does not start with the "
                  f"unallocated state code 00")
            check(gstin[5] == "X",
                  f"{item['item_id']}: tax id {gstin} embeds a structurally possible "
                  f"holder-type letter")
        if "document_number" in attrs:
            check("-ZZ" in attrs["document_number"],
                  f"{item['item_id']}: document number lacks the reserved ZZ block")

    # 4. Shifted population ------------------------------------------------------
    for item in items:
        if item["population"] == "shifted":
            check(item["tier"] == 5,
                  f"{item['item_id']}: shifted items must be tier 5 (charter 4.4.2)")
            check(item["shift_driver"] in gen.SHIFT_PLAN,
                  f"{item['item_id']}: unknown shift driver {item['shift_driver']}")
            check(item["tier_parameters"]["unseen_category"] is True,
                  f"{item['item_id']}: shifted item not marked unseen_category")
        else:
            check(item["shift_driver"] is None,
                  f"{item['item_id']}: baseline item carries a shift driver")
            if item["work_type"] == "ticket_triage":
                check(item["ground_truth"]["category"] in gen.BASELINE_TICKET_CATEGORIES,
                      f"{item['item_id']}: baseline ticket uses an unseen category")
            if item["work_type"] == "invoice_po_recon":
                check(item["attributes"]["vendor_format"] in gen.BASELINE_VENDOR_FORMATS,
                      f"{item['item_id']}: baseline invoice uses an unseen format")

    shifted_categories = set()
    for item in items:
        if item["population"] == "shifted" and item["work_type"] == "ticket_triage":
            shifted_categories.add(item["ground_truth"]["category"])
    check(shifted_categories.issubset(set(gen.SHIFTED_TICKET_CATEGORIES)),
          "a shifted ticket uses a category from the baseline distribution")
    check(len(shifted_categories) >= 1,
          "no shifted ticket category is present, so tier 5 has no unseen category")

    # 5. Error class agrees with the shared classifier ---------------------------
    for item in items:
        stored = item["labour_keys"]["error_class_if_wrong"]
        proposed = item["reference_policy"]["proposed_outcome"]
        if proposed is None:
            check(stored is None,
                  f"{item['item_id']}: processing failure carries an error class")
            continue
        derived = classify_error(item["work_type"], item["ground_truth"]["outcome"],
                                 proposed, item["attributes"])
        check(stored == derived,
              f"{item['item_id']}: stored error class {stored} disagrees with the "
              f"classifier's {derived}")
        check(item["reference_policy"]["correct"] == (derived is None),
              f"{item['item_id']}: correctness flag disagrees with the classifier")

    # 6. Labour model keys exist -------------------------------------------------
    exception_types = labour["reviewer_minutes"]["exception_types"]
    error_classes = labour["rework_minutes"]["error_classes"]
    for item in items:
        keys = item["labour_keys"]
        check(keys["exception_type_if_routed"] in exception_types,
              f"{item['item_id']}: exception type "
              f"{keys['exception_type_if_routed']} is not in the labour model")
        if keys["error_class_if_wrong"]:
            check(keys["error_class_if_wrong"] in error_classes,
                  f"{item['item_id']}: error class {keys['error_class_if_wrong']} is "
                  f"not in the labour model")
    for work_type in ("ticket_triage", "kyc_case", "invoice_po_recon"):
        check(work_type in labour["audit_minutes"]["per_audited_item"],
              f"labour model has no audit minutes for {work_type}")
        check(work_type in labour["manual_handling_minutes"],
              f"labour model has no manual handling minutes for {work_type}")

    # 7. Money is placeholder, minutes state a basis ------------------------------
    for group in ("reviewer_cost", "machine_cost"):
        for name, entry in labour[group].items():
            check("placeholder" in str(entry.get("status", "")).lower(),
                  f"labour model {group}.{name} is not marked a placeholder")
            check(bool(entry.get("basis")),
                  f"labour model {group}.{name} states no basis")
    check(bool(labour["reviewer_minutes"]["tier_multiplier"].get("basis")),
          "tier multipliers state no basis")
    for name, spec in exception_types.items():
        check(bool(spec.get("basis")), f"exception type {name} states no basis")
        check("modelling assumption" in spec["basis"].lower(),
              f"exception type {name} does not say its minutes are a modelling "
              f"assumption, and no measured source is cited")
    check(bool(labour["audit_minutes"].get("basis")), "audit minutes state no basis")
    check(bool(labour["manual_handling_minutes"].get("basis")),
          "manual handling minutes state no basis")
    check(labour["status"]["measured_figures_in_this_file"] == 0,
          "the labour model claims a measured figure; none has been measured")

    # 8. Unpriced classes carry no minutes ---------------------------------------
    unpriced = 0
    for name, spec in error_classes.items():
        check(bool(spec.get("basis")), f"error class {name} states no basis")
        if spec["detection_route"] == "none_within_window":
            unpriced += 1
            for field in ("detect_minutes", "correct_minutes", "downstream_minutes"):
                check(spec[field] is None,
                      f"error class {name} has no detection route but carries "
                      f"{field}; charter 3.15.3 forbids an estimated minute figure")
        else:
            for field in ("detect_minutes", "correct_minutes", "downstream_minutes"):
                check(isinstance(spec[field], (int, float)),
                      f"error class {name} is priced but {field} is not a number")
    check(unpriced >= 1,
          "no error class has an absent detection route; the open exposure count "
          "would then never be exercised")

    # 9. Hash --------------------------------------------------------------------
    digest = hashlib.sha256(items_path.read_bytes()).hexdigest()
    check(digest == manifest.get("ground_truth_sha256"),
          f"ground truth sha256 {digest[:16]} does not match the manifest's "
          f"{str(manifest.get('ground_truth_sha256'))[:16]}")

    # 10. Determinism ------------------------------------------------------------
    if not args.skip_regenerate:
        regenerated, _ = gen.generate(int(manifest["seed"]))
        blob = "".join(json.dumps(i, sort_keys=True, ensure_ascii=False) + "\n"
                       for i in regenerated)
        check(hashlib.sha256(blob.encode("utf-8")).hexdigest() == digest,
              "regenerating from the seed does not reproduce the file byte for byte")

    print(f"checks run: {CHECKS}")
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}")
        for failure in FAILURES[:40]:
            print(f"  - {failure}")
        if len(FAILURES) > 40:
            print(f"  ... and {len(FAILURES) - 40} more")
        return 1
    print("all checks passed")
    print(f"items {len(items)} · baseline {populations.get('baseline')} · "
          f"shifted {populations.get('shifted')} · "
          f"unpriced error classes {unpriced} · sha256 {digest[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
