"""Match rules, charter section 3.3.2.

One shared normalisation function, applied identically to every system's output
(charter section 5.3). There is no per-model post-processing anywhere in this
package.

Rules by field class:

    identifier, code   exact:      NFKC, outer whitespace stripped, case kept
    date               normalised: parsed to an ISO 8601 calendar date
    amount             normalised: numeric value plus currency code
    rate, number       normalised: numeric value
    name               normalised: case, punctuation, diacritics, honorifics,
                                   multiple spaces
    enum, boolean      normalised: case and whitespace
    free_text          tolerance rule, reported separately from the exact and
                       normalised classes

`exact_strict` (byte-for-byte string equality) is computed for every instance
and reported as a diagnostic column beside the match rule for the class.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

# --------------------------------------------------------------------------- #
# Primitives                                                                   #
# --------------------------------------------------------------------------- #

_HONORIFICS = (
    "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "professor", "shri", "sri",
    "smt", "sh", "kum", "messrs", "m/s", "ms.", "er", "adv", "capt", "col",
    "maj", "rev", "hon", "sir", "madam", "mdm",
)

# Every non-ASCII character in this file is written as a \u escape, so the
# source is pure ASCII and survives any transport that is not byte-exact.
_CURRENCY_SYMBOLS = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR", "र": "INR",
    "$": "USD", "us$": "USD", "usd": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
    "₱": "PHP", "php": "PHP", "p": None,  # bare P is ambiguous, not mapped
    "¥": "JPY", "jpy": "JPY",
    "aed": "AED", "sgd": "SGD", "aud": "AUD", "cad": "CAD", "chf": "CHF",
}

_TRUE = {"true", "t", "yes", "y", "1", "1.0", "on"}
_FALSE = {"false", "f", "no", "n", "0", "0.0", "off"}

_MISSING = object()


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def collapse_ws(text: str) -> str:
    return " ".join(text.split())


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    )


def strip_punctuation(text: str) -> str:
    return "".join(
        " " if unicodedata.category(ch).startswith("P") or ch in "|/\\" else ch
        for ch in text
    )


def as_text(value: Any) -> str | None:
    """Coerce a returned value to text. None and empty mean absent."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, str):
        return value
    return None


