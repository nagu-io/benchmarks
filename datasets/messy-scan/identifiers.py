#!/usr/bin/env python3
"""Messy Scan — identifier construction.

Split out of ``generate.py`` so that each part of the generator sits in a file small
enough to read in one sitting. ``generate.py`` imports these modules and assembles the
dataset; the code and the data are unchanged by the split, and the seed still produces
a byte-identical ``ground-truth.jsonl``.

Every identifier this module produces is structurally plausible and deliberately
invalid: the correct check digit or character is computed by the real algorithm and
then a different one is emitted. Each ``make_*`` function returns the value together
with the rule it breaks and the correct value it was broken from, so ``validate.py``
can re-derive the break rather than trust it. The header of ``generate.py`` documents
the failure guarantee for every scheme.
"""

from __future__ import annotations

import datetime as dt
import random
import re


# --------------------------------------------------------------------------- #
# Checksum algorithms (used to compute the correct value, then break it)       #
# --------------------------------------------------------------------------- #

_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_check_digit(payload: str) -> str:
    """Verhoeff check digit for a digit string that does not yet carry one."""
    c = 0
    for i, ch in enumerate(reversed(payload)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(ch)]]
    return str(_VERHOEFF_INV[c])


def verhoeff_valid(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def luhn_check_digit(payload: str) -> str:
    """Luhn check digit for a digit string that does not yet carry one."""
    total = 0
    for i, ch in enumerate(reversed(payload)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def luhn_valid(number: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


_GST_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_check_char(first14: str, start_factor: int = 2) -> str:
    """Published GSTN modulo-36 check character over the first 14 characters.

    ``start_factor`` selects the factor applied to the rightmost character.
    Published implementations use 2; some use 1. We compute both and avoid both.
    """
    mod = len(_GST_ALPHABET)
    factor = start_factor
    total = 0
    for ch in reversed(first14):
        cp = _GST_ALPHABET.index(ch)
        prod = factor * cp
        factor = 1 if factor == 2 else 2
        total += (prod // mod) + (prod % mod)
    return _GST_ALPHABET[(mod - (total % mod)) % mod]


def iban_mod97(iban: str) -> int:
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(digits) % 97


def iban_check_digits(country: str, bban: str) -> str:
    tmp = bban + country + "00"
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in tmp)
    return f"{98 - int(digits) % 97:02d}"


def aba_check_digit(first8: str) -> str:
    """Ninth digit of an ABA routing number under the published 3-7-1 test."""
    w = (3, 7, 1, 3, 7, 1, 3, 7)
    total = sum(int(c) * k for c, k in zip(first8, w))
    return str((10 - total % 10) % 10)


def aba_valid(number: str) -> bool:
    w = (3, 7, 1, 3, 7, 1, 3, 7, 1)
    return sum(int(c) * k for c, k in zip(number, w)) % 10 == 0


_MRZ_WEIGHTS = (7, 3, 1)


def mrz_check_digit(field: str) -> str:
    total = 0
    for i, ch in enumerate(field):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch) - 55
        total += v * _MRZ_WEIGHTS[i % 3]
    return str(total % 10)


_VIN_TRANSLIT = {
    **{str(d): d for d in range(10)},
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}
_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def vin_check_char(vin17: str) -> str:
    total = sum(_VIN_TRANSLIT[c] * w for c, w in zip(vin17, _VIN_WEIGHTS))
    r = total % 11
    return "X" if r == 10 else str(r)


def de_vat_check_digit(first8: str) -> str:
    """ISO 7064 MOD 11,10 as used by the German USt-IdNr."""
    product = 10
    for ch in first8:
        s = (int(ch) + product) % 10
        if s == 0:
            s = 10
        product = (2 * s) % 11
    return str((11 - product) % 10)


def fr_vat_key(siren: str) -> str:
    return f"{(12 + 3 * (int(siren) % 97)) % 97:02d}"


def nl_vat_check_digit(first8: str) -> str:
    """Weighted modulo-11 test over the nine-digit Dutch BTW body."""
    total = sum(int(c) * w for c, w in zip(first8, (9, 8, 7, 6, 5, 4, 3, 2)))
    return str(total % 11)  # a valid body requires this to be < 10 and equal to d9


def it_vat_check_digit(first10: str) -> str:
    total = 0
    for i, ch in enumerate(first10):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def mod11_2_check_digit(payload: str) -> str:
    """ISO 7064 MOD 11-2. Used only as the documented surrogate for the
    Philippine TIN, whose real algorithm BIR does not publish."""
    p = 0
    for ch in payload:
        p = ((p + int(ch)) * 2) % 11
    check = (12 - p) % 11
    return "X" if check == 10 else str(check)


# --------------------------------------------------------------------------- #
# Identifier builders: plausible shape, deliberately failing check             #
# --------------------------------------------------------------------------- #

# The dataset guarantees two things about raw digit runs, so that nobody scanning
# the files finds something that looks like a live card or identity number:
#   Rule A  every maximal digit run of 12 to 19 digits fails Luhn, and a run of
#           exactly 12 digits also fails Verhoeff;
#   Rule B  inside a maximal run of 20 or more digits (an IBAN body, for example)
#           no 16-digit window is Luhn-valid. 16 is the modal card length and the
#           one a sliding-window scanner looks for.
# Windows of other lengths inside a run of 20 or more are not constrained: with
# eighty-odd overlapping windows per IBAN that is not achievable, and a run that
# long is not card-shaped under ISO/IEC 7812 anyway. validate.py enforces exactly
# these two rules and says so.

_DIGIT_RUN_RE = re.compile(r"\d+")


def digit_runs_clean(text: str) -> bool:
    for m in _DIGIT_RUN_RE.finditer(text):
        run = m.group(0)
        n = len(run)
        if 12 <= n <= 19:
            if luhn_valid(run):
                return False
            if n == 12 and verhoeff_valid(run):
                return False
        elif n >= 20:
            for i in range(n - 15):
                if luhn_valid(run[i:i + 16]):
                    return False
    return True


def _other_digit(rng: random.Random, correct: str) -> str:
    choices = [d for d in "0123456789" if d != correct]
    return rng.choice(choices)


def _other_char(rng: random.Random, correct_set: set[str], alphabet: str) -> str:
    choices = [c for c in alphabet if c not in correct_set]
    return rng.choice(choices)


def make_opaque_number(rng: random.Random, length: int) -> str:
    """A plain account-style number that is neither Luhn-valid nor Verhoeff-valid.

    Bank account numbers, permit numbers and the like carry no published checksum,
    so nothing forces them to be invalid. Left to chance, roughly one in ten would
    be Luhn-valid and one in ten Verhoeff-valid, and anyone scanning the dataset
    would then find a "valid card number" that is nothing of the sort. We choose
    the last digit so the whole run fails both tests.
    """
    body = "".join(str(rng.randint(0, 9)) for _ in range(length - 1))
    order = list("0123456789")
    rng.shuffle(order)
    for d in order:
        candidate = body + d
        if not luhn_valid(candidate) and not verhoeff_valid(candidate):
            return candidate
    return body + order[0]  # unreachable: at most two of ten digits can pass


def make_aadhaar(rng: random.Random) -> dict:
    payload = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(10))
    correct = verhoeff_check_digit(payload)
    order = [d for d in "0123456789" if d != correct]
    rng.shuffle(order)
    emitted = next(d for d in order if not luhn_valid(payload + d))
    number = payload + emitted
    assert not verhoeff_valid(number) and not luhn_valid(number)
    return {
        "value": number,
        "formatted": f"{number[0:4]} {number[4:8]} {number[8:12]}",
        "check": "verhoeff",
        "broken_by": (f"check digit {emitted} substituted for the correct {correct}; "
                      "the digit is also chosen so the 12-digit run is not Luhn-valid"),
    }


PAN_VALID_HOLDER_CODES = set("ABCFGHJLPTEK")
PAN_BROKEN_HOLDER_CODES = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in PAN_VALID_HOLDER_CODES]


