#!/usr/bin/env python3
"""Messy Scan dataset v1.0 — validator.

Checks the eight things that have to be true for a result taken from this dataset
to mean anything:

  1. The checksum implementations in this file are themselves right. Each one is
     tested against a published vector or a round-trip property before it is used
     to judge the data. A validator with a broken Luhn would happily pass a live
     card number.
  2. Structure: the file parses, there are no duplicate document ids, and the
     count per subtype matches the published plan.
  3. Fields: every field named in a document's own schema is present and non-empty.
  4. Arithmetic: every line amount, subtotal, tax and total reconciles. The rules
     are re-derived here from the stated rates and components; nothing is imported
     from the generator.
  5. Identifiers: every identifier FAILS its check. The check is named per
     identifier type and classified as a real checksum, a published structural
     rule, or "no public check available" - the last is reported, never counted as
     a pass.
  6. A blanket sweep over every string in the ground truth, which catches anything
     the per-field checks miss. Two rules:
       Rule A  every maximal digit run of 12 to 19 digits fails Luhn, and a run of
               exactly 12 digits also fails Verhoeff;
       Rule B  inside a maximal run of 20 or more digits (an IBAN body, say) no
               16-digit window is Luhn-valid.
     Runs of 20 or more digits are not card-shaped under ISO/IEC 7812, and the
     eighty-odd overlapping windows in one are not all constrainable, so only the
     16-digit windows are checked. The datasheet states this limit.
  7. Tier distribution matches the plan, and the public and private splits are the
     stated sizes and disjoint.
  8. Every rendered file referenced by the ground truth exists and its SHA-256
     matches the recorded value.
  9. The rendered document says what the ground truth says it says. For a sample of
     documents per subtype the clean PDF's text layer is read back and every
     identifier and total is looked for literally. A hash proves a file has not
     changed; it does not prove the file matches the ground truth beside it.

Exit status is 0 only if every check passes. Documents that have not been rendered
yet are reported as such; pass --strict-render to fail on them.

Usage
-----
    python3 validate.py
    python3 validate.py --strict-render
    python3 validate.py --self-test-only

Licence: MIT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_GT = HERE / "ground-truth.jsonl"

# The published plan. Asserted against generate.py's constants below, so the two
# cannot drift apart silently.
EXPECTED_SUBTYPE_COUNTS = {
    "invoice_in_gst": 100, "invoice_us": 100, "invoice_eu_vat": 100, "invoice_ph_bir": 100,
    "kyc_aadhaar": 130, "kyc_pan": 120,
    "claim_motor": 80, "claim_health": 70, "claim_property": 50,
    "po_in": 50, "po_us": 40, "po_eu": 35, "po_ph": 25,
}
EXPECTED_TIER_SHARES = {1: 0.15, 2: 0.25, 3: 0.25, 4: 0.20, 5: 0.15}
EXPECTED_SPLIT_SIZES = {"public_sample": 50, "private_holdout": 200}


# --------------------------------------------------------------------------- #
# Independent checksum implementations                                        #
# --------------------------------------------------------------------------- #

_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6), (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8), (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2), (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4), (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2), (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0), (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5), (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_ok(number: str) -> bool:
    if not number.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def luhn_ok(number: str) -> bool:
    if not number.isdigit() or len(number) < 2:
        return False
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_ok(value: str) -> bool:
    v = value.replace(" ", "").upper()
    if len(v) < 15 or not v[:2].isalpha() or not v[2:4].isdigit():
        return False
    rearranged = v[4:] + v[:4]
    if not rearranged.isalnum():
        return False
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(digits) % 97 == 1


_GST_ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _gst_char(first14: str, start_factor: int) -> str:
    mod = 36
    factor = start_factor
    total = 0
    for ch in reversed(first14):
        cp = _GST_ALPHA.index(ch)
        prod = factor * cp
        factor = 1 if factor == 2 else 2
        total += (prod // mod) + (prod % mod)
    return _GST_ALPHA[(mod - (total % mod)) % mod]


def gstin_ok(value: str) -> bool:
    """True if the check character matches under either published factor convention."""
    if len(value) != 15 or any(c not in _GST_ALPHA for c in value):
        return False
    return value[14] in {_gst_char(value[:14], 2), _gst_char(value[:14], 1)}


def aba_ok(value: str) -> bool:
    if len(value) != 9 or not value.isdigit():
        return False
    w = (3, 7, 1, 3, 7, 1, 3, 7, 1)
    return sum(int(c) * k for c, k in zip(value, w)) % 10 == 0


def mrz_cd(field: str) -> str:
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch) - 55
        total += v * weights[i % 3]
    return str(total % 10)


def mrz_td3_ok(line2: str) -> bool:
    """True if the TD3 second line satisfies every published check digit."""
    if len(line2) != 44:
        return False
    doc_field, doc_cd = line2[0:9], line2[9]
    dob_field, dob_cd = line2[13:19], line2[19]
    exp_field, exp_cd = line2[21:27], line2[27]
    opt_field, opt_cd = line2[28:42], line2[42]
    comp_cd = line2[43]
    if mrz_cd(doc_field) != doc_cd:
        return False
    if mrz_cd(dob_field) != dob_cd or mrz_cd(exp_field) != exp_cd:
        return False
    if mrz_cd(opt_field) != opt_cd:
        return False
    composite = doc_field + doc_cd + dob_field + dob_cd + exp_field + exp_cd + opt_field + opt_cd
    return mrz_cd(composite) == comp_cd


_VIN_T = {**{str(d): d for d in range(10)},
          "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
          "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
          "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9}
_VIN_W = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def vin_ok(value: str) -> bool:
    if len(value) != 17 or any(c not in _VIN_T and c != "X" for c in value):
        return False
    total = sum(_VIN_T[c] * w for c, w in zip(value, _VIN_W) if c in _VIN_T)
    if any(c not in _VIN_T for i, c in enumerate(value) if i != 8):
        return False
    r = total % 11
    expected = "X" if r == 10 else str(r)
    return value[8] == expected


def de_vat_ok(value: str) -> bool:
    body = value[2:]
    if len(body) != 9 or not body.isdigit():
        return False
    product = 10
    for ch in body[:8]:
        s = (int(ch) + product) % 10
        if s == 0:
            s = 10
        product = (2 * s) % 11
    return str((11 - product) % 10) == body[8]


def fr_vat_ok(value: str) -> bool:
    body = value[2:]
    if len(body) != 11 or not body.isdigit():
        return False
    key, siren = body[:2], body[2:]
    return int(key) == (12 + 3 * (int(siren) % 97)) % 97 and luhn_ok(siren)


def nl_vat_ok(value: str) -> bool:
    body = value[2:]
    if len(body) != 12 or not body[:9].isdigit() or body[9] != "B":
        return False
    total = sum(int(c) * w for c, w in zip(body[:8], (9, 8, 7, 6, 5, 4, 3, 2)))
    r = total % 11
    return r < 10 and str(r) == body[8]


def it_vat_ok(value: str) -> bool:
    body = value[2:]
    if len(body) != 11 or not body.isdigit():
        return False
    total = 0
    for i, ch in enumerate(body[:10]):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10) == body[10]


def eu_vat_ok(value: str) -> bool:
    return {"DE": de_vat_ok, "FR": fr_vat_ok, "NL": nl_vat_ok,
            "IT": it_vat_ok}.get(value[:2], lambda _v: False)(value)


PAN_PUBLISHED_HOLDER_CODES = set("ABCFGHJLPTEK")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def pan_format_ok(value: str, surname_initial: str | None) -> bool:
    """True if the value satisfies the published PAN format rules we can check.

    The tenth-character algorithm is not published by the Income Tax Department, so
    it is not asserted here or anywhere else in this dataset.
    """
    if not PAN_RE.match(value):
        return False
    if value[3] not in PAN_PUBLISHED_HOLDER_CODES:
        return False
    if surname_initial and value[4] != surname_initial.upper():
        return False
    return True


def ifsc_format_ok(value: str) -> bool:
    return bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", value))


IRS_UNISSUED_PREFIXES = {"07", "08", "09", "17", "18", "19", "28", "29",
                         "49", "69", "70", "78", "79", "89"}


def ein_prefix_ok(value: str) -> bool:
    v = value.replace("-", "")
    return len(v) == 9 and v.isdigit() and v[:2] not in IRS_UNISSUED_PREFIXES


def mod11_2(payload: str) -> str:
    p = 0
    for ch in payload:
        p = ((p + int(ch)) * 2) % 11
    c = (12 - p) % 11
    return "X" if c == 10 else str(c)


def ph_tin_surrogate_ok(value: str) -> bool:
    digits = value.replace("-", "")
    if len(digits) < 9 or not digits[:9].isdigit():
        return False
    return mod11_2(digits[:8]) == digits[8]


# --------------------------------------------------------------------------- #
# Self-test of the checkers                                                   #
# --------------------------------------------------------------------------- #

def self_test() -> list[str]:
    """Published vectors first, round-trip properties where no vector is public."""
    fails: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            fails.append(name)

    # Luhn: the standard worked example.
    check("luhn accepts 79927398713", luhn_ok("79927398713"))
    check("luhn rejects 79927398710", not luhn_ok("79927398710"))
    # Verhoeff: the published example, check digit for 236 is 3.
    check("verhoeff accepts 2363", verhoeff_ok("2363"))
    check("verhoeff rejects 2364", not verhoeff_ok("2364"))
    # IBAN: the two examples published with ISO 13616 / ECBS.
    check("iban accepts GB82WEST12345698765432", iban_ok("GB82WEST12345698765432"))
    check("iban accepts DE89370400440532013000", iban_ok("DE89370400440532013000"))
    check("iban rejects GB82WEST12345698765433", not iban_ok("GB82WEST12345698765433"))
    # ABA routing: a published example routing number.
    check("aba accepts 021000021", aba_ok("021000021"))
    check("aba rejects 021000022", not aba_ok("021000022"))
    # ICAO 9303 specimen: document number L898902C has check digit 3.
    check("mrz check digit L898902C< is 3", mrz_cd("L898902C<") == "3")
    # VIN: the published worked example, check character X.
    check("vin accepts 1M8GDM9AXKP042788", vin_ok("1M8GDM9AXKP042788"))
    check("vin rejects 1M8GDM9A1KP042788", not vin_ok("1M8GDM9A1KP042788"))

    # No public vector exists for the GSTN and the four EU VAT schemes in a form we
    # can cite, so these are round-trip tested: build a value that the published
    # algorithm says is correct, then confirm the checker accepts it and rejects
    # every other check character.
    import random as _r
    rng = _r.Random(7)
    for _ in range(200):
        first14 = "".join(rng.choice(_GST_ALPHA) for _ in range(14))
        good = _gst_char(first14, 2)
        check("gstin round trip", gstin_ok(first14 + good))
        bad = rng.choice([c for c in _GST_ALPHA
                          if c not in {good, _gst_char(first14, 1)}])
        check("gstin rejects wrong check char", not gstin_ok(first14 + bad))

    for _ in range(200):
        body = "".join(str(rng.randint(0, 9)) for _ in range(8))
        product = 10
        for ch in body:
            s = (int(ch) + product) % 10
            s = 10 if s == 0 else s
            product = (2 * s) % 11
        good = str((11 - product) % 10)
        check("de vat round trip", de_vat_ok("DE" + body + good))
        check("de vat rejects wrong digit",
              not de_vat_ok("DE" + body + str((int(good) + 1) % 10)))

        siren_body = "".join(str(rng.randint(0, 9)) for _ in range(8))
        t = 0
        for i, ch in enumerate(reversed(siren_body)):
            d = int(ch)
            if i % 2 == 0:
                d *= 2
                d = d - 9 if d > 9 else d
            t += d
        siren = siren_body + str((10 - t % 10) % 10)
        key = f"{(12 + 3 * (int(siren) % 97)) % 97:02d}"
        check("fr vat round trip", fr_vat_ok("FR" + key + siren))

        nl_body = "".join(str(rng.randint(0, 9)) for _ in range(8))
        r = sum(int(c) * w for c, w in zip(nl_body, (9, 8, 7, 6, 5, 4, 3, 2))) % 11
        if r < 10:
            check("nl vat round trip", nl_vat_ok("NL" + nl_body + str(r) + "B01"))

        it_body = "".join(str(rng.randint(0, 9)) for _ in range(10))
        t = 0
        for i, ch in enumerate(it_body):
            d = int(ch)
            if i % 2 == 1:
                d *= 2
                d = d - 9 if d > 9 else d
            t += d
        check("it vat round trip", it_vat_ok("IT" + it_body + str((10 - t % 10) % 10)))

    return sorted(set(fails))


# --------------------------------------------------------------------------- #
# Money helpers, re-derived here                                              #
# --------------------------------------------------------------------------- #

def to_minor(value: str) -> int:
    s = str(value).strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if "." in s:
        ip, fp = s.split(".", 1)
        fp = (fp + "00")[:2]
    else:
        ip, fp = s, "00"
    out = int(ip or "0") * 100 + int(fp)
    return -out if neg else out


def pct_minor(base_minor: int, rate: str) -> int:
    """Round-half-up application of a percentage to an integer minor amount."""
    rate_bp = int(round(float(rate) * 100))
    return (base_minor * rate_bp + 5000) // 10000


def dec_str(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    m = abs(minor)
    return f"{sign}{m // 100}.{m % 100:02d}"


# --------------------------------------------------------------------------- #
# Checks                                                                      #
# --------------------------------------------------------------------------- #

class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []
        self.failures: list[str] = []
        self.notes: list[str] = []

    def add(self, section: str, check: str, count: str, verdict: str) -> None:
        self.rows.append((section, check, count, verdict))

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def check_structure(records: list[dict], rep: Report) -> None:
    ids = [r["doc_id"] for r in records]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    rep.add("structure", "documents in file", str(len(records)),
            "ok" if len(records) == sum(EXPECTED_SUBTYPE_COUNTS.values()) else "FAIL")
    if len(records) != sum(EXPECTED_SUBTYPE_COUNTS.values()):
        rep.fail(f"expected {sum(EXPECTED_SUBTYPE_COUNTS.values())} documents, found {len(records)}")
    rep.add("structure", "duplicate document ids", str(len(dupes)),
            "ok" if not dupes else "FAIL")
    if dupes:
        rep.fail(f"duplicate document ids: {dupes[:5]}")
    counts = Counter(r["doc_subtype"] for r in records)
    bad = {k: (counts.get(k, 0), v) for k, v in EXPECTED_SUBTYPE_COUNTS.items()
           if counts.get(k, 0) != v}
    rep.add("structure", "subtype counts match plan", f"{len(EXPECTED_SUBTYPE_COUNTS)} subtypes",
            "ok" if not bad else "FAIL")
    if bad:
        rep.fail(f"subtype counts differ from plan: {bad}")


def largest_remainder(total: int, shares: dict) -> dict:
    raw = {k: total * v for k, v in shares.items()}
    out = {k: int(v) for k, v in raw.items()}
    left = total - sum(out.values())
    order = sorted(shares, key=lambda k: (-(raw[k] - out[k]), k))
    for k in order[:left]:
        out[k] += 1
    return out


def check_tiers(records: list[dict], rep: Report) -> dict:
    planned = Counter()
    for subtype, count in EXPECTED_SUBTYPE_COUNTS.items():
        for tier, n in largest_remainder(count, EXPECTED_TIER_SHARES).items():
            planned[tier] += n
    actual = Counter(r["tier"] for r in records)
    ok = all(planned[t] == actual.get(t, 0) for t in EXPECTED_TIER_SHARES)
    detail = ", ".join(f"T{t}={actual.get(t, 0)}/{planned[t]}" for t in sorted(EXPECTED_TIER_SHARES))
    rep.add("tiers", "actual/planned per tier", detail, "ok" if ok else "FAIL")
    if not ok:
        rep.fail(f"tier distribution differs from plan: actual {dict(actual)}, plan {dict(planned)}")
    return dict(planned)


def check_splits(records: list[dict], rep: Report, gt_path: Path) -> None:
    by_split = Counter(r["split"] for r in records)
    for name, size in EXPECTED_SPLIT_SIZES.items():
        got = by_split.get(name, 0)
        rep.add("splits", f"{name} size", f"{got}/{size}", "ok" if got == size else "FAIL")
        if got != size:
            rep.fail(f"split {name} has {got} documents, plan says {size}")
    ids = defaultdict(set)
    for r in records:
        ids[r["split"]].add(r["doc_id"])
    overlap = ids["public_sample"] & ids["private_holdout"]
    rep.add("splits", "public and private disjoint", str(len(overlap)),
            "ok" if not overlap else "FAIL")
    if overlap:
        rep.fail(f"public sample and private split overlap on {sorted(overlap)[:5]}")
    for name, folder in (("public_sample", "sample"), ("private_holdout", "private")):
        sub = gt_path.parent / folder / "ground-truth.jsonl"
        if not sub.exists():
            rep.note(f"{folder}/ground-truth.jsonl not present; run degrade.py to build the splits")
            continue
        n = sum(1 for line in sub.open(encoding="utf-8") if line.strip())
        want = EXPECTED_SPLIT_SIZES[name]
        rep.add("splits", f"{folder}/ground-truth.jsonl lines", f"{n}/{want}",
                "ok" if n == want else "FAIL")
        if n != want:
            rep.fail(f"{folder}/ground-truth.jsonl has {n} lines, expected {want}")


def check_fields(records: list[dict], rep: Report) -> None:
    missing = 0
    empty = 0
    extra = 0
    for r in records:
        fields = r["fields"]
        for name, kind in r["schema"].items():
            if name not in fields:
                missing += 1
                rep.fail(f'{r["doc_id"]}: field {name} missing')
                continue
            v = fields[name]
            if v is None or (isinstance(v, str) and not v.strip()) or \
                    (isinstance(v, list) and not v):
                empty += 1
                rep.fail(f'{r["doc_id"]}: field {name} empty')
        for name in fields:
            if name not in r["schema"]:
                extra += 1
                rep.fail(f'{r["doc_id"]}: field {name} is not in the schema')
    total = sum(len(r["schema"]) for r in records)
    rep.add("fields", "schema fields present and non-empty", f"{total - missing - empty}/{total}",
            "ok" if missing == empty == extra == 0 else "FAIL")


def _check_lines(doc_id: str, lines: list[dict], rep: Report) -> int:
    total = 0
    for ln in lines:
        unit = ln["unit_price_minor"]
        qty = ln["quantity_thousandths"]
        want = (unit * qty + 500) // 1000
        if ln["amount_minor"] != want:
            rep.fail(f'{doc_id}: line {ln["sl"]} amount {ln["amount_minor"]} != '
                     f"quantity x unit price {want}")
        if to_minor(ln["amount"]) != ln["amount_minor"]:
            rep.fail(f'{doc_id}: line {ln["sl"]} amount string disagrees with minor units')
        if to_minor(ln["unit_price"]) != unit:
            rep.fail(f'{doc_id}: line {ln["sl"]} unit price string disagrees with minor units')
        if int(round(float(ln["quantity"]) * 1000)) != qty:
            rep.fail(f'{doc_id}: line {ln["sl"]} quantity string disagrees with thousandths')
        total += ln["amount_minor"]
    return total


def check_arithmetic(records: list[dict], rep: Report) -> None:
    before = len(rep.failures)
    for r in records:
        f = r["fields"]
        sub = r["doc_subtype"]
        did = r["doc_id"]
        if sub == "invoice_in_gst":
            taxable = _check_lines(did, f["line_items"], rep)
            if to_minor(f["taxable_value"]) != taxable:
                rep.fail(f"{did}: taxable value != sum of line amounts")
            cgst, sgst, igst = (to_minor(f["cgst_amount"]), to_minor(f["sgst_amount"]),
                                to_minor(f["igst_amount"]))
            for name, amt, rate in (("cgst", cgst, f["cgst_rate"]), ("sgst", sgst, f["sgst_rate"]),
                                    ("igst", igst, f["igst_rate"])):
                if amt != pct_minor(taxable, rate):
                    rep.fail(f"{did}: {name} {dec_str(amt)} != {rate}% of taxable value")
            if to_minor(f["total_tax"]) != cgst + sgst + igst:
                rep.fail(f"{did}: total tax != CGST + SGST + IGST")
            total = to_minor(f["invoice_total"])
            if total != taxable + cgst + sgst + igst + to_minor(f["round_off"]):
                rep.fail(f"{did}: invoice total != taxable + tax + round off")
            if abs(to_minor(f["round_off"])) > 50 or total % 100 != 0:
                rep.fail(f"{did}: round off outside the stated rule")
        elif sub == "invoice_us":
            subtotal = _check_lines(did, f["line_items"], rep)
            if to_minor(f["subtotal"]) != subtotal:
                rep.fail(f"{did}: subtotal != sum of line amounts")
            taxable = subtotal - to_minor(f["discount"])
            if to_minor(f["sales_tax_amount"]) != pct_minor(taxable, f["sales_tax_rate"]):
                rep.fail(f"{did}: sales tax != rate applied to subtotal less discount")
            want = taxable + to_minor(f["sales_tax_amount"]) + to_minor(f["shipping"])
            if to_minor(f["invoice_total"]) != want:
                rep.fail(f"{did}: invoice total != subtotal - discount + tax + shipping")
        elif sub == "invoice_eu_vat":
            net = _check_lines(did, f["line_items"], rep)
            if to_minor(f["net_total"]) != net:
                rep.fail(f"{did}: net total != sum of line amounts")
            if to_minor(f["vat_amount"]) != pct_minor(net, f["vat_rate"]):
                rep.fail(f"{did}: VAT != rate applied to net total")
            if to_minor(f["gross_total"]) != net + to_minor(f["vat_amount"]):
                rep.fail(f"{did}: gross total != net + VAT")
            if f["reverse_charge"] == "true" and float(f["vat_rate"]) != 0.0:
                rep.fail(f"{did}: reverse charge invoice carries a non-zero VAT rate")
        elif sub == "invoice_ph_bir":
            lines_total = _check_lines(did, f["line_items"], rep)
            parts = (to_minor(f["vatable_sales"]) + to_minor(f["vat_exempt_sales"])
                     + to_minor(f["zero_rated_sales"]))
            if parts != lines_total:
                rep.fail(f"{did}: VATable + exempt + zero-rated != sum of line amounts")
            if to_minor(f["vat_amount"]) != pct_minor(to_minor(f["vatable_sales"]), f["vat_rate"]):
                rep.fail(f"{did}: VAT != rate applied to VATable sales")
            if to_minor(f["total_amount_due"]) != lines_total + to_minor(f["vat_amount"]):
                rep.fail(f"{did}: total amount due != sales + VAT")
        elif sub.startswith("kyc"):
            units = int(f["units_consumed"])
            tariff = to_minor(f["tariff_rate"])
            if to_minor(f["energy_charge"]) != units * tariff:
                rep.fail(f"{did}: energy charge != units x tariff")
            base = to_minor(f["energy_charge"]) + to_minor(f["fixed_charge"])
            if to_minor(f["electricity_duty"]) != pct_minor(base, f["electricity_duty_rate"]):
                rep.fail(f"{did}: electricity duty != rate applied to energy plus fixed charge")
            want = base + to_minor(f["electricity_duty"]) + to_minor(f["utility_arrears"])
            if to_minor(f["utility_total"]) != want:
                rep.fail(f"{did}: utility total != energy + fixed + duty + arrears")
        elif sub.startswith("claim"):
            assessed = _check_lines(did, f["estimate_lines"], rep)
            if to_minor(f["assessed_total"]) != assessed:
                rep.fail(f"{did}: assessed total != sum of estimate lines")
            if sub == "claim_health":
                copay = pct_minor(assessed, f["co_pay_rate"])
                if to_minor(f["co_pay_amount"]) != copay:
                    rep.fail(f"{did}: co-pay != rate applied to assessed total")
                want = assessed - copay - to_minor(f["policy_excess"])
            else:
                want = assessed - to_minor(f["salvage_value"]) - to_minor(f["policy_excess"])
            if to_minor(f["net_payable"]) != want:
                rep.fail(f"{did}: net payable != assessed total less deductions")
        elif sub.startswith("po_"):
            subtotal = _check_lines(did, f["line_items"], rep)
            if to_minor(f["subtotal"]) != subtotal:
                rep.fail(f"{did}: subtotal != sum of line amounts")
            if to_minor(f["tax_amount"]) != pct_minor(subtotal, f["tax_rate"]):
                rep.fail(f"{did}: tax != rate applied to subtotal")
            want = subtotal + to_minor(f["tax_amount"]) + to_minor(f["freight"])
            if to_minor(f["po_total"]) != want:
                rep.fail(f"{did}: order total != subtotal + tax + freight")
        else:
            rep.fail(f"{did}: no arithmetic rule defined for subtype {sub}")
    broken = len(rep.failures) - before
    rep.add("arithmetic", "documents whose totals reconcile",
            f"{len(records) - broken}/{len(records)}" if broken else f"{len(records)}/{len(records)}",
            "ok" if broken == 0 else "FAIL")


# identifier field -> (check name, human label, class)
REAL = "real checksum"
STRUCT = "published structural rule"
NOCHECK = "no public check available"

IDENTIFIER_CHECKS: dict[str, tuple[str, str]] = {
    "aadhaar_number": ("Verhoeff (dihedral D5) over 12 digits", REAL),
    "card_number": ("Luhn, ISO/IEC 7812-1", REAL),
    "iban": ("ISO 13616 / ISO 7064 MOD 97-10", REAL),
    "supplier_gstin": ("GSTN modulo-36 check character", REAL),
    "buyer_gstin": ("GSTN modulo-36 check character", REAL),
    "ach_routing_number": ("ABA 3-7-1 modulo-10", REAL),
    "passport_number": ("ICAO 9303 TD3 7-3-1 modulo-10 check digits", REAL),
    "vehicle_vin": ("VIN position-9 modulo-11 transliteration check", REAL),
    "supplier_vat_number": ("EU VAT scheme check (DE, FR, NL, IT)", REAL),
    "customer_vat_number": ("EU VAT scheme check (DE, FR, NL, IT)", REAL),
    "supplier_pan": ("PAN published format: holder-type and surname characters", STRUCT),
    "pan_number": ("PAN published format: holder-type and surname characters", STRUCT),
    "bank_ifsc": ("RBI IFSC format: fifth character must be 0", STRUCT),
    "settlement_ifsc": ("RBI IFSC format: fifth character must be 0", STRUCT),
    "vendor_ein": ("IRS published campus prefix list", STRUCT),
    "seller_tin": ("BIR TIN: no published algorithm (MOD 11-2 surrogate reported)", NOCHECK),
    "buyer_tin": ("BIR TIN: no published algorithm (MOD 11-2 surrogate reported)", NOCHECK),
}


def identifier_passes(field: str, value: str, rec: dict) -> bool | None:
    """True when the identifier PASSES its real check, which is the failure case
    for this dataset. None when there is no check to apply."""
    f = rec["fields"]
    if field == "aadhaar_number":
        return verhoeff_ok(value)
    if field == "card_number":
        return luhn_ok(value)
    if field == "iban":
        return iban_ok(value)
    if field in ("supplier_gstin", "buyer_gstin"):
        return gstin_ok(value)
    if field == "ach_routing_number":
        return aba_ok(value)
    if field == "passport_number":
        return mrz_td3_ok(f["mrz_line2"])
    if field == "vehicle_vin":
        return vin_ok(value)
    if field in ("supplier_vat_number", "customer_vat_number"):
        return eu_vat_ok(value)
    if field in ("supplier_pan", "pan_number"):
        holder = f.get("holder_name") or f.get("supplier_name") or ""
        initial = holder.split()[-1][0] if holder else None
        return pan_format_ok(value, initial)
    if field in ("bank_ifsc", "settlement_ifsc"):
        return ifsc_format_ok(value)
    if field == "vendor_ein":
        return ein_prefix_ok(value)
    if field in ("seller_tin", "buyer_tin"):
        return None
    return None


def classify_vendor_tax_id(value: str) -> tuple[str, str, str]:
    """Purchase orders carry one tax id whose scheme depends on the locale."""
    if value[:2] in ("DE", "FR", "NL", "IT"):
        return "vendor_tax_id (EU VAT)", "EU VAT scheme check (DE, FR, NL, IT)", REAL
    if len(value) == 15 and value[2:12].isalnum() and not value[0].isalpha():
        return "vendor_tax_id (GSTIN)", "GSTN modulo-36 check character", REAL
    if re.match(r"^\d{2}-\d{7}$", value):
        return "vendor_tax_id (EIN)", "IRS published campus prefix list", STRUCT
    return ("vendor_tax_id (PH TIN)",
            "BIR TIN: no published algorithm (MOD 11-2 surrogate reported)", NOCHECK)


def check_identifiers(records: list[dict], rep: Report) -> list[tuple]:
    stats: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for r in records:
        f = r["fields"]
        for field, kind in r["schema"].items():
            if kind != "identifier":
                continue
            value = f[field]
            if field == "vendor_tax_id":
                name, check, klass = classify_vendor_tax_id(value)
                if klass is NOCHECK:
                    passes = None
                    surrogate = ph_tin_surrogate_ok(value)
                elif "EU VAT" in check:
                    passes = eu_vat_ok(value)
                elif "GSTN" in check:
                    passes = gstin_ok(value)
                else:
                    passes = ein_prefix_ok(value)
            else:
                check, klass = IDENTIFIER_CHECKS[field]
                name = field
                passes = identifier_passes(field, value, r)
                surrogate = ph_tin_surrogate_ok(value) if klass is NOCHECK else None
            key = (name, check, klass)
            stats[key][0] += 1
            if passes is True:
                stats[key][1] += 1
                rep.fail(f'{r["doc_id"]}: {name} {value} PASSES its check '
                         f"({check}); every identifier must fail")
            elif passes is False:
                stats[key][2] += 1
            elif klass is NOCHECK and surrogate:
                rep.fail(f'{r["doc_id"]}: {name} {value} satisfies the documented '
                         "MOD 11-2 surrogate; it should fail it")
    rows = []
    for (name, check, klass), (total, passing, failing) in sorted(stats.items()):
        verdict = "ok" if passing == 0 else "FAIL"
        rows.append((name, check, klass, total, failing, passing, verdict))
    return rows


DIGIT_RUN = re.compile(r"\d+")


def walk_strings(value, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            walk_strings(v, out)
    elif isinstance(value, list):
        for v in value:
            walk_strings(v, out)


def check_pii_sweep(records: list[dict], rep: Report) -> tuple[int, int]:
    runs = 0
    hits = 0
    for r in records:
        strings: list[str] = []
        walk_strings(r["fields"], strings)
        for s in strings:
            for m in DIGIT_RUN.finditer(s):
                run = m.group(0)
                n = len(run)
                if 12 <= n <= 19:
                    runs += 1
                    if luhn_ok(run):
                        hits += 1
                        rep.fail(f'{r["doc_id"]}: digit run {run} is Luhn-valid')
                    if n == 12 and verhoeff_ok(run):
                        hits += 1
                        rep.fail(f'{r["doc_id"]}: 12-digit run {run} is Verhoeff-valid')
                elif n >= 20:
                    runs += 1
                    for i in range(n - 15):
                        if luhn_ok(run[i:i + 16]):
                            hits += 1
                            rep.fail(f'{r["doc_id"]}: 16-digit window {run[i:i + 16]} '
                                     f"inside a {n}-digit run is Luhn-valid")
                            break
    rep.add("pii sweep", "card-shaped digit runs checked (rules A and B)", str(runs),
            "ok" if hits == 0 else "FAIL")
    return runs, hits


def check_renders(records: list[dict], rep: Report, strict: bool) -> tuple[int, int, int]:
    rendered = missing_files = bad_hash = 0
    not_rendered = 0
    for r in records:
        render = r.get("render")
        if not render:
            not_rendered += 1
            continue
        rendered += 1
        entries = [render["pdf"]] + list(render["pages"])
        for entry in entries:
            path = HERE / entry["path"]
            if not path.exists():
                missing_files += 1
                rep.fail(f'{r["doc_id"]}: rendered file missing: {entry["path"]}')
                continue
            h = hashlib.sha256()
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != entry["sha256"]:
                bad_hash += 1
                rep.fail(f'{r["doc_id"]}: SHA-256 mismatch for {entry["path"]}')
        if render["page_count"] != r["page_count"]:
            rep.fail(f'{r["doc_id"]}: rendered page count {render["page_count"]} != '
                     f'ground truth {r["page_count"]}')
    rep.add("renders", "documents with artefacts", f"{rendered}/{len(records)}",
            "ok" if not (strict and not_rendered) else "FAIL")
    rep.add("renders", "referenced files present", "missing " + str(missing_files),
            "ok" if missing_files == 0 else "FAIL")
    rep.add("renders", "SHA-256 matches", "mismatches " + str(bad_hash),
            "ok" if bad_hash == 0 else "FAIL")
    if not_rendered:
        msg = (f"{not_rendered} documents have no rendered artefact yet; "
               "finish with: python3 render.py --skip-existing && "
               "python3 degrade.py --skip-existing")
        if strict:
            rep.fail(msg)
        else:
            rep.note(msg)
    return rendered, missing_files, bad_hash


TEXT_CHECK_IDENTIFIERS = (
    "supplier_gstin", "buyer_gstin", "supplier_pan", "pan_number", "aadhaar_number",
    "vendor_ein", "supplier_vat_number", "customer_vat_number", "seller_tin",
    "buyer_tin", "iban", "passport_number", "mrz_line2", "vehicle_vin",
    "vendor_tax_id", "ach_routing_number", "bank_ifsc", "settlement_ifsc",
    "utility_consumer_number", "invoice_number", "si_number", "po_number",
    "claim_number", "policy_number",
)
TEXT_CHECK_TOTALS = ("invoice_total", "gross_total", "total_amount_due", "po_total",
                     "net_payable", "utility_total", "assessed_total")


def check_ground_truth_on_page(records: list[dict], rep: Report, per_subtype: int,
                               render_dir: Path) -> None:
    """Does the rendered document actually say what the ground truth says it says?

    The hash check proves a file has not changed. It does not prove the file matches
    the ground truth beside it. This reads the text layer out of the clean PDF for a
    sample of documents and looks for the identifiers and totals literally.
    Requires pdftotext; skipped with a note if it is not installed.
    """
    import shutil as _shutil
    import subprocess
    if not _shutil.which("pdftotext"):
        rep.note("pdftotext not installed; skipped the ground-truth-on-page check")
        return
    import random as _random
    by_sub: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_sub[r["doc_subtype"]].append(r)
    rng = _random.Random(1)
    checked = 0
    misses = 0
    for sub in sorted(by_sub):
        pool = by_sub[sub]
        for r in rng.sample(pool, min(per_subtype, len(pool))):
            pdf = render_dir / r["doc_id"] / "clean.pdf"
            if not pdf.exists():
                continue
            out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                                 capture_output=True, text=True)
            flat = " ".join(out.stdout.split())
            ungrouped = flat.replace(",", "")
            f = r["fields"]
            for key in TEXT_CHECK_IDENTIFIERS:
                if key in f and str(f[key]) not in flat:
                    misses += 1
                    rep.fail(f'{r["doc_id"]}: {key} is in the ground truth but not on '
                             "the rendered page")
            for key in TEXT_CHECK_TOTALS:
                if key in f:
                    major = str(abs(int(round(float(f[key]) * 100))) // 100)
                    if major not in ungrouped:
                        misses += 1
                        rep.fail(f'{r["doc_id"]}: {key} is in the ground truth but not '
                                 "on the rendered page")
            checked += 1
    rep.add("ground truth on page", f"documents read back from the PDF text layer",
            str(checked), "ok" if misses == 0 else "FAIL")


# --------------------------------------------------------------------------- #
# Output                                                                      #
# --------------------------------------------------------------------------- #

def print_table(headers: list[str], rows: list[tuple]) -> None:
    cols = len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(row[i])))
    line = "  ".join("-" * w for w in widths)
    print("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print(line)
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(cols)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the Messy Scan dataset.")
    ap.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    ap.add_argument("--strict-render", action="store_true",
                    help="fail if any document has no rendered artefact")
    ap.add_argument("--self-test-only", action="store_true")
    ap.add_argument("--text-check-per-subtype", type=int, default=3,
                    help="documents per subtype to read back from the PDF text layer "
                         "(0 to skip)")
    ap.add_argument("--render-dir", type=Path, default=HERE / "build" / "render")
    ap.add_argument("--max-failures", type=int, default=25)
    args = ap.parse_args(argv)

    print("Messy Scan dataset v1.0 - validation")
    print("=" * 78)
    print()

    st = self_test()
    print("1. Checksum implementations, tested before use")
    print_table(["check", "result"], [
        ("published vectors and round-trip properties",
         "ok" if not st else "FAIL: " + ", ".join(st))])
    print()
    if st:
        print("The validator's own checksum code is wrong. Nothing below can be trusted.")
        return 2
    if args.self_test_only:
        return 0

    # The plan constants must match the generator's.
    sys.path.insert(0, str(HERE))
    import generate as gen  # noqa: E402
    gen_counts = {sub: count for _t, sub, count in gen.TYPE_PLAN}
    if gen_counts != EXPECTED_SUBTYPE_COUNTS or gen.TIER_SHARES != EXPECTED_TIER_SHARES \
            or gen.SPLIT_SIZES != EXPECTED_SPLIT_SIZES:
        print("FAIL: the plan in validate.py and the plan in generate.py disagree.")
        return 2

    if not args.ground_truth.exists():
        print(f"FAIL: {args.ground_truth} not found. Run generate.py, render.py, degrade.py.")
        return 2
    records = [json.loads(line) for line in args.ground_truth.open(encoding="utf-8")
               if line.strip()]

    rep = Report()
    check_structure(records, rep)
    check_fields(records, rep)
    check_arithmetic(records, rep)
    ident_rows = check_identifiers(records, rep)
    check_pii_sweep(records, rep)
    check_tiers(records, rep)
    check_splits(records, rep, args.ground_truth)
    check_renders(records, rep, args.strict_render)
    if args.text_check_per_subtype > 0:
        check_ground_truth_on_page(records, rep, args.text_check_per_subtype,
                                   args.render_dir)

    print("2. Dataset checks")
    print_table(["section", "check", "count", "verdict"], rep.rows)
    print()

    print("3. Identifiers: every one must FAIL its check")
    print_table(["field", "named check", "class", "seen", "failing", "passing", "verdict"],
                ident_rows)
    print()

    print("4. Composition")
    comp = Counter((r["doc_type"], r["doc_subtype"]) for r in records)
    tier_by_type = defaultdict(Counter)
    for r in records:
        tier_by_type[r["doc_subtype"]][r["tier"]] += 1
    rows = []
    for (dtype, sub), n in sorted(comp.items()):
        tiers = tier_by_type[sub]
        rows.append((dtype, sub, n, *[tiers.get(t, 0) for t in (1, 2, 3, 4, 5)]))
    totals = Counter(r["tier"] for r in records)
    rows.append(("all", "total", len(records), *[totals.get(t, 0) for t in (1, 2, 3, 4, 5)]))
    print_table(["type", "subtype", "n", "T1", "T2", "T3", "T4", "T5"], rows)
    print()

    print("5. Languages and page counts")
    langs = Counter(",".join(r["languages"]) for r in records)
    pages = Counter(r["page_count"] for r in records)
    print_table(["languages", "documents"], sorted(langs.items()))
    print()
    print_table(["pages per document", "documents"], sorted(pages.items()))
    print()

    if rep.notes:
        print("Notes")
        for n in rep.notes:
            print(f"  - {n}")
        print()

    if rep.failures:
        print(f"FAILURES: {len(rep.failures)}")
        for msg in rep.failures[:args.max_failures]:
            print(f"  - {msg}")
        if len(rep.failures) > args.max_failures:
            print(f"  ... and {len(rep.failures) - args.max_failures} more")
        print()
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS - every check above passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
