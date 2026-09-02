#!/usr/bin/env python3
"""Messy Scan dataset v1.0 — document and ground-truth generator.

Builds 1,000 synthetic business documents with known-answer ground truth.
Everything is deterministic from ``--seed``: the same seed produces byte-identical
``build/documents.jsonl``.

Composition (see datasheet.md, section "Composition"):

    400  invoices          100 Indian GST, 100 US, 100 EU VAT, 100 Philippine BIR
    250  KYC packs         130 Aadhaar-style, 120 PAN-style; each pack carries a
                           passport data page with an ICAO 9303 machine-readable
                           zone and a utility bill used as address proof
    200  insurance claims   80 motor, 70 health, 50 property
    150  purchase orders    50 India, 40 US, 35 EU, 25 Philippines

Arithmetic
----------
All money is held as integer minor units (paise, cents, centavos). Line amount is
quantity x unit price; the subtotal is the sum of line amounts; tax is the stated
rate applied to the stated taxable base with round-half-up on minor units; the
total is the sum of its stated components. ``validate.py`` re-derives every one of
these independently and fails if any of them disagrees.

Identifiers: the checksum-failure guarantee
-------------------------------------------
Every identifier in this dataset is structurally plausible and deliberately
invalid. An extractor sees something that looks like the real thing; a checksum
validator rejects it. How each one is broken:

  Aadhaar-style number (12 digits)
      Real check: Verhoeff (dihedral group D5) over all 12 digits.
      Broken by: computing the correct 12th digit for the 11-digit payload, then
      emitting a different digit. First digit is kept in 2-9, which is the
      published structural rule for issued Aadhaar numbers, so the value stays
      plausible. Verhoeff has a single conventional formulation, so one
      substitution is enough.

  PAN-style number (AAAAA9999A)
      Real check: the Income Tax Department has never published the algorithm for
      the tenth character, so no validator can honestly assert "this check
      character is wrong". We therefore break two rules that ARE published:
        (a) the fourth character is the holder-type code and must be one of
            A B C F G H J L P T (E and K appear in some published lists; we avoid
            all twelve). We emit a code outside that set.
        (b) the fifth character is the first letter of the holder's surname or
            entity name. We emit a letter that is not that first letter.
      Both failures are checkable against the published PAN format and both are
      enforced by validate.py.

  GSTIN (15 characters)
      Real check: the published GSTN modulo-36 weighted check character.
      Broken by: computing the correct character under BOTH factor-parity
      conventions found in published implementations and emitting a character
      that differs from both. The two leading digits stay a real state code so
      the value stays plausible.

  IFSC (bank branch code, 11 characters)
      Real check: no checksum exists. The published RBI format requires the fifth
      character to be "0". Broken by: emitting a non-zero digit there.

  Payment card number (16 digits)
      Real check: Luhn (ISO/IEC 7812-1).
      Broken by: computing the correct Luhn check digit and emitting a different
      one. The leading digits stay in a plausible major-industry range.

  IBAN
      Real check: ISO 13616 / ISO 7064 MOD 97-10 (the rearranged string must be
      congruent to 1 modulo 97).
      Broken by: computing the correct two check digits and emitting a different
      pair, then confirming the result is not congruent to 1.

  EU VAT number (DE, FR, NL, IT)
      Real checks: DE is ISO 7064 MOD 11,10; FR is key = (12 + 3 x (SIREN mod 97))
      mod 97 over a Luhn-valid SIREN; NL is the weighted modulo-11 test over the
      nine digits; IT is the Luhn-style modulo-10 test over eleven digits.
      Broken by: computing the correct check value for each scheme and emitting a
      different one. For FR the SIREN is additionally made Luhn-invalid, so the
      number fails on two independent counts.

  US EIN (99-9999999)
      Real check: no checksum exists. The IRS publishes the list of campus
      prefixes it issues. Broken by: drawing the two-digit prefix from the
      complement of that list (07, 08, 09, 17, 18, 19, 28, 29, 49, 69, 70, 78,
      79, 89), so the number cannot be an issued EIN.

  ABA routing number (9 digits)
      Real check: the published 3-7-1 weighted modulo-10 test.
      Broken by: computing the correct ninth digit and emitting a different one.

  Passport number and MRZ (ICAO 9303 TD3)
      Real check: the 7-3-1 weighted modulo-10 check digits over the document
      number, date of birth, date of expiry, the optional-data field, and the
      composite.
      Broken by: computing every check digit correctly, then corrupting the
      document-number check digit and the composite check digit. The other check
      digits are left correct so the zone still parses; a conforming reader
      rejects the document on the two broken digits.

  VIN (17 characters, motor claims)
      Real check: the published position-9 modulo-11 transliteration check.
      Broken by: computing the correct character and emitting a different one.

  Philippine TIN, Indian utility consumer numbers, vehicle registrations, policy
  numbers, claim numbers, purchase-order numbers, invoice numbers
      No public check algorithm exists for any of these. We say so plainly rather
      than claim a guarantee we cannot make: these values are drawn from the
      seeded generator and carry no proof of invalidity. validate.py reports them
      in a separate class ("no public check available") and never counts them as
      passing a checksum-failure test. The Philippine TIN additionally fails a
      dataset-defined MOD 11-2 surrogate, which is documented for completeness
      and is not a claim about BIR's real algorithm.

How this generator is laid out
------------------------------
The generator is five files. This one holds the composition plan, the tier and split
allocation, and the assembly loop; the parts it draws on sit beside it, each small
enough to read in one sitting:

    identifiers.py   the real check-digit algorithms, and the ``make_*`` functions
                     that compute a correct value and then emit a broken one
    content.py       invented names, addresses and catalogue, and money formatting
    schemas.py       the field schema per document type, and the published check
                     rule each identifier field is broken against
    builders.py      one builder per subtype, plus the logical page plan

The split is a matter of file size only. ``render.py``, ``degrade.py`` and
``validate.py`` still import everything they need from this module, and the seed still
produces a byte-identical plan.

Names, addresses, people
------------------------
No real company names, no real addresses, no real people. Organisation names and
family names are assembled from syllable inventories in ``content.py``; street and
locality names are invented. City, state and country names are real, because a
document with an impossible city is not a realistic document. Postal codes are
plausible for the state shown. Any collision with a real organisation or person
is coincidental and unintended.

Usage
-----
    python3 generate.py --seed 20260902
    python3 generate.py --seed 20260902 --out build/documents.jsonl

Licence: MIT (code). Data produced by this script: CC BY 4.0.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from builders import BUILDERS, logical_pages
# BILINGUAL, DATE_DISPLAY and fmt_money are re-exported: render.py imports them from here,
# so the split stays invisible to the three scripts downstream of this one.
from content import (  # noqa: F401
    BILINGUAL, DATE_DISPLAY, LOCALE_SECOND_LANGUAGE, fmt_money, rng_for,
)
from schemas import IDENTIFIER_CHECKS, SCHEMAS  # noqa: F401

HERE = Path(__file__).resolve().parent
DATASET_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_SEED = 20260902
DEFAULT_PLAN_PATH = HERE / "build" / "documents.jsonl"

# --------------------------------------------------------------------------- #
# Composition plan                                                            #
# --------------------------------------------------------------------------- #

TYPE_PLAN: list[tuple[str, str, int]] = [
    # (doc_type, subtype, count)
    ("invoice", "invoice_in_gst", 100),
    ("invoice", "invoice_us", 100),
    ("invoice", "invoice_eu_vat", 100),
    ("invoice", "invoice_ph_bir", 100),
    ("kyc_pack", "kyc_aadhaar", 130),
    ("kyc_pack", "kyc_pan", 120),
    ("insurance_claim", "claim_motor", 80),
    ("insurance_claim", "claim_health", 70),
    ("insurance_claim", "claim_property", 50),
    ("purchase_order", "po_in", 50),
    ("purchase_order", "po_us", 40),
    ("purchase_order", "po_eu", 35),
    ("purchase_order", "po_ph", 25),
]

TYPE_PREFIX = {
    "invoice": "inv",
    "kyc_pack": "kyc",
    "insurance_claim": "clm",
    "purchase_order": "po",
}

# Tier shares. Stratified inside every subtype with largest-remainder rounding,
# so the global distribution is exact and every subtype is represented in every
# tier that its count allows.
TIER_SHARES = {1: 0.15, 2: 0.25, 3: 0.25, 4: 0.20, 5: 0.15}

SPLIT_SIZES = {"public_sample": 50, "private_holdout": 200}


# --------------------------------------------------------------------------- #
# Degradation plan                                                            #
# --------------------------------------------------------------------------- #

DESK_TONES = [(206, 198, 184), (176, 168, 158), (122, 116, 108), (231, 227, 220), (150, 143, 132)]
STAMP_KINDS = ["PAID", "RECEIVED", "APPROVED", "ENTERED IN LEDGER", "VERIFIED",
               "ORIGINAL FOR RECIPIENT", "DUPLICATE"]
HANDWRITING_SNIPPETS = [
    "chk with acct", "posted 12/6", "approved - RK", "ref PO?", "TDS?", "call vendor",
    "held for GRN", "part short", "pl verify tax", "entered", "ok to pay", "see note 3",
]


def degradation_plan(tier: int, rng: random.Random, page_count: int, locale: str) -> dict:
    if tier == 1:
        return {
            "tier": 1,
            "name": "clean digital",
            "render_dpi": 200,
            "colour_mode": "rgb",
            "output": {"pdf": "vector", "png": "lossless"},
            "operations": [],
        }
    if tier == 2:
        return {
            "tier": 2,
            "name": "flatbed scan",
            "render_dpi": 200,
            "colour_mode": "grey",
            "operations": ["skew", "paper_tone", "gaussian_noise", "blur", "dust", "lid_shadow",
                           "jpeg"],
            "skew_deg": round(rng.uniform(-1.6, 1.6), 3),
            "paper_grey": rng.randint(236, 250),
            "gaussian_noise_sigma": round(rng.uniform(2.5, 6.0), 2),
            "blur_sigma": round(rng.uniform(0.3, 0.75), 3),
            "contrast": round(rng.uniform(0.90, 1.08), 3),
            "brightness": round(rng.uniform(0.94, 1.06), 3),
            "dust_specks": rng.randint(12, 70),
            "lid_shadow_px": rng.randint(0, 16),
            "jpeg_quality": rng.randint(78, 93),
        }
    if tier == 3:
        return {
            "tier": 3,
            "name": "phone photo",
            "render_dpi": 200,
            "colour_mode": "rgb",
            "operations": ["perspective", "rotation", "shadow_gradient", "glare", "blur",
                           "noise", "white_balance", "desk_background", "jpeg"],
            "perspective_offsets_frac": [round(rng.uniform(0.004, 0.048), 4) for _ in range(8)],
            "rotation_deg": round(rng.uniform(-3.5, 3.5), 3),
            "shadow": {
                "axis": rng.choice(["x", "y", "diag"]),
                "strength": round(rng.uniform(0.18, 0.46), 3),
                "centre": round(rng.uniform(0.15, 0.85), 3),
            },
            "glare": {
                "cx": round(rng.uniform(0.15, 0.85), 3),
                "cy": round(rng.uniform(0.12, 0.80), 3),
                "radius_frac": round(rng.uniform(0.08, 0.24), 3),
                "intensity": round(rng.uniform(0.25, 0.72), 3),
            },
            "blur_sigma": round(rng.uniform(0.6, 1.9), 3),
            "gaussian_noise_sigma": round(rng.uniform(3.0, 9.0), 2),
            "white_balance": {"r": round(rng.uniform(0.96, 1.07), 3),
                              "g": round(rng.uniform(0.97, 1.03), 3),
                              "b": round(rng.uniform(0.93, 1.05), 3)},
            "desk_tone": list(DESK_TONES[rng.randrange(len(DESK_TONES))]),
            "margin_frac": round(rng.uniform(0.03, 0.11), 3),
            "jpeg_quality": rng.randint(58, 86),
        }
    if tier == 4:
        stamps = []
        for _ in range(rng.randint(1, 3)):
            stamps.append({
                "text": rng.choice(STAMP_KINDS),
                "cx": round(rng.uniform(0.20, 0.82), 3),
                "cy": round(rng.uniform(0.18, 0.86), 3),
                "rotation_deg": round(rng.uniform(-28, 28), 2),
                "scale": round(rng.uniform(0.72, 1.35), 3),
                "shape": rng.choice(["rect", "ellipse", "double_rect"]),
                "ink": rng.choice(["#1b3f8f", "#8f1b1b", "#25462a"]),
                "alpha": round(rng.uniform(0.42, 0.80), 3),
            })
        signatures = []
        for _ in range(rng.randint(1, 2)):
            signatures.append({
                "cx": round(rng.uniform(0.52, 0.90), 3),
                "cy": round(rng.uniform(0.62, 0.94), 3),
                "scale": round(rng.uniform(0.6, 1.3), 3),
                "rotation_deg": round(rng.uniform(-9, 9), 2),
                "stroke_seed": rng.randint(1, 10**9),
                "ink": rng.choice(["#12224a", "#101010", "#1d3b6e"]),
            })
        handwriting = []
        for _ in range(rng.randint(1, 3)):
            handwriting.append({
                "text": rng.choice(HANDWRITING_SNIPPETS),
                "x": round(rng.uniform(0.02, 0.86), 3),
                "y": round(rng.uniform(0.06, 0.95), 3),
                "rotation_deg": round(rng.uniform(-12, 12), 2),
                "size_frac": round(rng.uniform(0.016, 0.030), 4),
                "ink": rng.choice(["#1a2f7a", "#7a1a1a", "#20201f"]),
                "stroke_seed": rng.randint(1, 10**9),
            })
        return {
            "tier": 4,
            "name": "fax quality with marks",
            "render_dpi": 200,
            "colour_mode": "bilevel",
            "operations": ["stamps", "signatures", "handwriting", "staple_holes", "skew",
                           "downsample", "noise", "dither", "speckle", "line_dropout", "png1bit"],
            "skew_deg": round(rng.uniform(-2.6, 2.6), 3),
            "fax_dpi": rng.choice([100, 120, 150]),
            "pre_noise_sigma": round(rng.uniform(8.0, 18.0), 2),
            "dither": rng.choice(["floyd_steinberg", "threshold"]),
            "threshold": rng.randint(108, 162),
            "speckle_density": round(rng.uniform(0.002, 0.013), 5),
            "line_dropout_rows": rng.randint(0, 6),
            "stamps": stamps,
            "signatures": signatures,
            "handwriting": handwriting,
            "staple": {
                "corner": rng.choice(["tl", "tr"]),
                "holes": rng.randint(1, 2),
                "tear": rng.random() < 0.45,
                "offset_frac": round(rng.uniform(0.018, 0.045), 4),
            },
        }
    # tier 5
    second = rng.choice(LOCALE_SECOND_LANGUAGE.get(locale, ["hi"]))
    bundle = []
    for i in range(page_count):
        bundle.append({"source": "doc_page", "index": i})
    bundle.append({"source": "cover_note", "language": second})
    dup_from = rng.randrange(len(bundle))
    insert_at = rng.randrange(len(bundle) + 1)
    # The duplicate records the page it copies as a descriptor, not as an index.
    # An index would refer to the list before this insertion and before the swap
    # below, and would therefore be wrong in the stored plan.
    bundle.insert(insert_at, {"source": "duplicate", "of": dict(bundle[dup_from])})
    if rng.random() < 0.45 and len(bundle) > 2:
        i, j = rng.sample(range(len(bundle)), 2)
        bundle[i], bundle[j] = bundle[j], bundle[i]
    per_page = []
    for _ in bundle:
        per_page.append({
            "rotation_deg": rng.choices([0, 0, 0, 90, 180, 270], weights=[6, 6, 6, 3, 2, 2])[0],
            "base_effect": rng.choice(["flatbed", "phone", "fax"]),
            "extra_blur_sigma": round(rng.uniform(0.2, 1.4), 3),
        })
    return {
        "tier": 5,
        "name": "mixed multi-page bundle",
        "render_dpi": 200,
        "colour_mode": "mixed",
        "operations": ["bundle_assembly", "page_rotation", "page_duplication", "page_reorder",
                       "mixed_base_effects", "downscale", "double_jpeg", "bilingual_page"],
        "second_language": second,
        "bundle_plan": bundle,
        "per_page": per_page,
        "downscale_frac": round(rng.uniform(0.34, 0.62), 3),
        "jpeg_quality_pass1": rng.randint(30, 52),
        "jpeg_quality_pass2": rng.randint(22, 42),
        "final_long_edge_px": rng.choice([1280, 1440, 1600]),
    }


# --------------------------------------------------------------------------- #
# Allocation helpers                                                          #
# --------------------------------------------------------------------------- #

def largest_remainder(total: int, shares: dict) -> dict:
    raw = {k: total * v for k, v in shares.items()}
    out = {k: int(v) for k, v in raw.items()}
    left = total - sum(out.values())
    order = sorted(shares, key=lambda k: (-(raw[k] - out[k]), k))
    for k in order[:left]:
        out[k] += 1
    return out


def tier_plan() -> dict:
    """Planned tier counts, computed the same way generate.py assigns them.
    validate.py recomputes this independently and compares against the built set."""
    totals = {t: 0 for t in TIER_SHARES}
    per_subtype = {}
    for _dtype, subtype, count in TYPE_PLAN:
        alloc = largest_remainder(count, TIER_SHARES)
        per_subtype[subtype] = alloc
        for t, n in alloc.items():
            totals[t] += n
    return {"per_subtype": per_subtype, "totals": totals}


def split_plan() -> dict:
    """Planned split sizes per subtype, largest-remainder over the subtype shares."""
    total = sum(c for _, _, c in TYPE_PLAN)
    shares = {sub: count / total for _, sub, count in TYPE_PLAN}
    return {name: largest_remainder(size, shares) for name, size in SPLIT_SIZES.items()}


# --------------------------------------------------------------------------- #
# Main generation                                                             #
# --------------------------------------------------------------------------- #

def build_all(master_seed: int) -> list[dict]:
    tiers = tier_plan()
    splits = split_plan()
    records: list[dict] = []

    for dtype, subtype, count in TYPE_PLAN:
        prefix = TYPE_PREFIX[dtype]
        # deterministic tier assignment inside the subtype
        tier_alloc = tiers["per_subtype"][subtype]
        tier_sequence: list[int] = []
        for t in sorted(tier_alloc):
            tier_sequence.extend([t] * tier_alloc[t])
        shuffler = rng_for(master_seed, f"tier-shuffle:{subtype}")
        shuffler.shuffle(tier_sequence)

        # deterministic split assignment, stratified by tier
        by_tier: dict[int, list[int]] = {}
        for idx, t in enumerate(tier_sequence):
            by_tier.setdefault(t, []).append(idx)
        split_assign: dict[int, str] = {}
        for split_name in ("public_sample", "private_holdout"):
            want = splits[split_name][subtype]
            if want == 0:
                continue
            per_tier = largest_remainder(want, TIER_SHARES)
            picker = rng_for(master_seed, f"split:{split_name}:{subtype}")
            for t in sorted(per_tier):
                pool = [i for i in by_tier.get(t, []) if i not in split_assign]
                take = min(per_tier[t], len(pool))
                for i in picker.sample(pool, take):
                    split_assign[i] = split_name
            # any shortfall (a tier ran out) is filled from the remaining pool
            short = want - sum(1 for v in split_assign.values() if v == split_name)
            if short > 0:
                pool = [i for i in range(count) if i not in split_assign]
                for i in picker.sample(pool, min(short, len(pool))):
                    split_assign[i] = split_name

        for i in range(count):
            doc_id = f"msc-{prefix}-{i + 1:04d}" if dtype != "invoice" else \
                f"msc-inv-{subtype.split('_', 1)[1]}-{i + 1:04d}"
            if dtype == "kyc_pack":
                doc_id = f"msc-kyc-{'aad' if subtype == 'kyc_aadhaar' else 'pan'}-{i + 1:04d}"
            elif dtype == "insurance_claim":
                doc_id = f"msc-clm-{subtype.split('_', 1)[1]}-{i + 1:04d}"
            elif dtype == "purchase_order":
                doc_id = f"msc-po-{subtype.split('_', 1)[1]}-{i + 1:04d}"

            rng = rng_for(master_seed, doc_id)
            fields, extra = BUILDERS[subtype](rng, subtype)
            locale = extra["aux"]["locale"]
            pages = logical_pages(subtype, fields, rng)
            tier = tier_sequence[i]
            deg = degradation_plan(tier, rng, len(pages), locale)

            languages = ["en"]
            if tier == 5:
                languages.append(deg["second_language"])
            page_count = len(deg["bundle_plan"]) if tier == 5 else len(pages)

            record = {
                "doc_id": doc_id,
                "dataset": "messy-scan",
                "dataset_version": DATASET_VERSION,
                "schema_version": SCHEMA_VERSION,
                "seed": master_seed,
                "doc_type": dtype,
                "doc_subtype": subtype,
                "locale": locale,
                "tier": tier,
                "languages": languages,
                "page_count": page_count,
                "split": split_assign.get(i, "open"),
                "layout_variant": rng.randrange(4),
                "display_formats": {
                    "date": DATE_DISPLAY[locale],
                    "decimal_separator": ".",
                    "thousands_grouping": "indian" if fields.get("currency") == "INR" else "western",
                },
                "schema": SCHEMAS[subtype],
                "fields": fields,
                "logical_pages": pages,
                "identifier_provenance": extra["provenance"],
                "degradation": deg,
                "bilingual_labels": BILINGUAL[deg["second_language"]] if tier == 5 else None,
                "render": None,
            }
            records.append(record)
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the Messy Scan document plan and ground truth.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=DEFAULT_PLAN_PATH)
    args = ap.parse_args(argv)

    records = build_all(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    tiers = tier_plan()["totals"]
    by_type: dict[str, int] = {}
    for r in records:
        by_type[r["doc_subtype"]] = by_type.get(r["doc_subtype"], 0) + 1
    print(f"seed {args.seed} -> {len(records)} documents")
    print("tier totals:", ", ".join(f"T{t}={n}" for t, n in sorted(tiers.items())))
    print("subtypes:", ", ".join(f"{k}={v}" for k, v in sorted(by_type.items())))
    splits: dict[str, int] = {}
    for r in records:
        splits[r["split"]] = splits.get(r["split"], 0) + 1
    print("splits:", ", ".join(f"{k}={v}" for k, v in sorted(splits.items())))
    print(f"written: {args.out}")
    return 0


def load_documents(path: Path | None = None) -> list[dict]:
    path = path or DEFAULT_PLAN_PATH
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


if __name__ == "__main__":
    sys.exit(main())