def make_pan(rng: random.Random, surname_initial: str) -> dict:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    head = "".join(rng.choice(letters) for _ in range(3))
    holder_code = rng.choice(PAN_BROKEN_HOLDER_CODES)          # rule (a) broken
    fifth = rng.choice([c for c in letters if c != surname_initial])  # rule (b) broken
    digits = "".join(str(rng.randint(0, 9)) for _ in range(4))
    tail = rng.choice(letters)
    number = head + holder_code + fifth + digits + tail
    return {
        "value": number,
        "check": "pan_published_format",
        "broken_by": (
            f"holder-type character {holder_code} is outside the published set "
            f"A B C F G H J L P T (E, K); fifth character {fifth} does not match the "
            f"holder initial {surname_initial}. The tenth-character algorithm is "
            "unpublished and is not asserted."
        ),
    }


# Real GST state codes (01-38). Kept real so the value stays plausible.
GST_STATE_CODES = {
    "Gujarat": "24", "Maharashtra": "27", "Karnataka": "29", "Tamil Nadu": "33",
    "Telangana": "36", "Delhi": "07", "Haryana": "06", "Uttar Pradesh": "09",
    "West Bengal": "19", "Rajasthan": "08", "Kerala": "32", "Punjab": "03",
    "Madhya Pradesh": "23", "Odisha": "21",
}