def is_absent(value: Any) -> bool:
    """An explicit null or an empty value."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


# --------------------------------------------------------------------------- #
# Class normalisers                                                            #
# --------------------------------------------------------------------------- #


def norm_exact(text: str) -> str:
    """Identifiers and codes: NFKC, outer whitespace stripped, case kept."""
    return nfkc(text).strip()


_HONORIFIC_RE = re.compile(
    r"^(?:m/s|messrs|mr|mrs|ms|miss|mx|dr|prof|professor|shri|sri|smt|sh|kum|"
    r"er|adv|capt|col|maj|rev|hon|sir|madam|mdm)\.?[\s,]+",
    re.IGNORECASE,
)


def norm_name(text: str) -> str:
    """Names: case, punctuation, diacritics, honorifics, multiple spaces."""
    t = collapse_ws(strip_diacritics(nfkc(text)).casefold())
    while True:
        stripped = _HONORIFIC_RE.sub("", t, count=1)
        if stripped == t:
            break
        t = stripped
    t = collapse_ws(strip_punctuation(t))
    parts = [p for p in t.split(" ") if p]
    while parts and parts[0] in _HONORIFICS:
        parts.pop(0)
    return " ".join(parts)


def norm_enum(text: str) -> str:
    t = nfkc(text).casefold().replace("_", " ").replace("-", " ")
    return collapse_ws(t)


def norm_free_text(text: str) -> str:
    """The stated tolerance rule for the free-text class.

    NFKC, case folded, diacritics stripped, punctuation replaced by a space,
    whitespace collapsed. Printed in every report so a reader knows exactly what
    tolerance the free-text figure was scored under.
    """
    t = strip_diacritics(nfkc(text)).casefold()
    t = strip_punctuation(t)
    return collapse_ws(t)


FREE_TEXT_TOLERANCE_RULE = (
    "Unicode NFKC, case folded, diacritics stripped, punctuation replaced by a "
    "space, whitespace collapsed, then string equality."
)


def norm_boolean(text: str) -> str | None:
    t = collapse_ws(nfkc(text).casefold())
    if t in _TRUE:
        return "true"
    if t in _FALSE:
        return "false"
    return None


# --------------------------------------------------------------------------- #
# Dates                                                                        #
# --------------------------------------------------------------------------- #

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_NUMERIC_DATE_RE = re.compile(r"^(\d{1,4})[-/. ](\d{1,2})[-/. ](\d{1,4})$")
_TEXT_DATE_RE = re.compile(r"^(\d{1,2})\s+([a-z]+)\.?\s+(\d{2,4})$")
_TEXT_DATE_RE2 = re.compile(r"^([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{2,4})$")


@dataclass(frozen=True)
class DateParse:
    value: _dt.date | None
    ambiguous: bool = False


def parse_date(text: str, *, display_format: str | None = None) -> DateParse:
    """Parse a date to an ISO 8601 calendar date.

    `display_format` is the document's own printed date format, taken from the
    dataset ground truth (`display_formats.date`). It is a property of the item,
    not of the model, and it is used identically for every model to break the
    day/month ambiguity in numeric dates.
    """
    if text is None:
        return DateParse(None)
    t = collapse_ws(nfkc(str(text))).strip().strip(",").casefold()
    if not t:
        return DateParse(None)

    # Strip a time component if a model returned one.
    t = re.split(r"[t ]\d{1,2}:\d{2}", t)[0].strip()

    m = _TEXT_DATE_RE.match(t)
    if m and m.group(2) in _MONTHS:
        return _safe_date(_year(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    m = _TEXT_DATE_RE2.match(t)
    if m and m.group(1) in _MONTHS:
        return _safe_date(_year(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))

    m = _NUMERIC_DATE_RE.match(t)
    if not m:
        return DateParse(None)
    a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if len(m.group(1)) == 4:                       # YYYY-MM-DD
        return _safe_date(a, b, c)
    if len(m.group(3)) == 4 or c > 31:             # DD/MM/YYYY or MM/DD/YYYY
        year = _year(m.group(3))
        day_first = _day_first(display_format)
        first, second = (a, b) if day_first else (b, a)
        parsed = _safe_date(year, second, first)
        if parsed.value is not None:
            return DateParse(parsed.value, ambiguous=(a <= 12 and b <= 12 and a != b))
        # The stated display format does not yield a valid date, so try the
        # other order and mark the instance ambiguous.
        first, second = (b, a) if day_first else (a, b)
        parsed = _safe_date(year, second, first)
        return DateParse(parsed.value, ambiguous=True)
    return DateParse(None)


def _day_first(display_format: str | None) -> bool:
    if not display_format:
        return True  # ISO-adjacent default; every dataset record states its own
    fmt = display_format.replace("%", "")
    for ch in fmt:
        if ch in "dm":
            return ch == "d"
    return True


def _year(raw: str) -> int:
    y = int(raw)
    if y < 100:
        return 2000 + y if y < 70 else 1900 + y
    return y


def _safe_date(year: int, month: int, day: int) -> DateParse:
    try:
        return DateParse(_dt.date(year, month, day))
    except ValueError:
        return DateParse(None)


# --------------------------------------------------------------------------- #
# Amounts and numbers                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Amount:
    value: Decimal | None
    currency: str | None
    currency_stated: bool


_CURRENCY_TOKEN_RE = re.compile(
    "[a-z$\\u20ac\\u00a3\\u20b9\\u20b1\\u00a5]+\\.?", re.IGNORECASE
)


def parse_amount(text: str, *, decimal_separator: str | None = None) -> Amount:
    """A money value: numeric value plus currency code.

    Separators, symbols and whitespace are removed, as charter section 3.3.2
    requires. `decimal_separator` is the document's own printed convention from
    the dataset ground truth, used identically for every model where a single
    separator is genuinely ambiguous.
    """
    if text is None:
        return Amount(None, None, False)
    raw = nfkc(str(text)).strip()
    if not raw:
        return Amount(None, None, False)

    currency = None
    for token in _CURRENCY_TOKEN_RE.findall(raw):
        key = token.casefold()
        if key in _CURRENCY_SYMBOLS and _CURRENCY_SYMBOLS[key]:
            currency = _CURRENCY_SYMBOLS[key]
            break
    if currency is None:
        # A bare three-letter ISO code such as SEK that is not in the table.
        m = re.search(r"\b([A-Z]{3})\b", raw)
        if m:
            currency = m.group(1)

    negative = ("(" in raw and ")" in raw) or bool(re.search(r"-\s*[\d.,]*\d", raw))
    # Take the numeric run itself, so a currency word such as "Rs." does not
    # leave a stray separator behind.
    match = re.search("\\d[\\d.,\\s\\u00a0'\\u2019]*\\d|\\d", raw)
    if not match:
        return Amount(None, currency, currency is not None)
    body = re.sub("[\\s\\u00a0'\\u2019]", "", match.group(0))
    if not re.search(r"\d", body):
        return Amount(None, currency, currency is not None)

    number = _to_decimal(body, decimal_separator)
    if number is None:
        return Amount(None, currency, currency is not None)
    if negative:
        number = -number
    return Amount(number, currency, currency is not None)


def _to_decimal(body: str, decimal_separator: str | None) -> Decimal | None:
    commas = body.count(",")
    dots = body.count(".")
    if commas and dots:
        # The rightmost separator is the decimal point.
        dec = "," if body.rfind(",") > body.rfind(".") else "."
        thousands = "." if dec == "," else ","
        body = body.replace(thousands, "").replace(dec, ".")
    elif commas or dots:
        sep = "," if commas else "."
        parts = body.split(sep)
        tail = parts[-1]
        if len(parts) > 2:
            body = body.replace(sep, "")            # 1,23,456 or 1.234.567
        elif len(tail) == 3 and len(parts[0]) > 0:
            # Ambiguous: 1,234 could be one thousand two hundred and thirty
            # four, or one point two three four. The document's own decimal
            # separator decides, and the default treats it as a group.
            if decimal_separator and decimal_separator == sep:
                body = body.replace(sep, ".")
            else:
                body = body.replace(sep, "")
        else:
            body = body.replace(sep, ".")
    try:
        return Decimal(body)
    except (InvalidOperation, ValueError):
        return None


def parse_number(text: str, *, decimal_separator: str | None = None) -> Decimal | None:
    """A plain number or a rate. A trailing percent sign is dropped."""
    if text is None:
        return None
    raw = nfkc(str(text)).strip()
    if not raw:
        return None
    raw = raw.replace("%", "").replace("percent", "").strip()
    amount = parse_amount(raw, decimal_separator=decimal_separator)
    return amount.value


def decimals_equal(a: Decimal | None, b: Decimal | None, tolerance: Decimal | None = None) -> bool:
    if a is None or b is None:
        return False
    if tolerance is None or tolerance == 0:
        return a == b
    return abs(a - b) <= tolerance