def make_gstin(rng: random.Random, state_code: str, pan_value: str) -> dict:
    entity_number = rng.choice("123456789")
    first14 = state_code + pan_value + entity_number + "Z"
    c2 = gstin_check_char(first14, start_factor=2)
    c1 = gstin_check_char(first14, start_factor=1)
    emitted = _other_char(rng, {c1, c2}, _GST_ALPHABET)
    return {
        "value": first14 + emitted,
        "check": "gstn_mod36",
        "broken_by": (
            f"check character {emitted} differs from the computed {c2} "
            f"(and from {c1} under the alternate factor convention); the embedded "
            "PAN is itself format-invalid"
        ),
    }


def make_ifsc(rng: random.Random, bank_code: str) -> dict:
    non_zero = rng.choice("123456789")
    branch = "".join(rng.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6))
    return {
        "value": bank_code + non_zero + branch,
        "check": "rbi_ifsc_format",
        "broken_by": f"fifth character is {non_zero}; the published RBI format requires 0",
    }


def make_card(rng: random.Random) -> dict:
    prefix = rng.choice(["4", "51", "52", "53", "54", "55", "60", "65"])
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(15 - len(prefix)))
    correct = luhn_check_digit(body)
    emitted = _other_digit(rng, correct)
    number = body + emitted
    assert not luhn_valid(number)
    return {
        "value": number,
        "formatted": " ".join(number[i:i + 4] for i in range(0, 16, 4)),
        "check": "luhn",
        "broken_by": f"check digit {emitted} substituted for the correct {correct}",
    }


def make_iban(rng: random.Random, country: str) -> dict:
    lengths = {"DE": 18, "FR": 23, "NL": 14, "IT": 23}
    bban_len = lengths[country]
    for _attempt in range(200):
        if country == "IT":
            bban = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + "".join(
                str(rng.randint(0, 9)) for _ in range(bban_len - 1))
        elif country == "NL":
            bban = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(4)) + "".join(
                str(rng.randint(0, 9)) for _ in range(bban_len - 4))
        else:
            bban = "".join(str(rng.randint(0, 9)) for _ in range(bban_len))
        correct = iban_check_digits(country, bban)
        emitted = correct
        while emitted == correct:
            emitted = f"{rng.randint(2, 98):02d}"
        value = country + emitted + bban
        # Rule B: no 16-digit window inside the long digit run may be Luhn-valid.
        if digit_runs_clean(value):
            break
    assert iban_mod97(value) != 1
    return {
        "value": value,
        "formatted": " ".join(value[i:i + 4] for i in range(0, len(value), 4)),
        "check": "iso13616_mod97",
        "broken_by": f"check digits {emitted} substituted for the correct {correct}",
    }


def make_eu_vat(rng: random.Random, country: str) -> dict:
    if country == "DE":
        first8 = "".join(str(rng.randint(0, 9)) for _ in range(8))
        correct = de_vat_check_digit(first8)
        emitted = _other_digit(rng, correct)
        return {
            "value": "DE" + first8 + emitted,
            "check": "iso7064_mod11_10",
            "broken_by": f"check digit {emitted} substituted for the correct {correct}",
        }
    if country == "FR":
        siren_body = "".join(str(rng.randint(0, 9)) for _ in range(8))
        siren_correct = luhn_check_digit(siren_body)
        siren = siren_body + _other_digit(rng, siren_correct)   # SIREN made Luhn-invalid
        key_correct = fr_vat_key(siren)
        key = key_correct
        while key == key_correct:
            key = f"{rng.randint(0, 96):02d}"
        return {
            "value": "FR" + key + siren,
            "check": "fr_siren_luhn_and_key_mod97",
            "broken_by": (
                f"SIREN check digit broken (correct {siren_correct}); VAT key {key} "
                f"substituted for the correct {key_correct}"
            ),
        }
    if country == "NL":
        first8 = "".join(str(rng.randint(0, 9)) for _ in range(8))
        correct = nl_vat_check_digit(first8)
        emitted = _other_digit(rng, correct if correct.isdigit() else "0")
        suffix = f"B{rng.randint(1, 99):02d}"
        return {
            "value": "NL" + first8 + emitted + suffix,
            "check": "nl_mod11",
            "broken_by": f"check digit {emitted} substituted for the correct {correct}",
        }
    first10 = "".join(str(rng.randint(0, 9)) for _ in range(10))
    correct = it_vat_check_digit(first10)
    emitted = _other_digit(rng, correct)
    return {
        "value": "IT" + first10 + emitted,
        "check": "it_mod10",
        "broken_by": f"check digit {emitted} substituted for the correct {correct}",
    }


# Two-digit prefixes the IRS does not issue.
EIN_UNISSUED_PREFIXES = ["07", "08", "09", "17", "18", "19", "28", "29", "49", "69", "70", "78", "79", "89"]


def make_ein(rng: random.Random) -> dict:
    prefix = rng.choice(EIN_UNISSUED_PREFIXES)
    body = "".join(str(rng.randint(0, 9)) for _ in range(7))
    return {
        "value": f"{prefix}-{body}",
        "check": "irs_campus_prefix",
        "broken_by": f"prefix {prefix} is not in the IRS published campus-prefix list",
    }


def make_aba(rng: random.Random) -> dict:
    first8 = f"{rng.randint(1, 12):02d}" + "".join(str(rng.randint(0, 9)) for _ in range(6))
    correct = aba_check_digit(first8)
    emitted = _other_digit(rng, correct)
    number = first8 + emitted
    assert not aba_valid(number)
    return {
        "value": number,
        "check": "aba_371_mod10",
        "broken_by": f"check digit {emitted} substituted for the correct {correct}",
    }


def make_ph_tin(rng: random.Random) -> dict:
    payload = "".join(str(rng.randint(1, 9)) for _ in range(1)) + "".join(
        str(rng.randint(0, 9)) for _ in range(7))
    correct = mod11_2_check_digit(payload)
    emitted = _other_digit(rng, correct if correct.isdigit() else "0")
    branch = f"{rng.choice([0, 0, 0, 1, 2, 3]):03d}"
    number = payload + emitted
    return {
        "value": f"{number[0:3]}-{number[3:6]}-{number[6:9]}-{branch}",
        "check": "none_published",
        "broken_by": (
            "BIR does not publish a TIN check-digit algorithm, so no real-checksum "
            f"failure can be asserted. The ninth digit {emitted} also fails the "
            f"dataset-defined ISO 7064 MOD 11-2 surrogate (correct {correct}); that "
            "surrogate is a dataset convention, not a BIR rule."
        ),
    }


def make_vin(rng: random.Random) -> dict:
    alphabet = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    body = [rng.choice(alphabet) for _ in range(17)]
    body[8] = "0"
    correct = vin_check_char("".join(body))
    emitted = _other_char(rng, {correct}, "0123456789X")
    body[8] = emitted
    value = "".join(body)
    return {
        "value": value,
        "check": "vin_mod11_position9",
        "broken_by": f"position-9 character {emitted} substituted for the correct {correct}",
    }


def make_passport(rng: random.Random, country3: str, surname: str, given: str,
                  dob: dt.date, expiry: dt.date, sex: str) -> dict:
    """ICAO 9303 TD3 data page. Document-number and composite check digits broken.

    TD3 line 2 is 44 characters: document number (9, '<'-filled), its check digit,
    nationality (3), date of birth (6), its check digit, sex (1), date of expiry (6),
    its check digit, optional data (14), its check digit, composite check digit.
    The date-of-birth, expiry and optional-data check digits are left correct so the
    zone still parses; a conforming reader rejects the document on the document-number
    and composite digits, which are both wrong by construction.
    """
    doc_no = rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") + "".join(
        str(rng.randint(0, 9)) for _ in range(7))
    doc_field = doc_no.ljust(9, "<")
    doc_cd_correct = mrz_check_digit(doc_field)
    doc_cd = _other_digit(rng, doc_cd_correct)

    dob_field = dob.strftime("%y%m%d")
    exp_field = expiry.strftime("%y%m%d")
    dob_cd = mrz_check_digit(dob_field)
    exp_cd = mrz_check_digit(exp_field)
    optional = "<" * 14
    opt_cd = mrz_check_digit(optional)

    name_field = f"{surname.upper().replace(' ', '<')}<<{given.upper().replace(' ', '<')}"
    line1 = ("P<" + country3 + name_field).ljust(44, "<")[:44]
    # Composite runs over line-2 positions 1-10, 14-20 and 22-43.
    comp_field = doc_field + doc_cd + dob_field + dob_cd + exp_field + exp_cd + optional + opt_cd
    comp_correct = mrz_check_digit(comp_field)
    comp_cd = _other_digit(rng, comp_correct)
    line2 = (doc_field + doc_cd + country3 + dob_field + dob_cd + sex + exp_field + exp_cd
             + optional + opt_cd + comp_cd)
    assert len(line2) == 44, len(line2)
    return {
        "number": doc_no,
        "mrz_line1": line1,
        "mrz_line2": line2,
        "check": "icao9303_731_mod10",
        "broken_by": (
            f"document-number check digit {doc_cd} substituted for the correct "
            f"{doc_cd_correct}; composite check digit {comp_cd} substituted for the "
            f"correct {comp_correct}"
        ),
    }
