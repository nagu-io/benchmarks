#!/usr/bin/env python3
"""Messy Scan — invented names, addresses, catalogue and money formatting.

Split out of ``generate.py`` so that each part of the generator sits in a file small
enough to read in one sitting. ``generate.py`` imports these modules and assembles the
dataset; the code and the data are unchanged by the split, and the seed still produces
a byte-identical ``ground-truth.jsonl``.

Nothing here is copied from a real entity. Organisation and person names are built
from syllable pools, addresses from invented street and locality roots. Money is held
throughout as integer minor units and only ever formatted for display here, so no
rounding can enter through a formatting step.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random


# --------------------------------------------------------------------------- #
# Invented names, addresses, catalogue                                        #
# --------------------------------------------------------------------------- #

ORG_ROOT_A = ["Van", "Mar", "Kel", "Tir", "Bhad", "Sar", "Nel", "Ort", "Quil", "Dar",
              "Ves", "Lom", "Ank", "Ryn", "Tal", "Ceb", "Hal", "Jor", "Mird", "Pel",
              "Sund", "Vrin", "Zeb", "Kant", "Ferr", "Osp", "Brin", "Cald", "Dev", "Emr"]
ORG_ROOT_B = ["trik", "nova", "drin", "vale", "kora", "meth", "sara", "lith", "quen", "dara",
              "born", "cast", "reva", "shil", "tara", "veld", "wick", "yara", "zorn", "amba",
              "essa", "ondo", "urra", "ithe", "olan"]
ORG_SECTOR = ["Polymers", "Logistics", "Textiles", "Instruments", "Foods", "Chemicals",
              "Fabricators", "Components", "Distribution", "Packaging", "Engineering",
              "Trading", "Electricals", "Bearings", "Adhesives", "Castings", "Optics",
              "Filtration", "Abrasives", "Fasteners"]
ORG_SUFFIX = {
    "IN": ["Pvt Ltd", "Private Limited", "LLP", "Industries Pvt Ltd", "& Sons"],
    "US": ["Inc.", "LLC", "Corp.", "Co.", "Holdings LLC"],
    "EU": ["GmbH", "B.V.", "S.r.l.", "SAS", "AG"],
    "PH": ["Corporation", "Inc.", "Enterprises", "Trading Corp."],
}

GIVEN_SYL = {
    "IN": [["Ra", "Vi", "An", "Su", "Ni", "Pra", "Ka", "Ma", "Dhe", "Ish"],
           ["vin", "kesh", "jal", "mit", "tara", "shan", "ndra", "veer", "lata", "nika"]],
    "US": [["Mar", "Dar", "Kel", "Bren", "Cal", "Ver", "Lor", "Trav", "Nol", "Quin"],
           ["den", "isa", "ton", "lyn", "vin", "een", "ford", "ella", "sey", "an"]],
    "EU": [["Ans", "Hen", "Mar", "Rud", "Ing", "Lo", "Ker", "Nie", "Val", "Bern"],
           ["rik", "ke", "tijn", "olf", "rid", "renz", "sten", "wen", "erie", "hard"]],
    "PH": [["Mari", "Dan", "Rho", "Jos", "Cri", "Ime", "Rae", "Ferd", "Lil", "Nor"],
           ["lyn", "ilo", "sel", "wena", "sha", "berto", "nita", "van", "cor", "mae"]],
}
FAMILY_SYL = {
    "IN": [["Kot", "Vas", "Dho", "Mang", "Sur", "Pat", "Jha", "Ran", "Bhal", "Chit"],
           ["wani", "hani", "raja", "aliya", "vekar", "khani", "dora", "sekar", "puria", "manek"]],
    "US": [["Har", "Bram", "Kes", "Dun", "Ol", "Ver", "Nash", "Cald", "Rem", "Sto"],
           ["ley", "well", "trom", "bury", "sen", "field", "wick", "ridge", "man", "ton"]],
    "EU": [["Van", "Mei", "Sch", "Del", "Rho", "Kra", "Bon", "Ver", "Lind", "Alt"],
           ["derveld", "jer", "warz", "monte", "de", "user", "ini", "hoek", "gren", "mann"]],
    "PH": [["Bal", "Man", "Sar", "Del", "Tan", "Vil", "Gab", "Ras", "Lum", "Pan"],
           ["tazar", "sicat", "miento", "gado", "queza", "lamor", "riel", "onda", "bao", "tili"]],
}

STREET_ROOT = ["Harkanwar", "Belmira", "Tarnoc", "Kestrelane", "Vellord", "Marisol",
               "Oakvern", "Sundapa", "Rethen", "Calmora", "Nirvale", "Portham",
               "Ashquin", "Ferrolm", "Duskane", "Milaro", "Cavren", "Torreza"]
STREET_KIND = {
    "IN": ["Road", "Marg", "Cross Road", "Industrial Estate", "GIDC Estate", "Compound"],
    "US": ["Street", "Avenue", "Boulevard", "Drive", "Parkway", "Court"],
    "EU": ["straße", "weg", "laan", "via", "rue", "allee"],
    "PH": ["Street", "Avenue", "Road", "Extension"],
}

CITIES = {
    "IN": [("Surat", "Gujarat", "395"), ("Ahmedabad", "Gujarat", "380"),
           ("Rajkot", "Gujarat", "360"), ("Pune", "Maharashtra", "411"),
           ("Mumbai", "Maharashtra", "400"), ("Bengaluru", "Karnataka", "560"),
           ("Chennai", "Tamil Nadu", "600"), ("Hyderabad", "Telangana", "500"),
           ("New Delhi", "Delhi", "110"), ("Gurugram", "Haryana", "122"),
           ("Noida", "Uttar Pradesh", "201"), ("Kolkata", "West Bengal", "700"),
           ("Jaipur", "Rajasthan", "302"), ("Kochi", "Kerala", "682"),
           ("Ludhiana", "Punjab", "141"), ("Indore", "Madhya Pradesh", "452"),
           ("Bhubaneswar", "Odisha", "751")],
    "US": [("Austin", "TX", "787"), ("Columbus", "OH", "432"), ("Denver", "CO", "802"),
           ("Raleigh", "NC", "276"), ("Phoenix", "AZ", "850"), ("Tampa", "FL", "336"),
           ("Portland", "OR", "972"), ("Nashville", "TN", "372"),
           ("Kansas City", "MO", "641"), ("Boise", "ID", "837")],
    "EU": [("Stuttgart", "DE", "70173"), ("Dortmund", "DE", "44135"),
           ("Lyon", "FR", "69003"), ("Nantes", "FR", "44000"),
           ("Eindhoven", "NL", "5611"), ("Utrecht", "NL", "3511"),
           ("Bologna", "IT", "40121"), ("Bergamo", "IT", "24121")],
    "PH": [("Cebu City", "Cebu", "6000"), ("Quezon City", "Metro Manila", "1100"),
           ("Makati", "Metro Manila", "1200"), ("Davao City", "Davao del Sur", "8000"),
           ("Iloilo City", "Iloilo", "5000"), ("Cagayan de Oro", "Misamis Oriental", "9000")],
}

EU_COUNTRY_NAME = {"DE": "Germany", "FR": "France", "NL": "Netherlands", "IT": "Italy"}
EU_VAT_RATES = {"DE": 19.0, "FR": 20.0, "NL": 21.0, "IT": 22.0}

# Line-item catalogue: (description, hsn_sac, uom, unit price band in major units)
CATALOGUE = [
    ("HDPE granules, injection grade", "39012000", "KG", (72, 145)),
    ("Polypropylene woven sacks 50 kg", "63053200", "NOS", (14, 32)),
    ("Cotton yarn 30s combed", "52051200", "KG", (210, 340)),
    ("Polyester filament yarn 150D", "54024700", "KG", (118, 198)),
    ("Stainless steel fasteners M8x40", "73181500", "NOS", (4, 19)),
    ("Deep groove ball bearing 6204", "84821011", "NOS", (95, 260)),
    ("Industrial adhesive, 5 L pail", "35061000", "PAIL", (620, 1450)),
    ("Corrugated carton 5-ply 600x400", "48191010", "NOS", (28, 74)),
    ("Aluminium extruded profile 6063", "76042910", "KG", (215, 395)),
    ("Copper winding wire 1.2 mm", "85444911", "KG", (640, 980)),
    ("LED panel light 36 W", "94054090", "NOS", (410, 890)),
    ("Hydraulic hose assembly 1/2 in", "40093100", "NOS", (540, 1250)),
    ("Filter cartridge 10 in polypropylene", "84212190", "NOS", (85, 240)),
    ("Silicone gasket sheet 2 mm", "40169390", "SQM", (330, 720)),
    ("Machining service, CNC turning", "998873", "HOUR", (450, 1250)),
    ("Freight, road, full truck load", "996511", "TRIP", (4200, 18500)),
    ("Powder coating, RAL 7035", "998898", "SQM", (95, 260)),
    ("Calibration service, pressure gauge", "998346", "NOS", (700, 2100)),
    ("Software support, annual, per seat", "998313", "SEAT", (1800, 6400)),
    ("Packing and forwarding charges", "996729", "LOT", (600, 3200)),
]

SERVICE_HSN_PREFIXES = ("99",)

CURRENCY = {
    "invoice_in_gst": ("INR", "Rs."), "po_in": ("INR", "Rs."),
    "invoice_us": ("USD", "$"), "po_us": ("USD", "$"),
    "invoice_eu_vat": ("EUR", "EUR "), "po_eu": ("EUR", "EUR "),
    "invoice_ph_bir": ("PHP", "PHP "), "po_ph": ("PHP", "PHP "),
}

# Bilingual label sets used by tier 5 (two languages on one page).
BILINGUAL = {
    "hi": {
        "name": "हिन्दी",
        "iso": "hi",
        "script": "Devanagari",
        "labels": {
            "tax_invoice": "कर चालान", "supplier": "आपूर्तिकर्ता", "buyer": "क्रेता",
            "date": "दिनांक", "description": "विवरण", "quantity": "मात्रा",
            "rate": "दर", "amount": "राशि", "total": "कुल", "tax": "कर",
            "signature": "हस्ताक्षर", "address": "पता", "name": "नाम", "page": "पृष्ठ",
            "enclosures": "संलग्न दस्तावेज़ सूची",
            "note": "यह प्रति कार्यालय अभिलेख हेतु संलग्न है।",
        },
    },
    "gu": {
        "name": "ગુજરાતી",
        "iso": "gu",
        "script": "Gujarati",
        "labels": {
            "tax_invoice": "કર બિલ", "supplier": "સપ્લાયર", "buyer": "ખરીદનાર",
            "date": "તારીખ", "description": "વિગત", "quantity": "જથ્થો",
            "rate": "દર", "amount": "રકમ", "total": "કુલ", "tax": "વેરો",
            "signature": "સહી", "address": "સરનામું", "name": "નામ", "page": "પાનું",
            "enclosures": "જોડાયેલ દસ્તાવેજોની યાદી",
            "note": "આ નકલ કચેરીના રેકોર્ડ માટે જોડવામાં આવી છે.",
        },
    },
    "tl": {
        "name": "Tagalog",
        "iso": "tl",
        "script": "Latin",
        "labels": {
            "tax_invoice": "Singil sa Buwis", "supplier": "Tagapagtustos", "buyer": "Mamimili",
            "date": "Petsa", "description": "Paglalarawan", "quantity": "Dami",
            "rate": "Presyo", "amount": "Halaga", "total": "Kabuuan", "tax": "Buwis",
            "signature": "Lagda", "address": "Tirahan", "name": "Pangalan", "page": "Pahina",
            "enclosures": "Talaan ng mga kalakip na dokumento",
            "note": "Ang kopyang ito ay nakalakip para sa talaan ng opisina.",
        },
    },
}

LOCALE_SECOND_LANGUAGE = {"IN": ["hi", "gu"], "PH": ["tl"], "US": ["hi", "tl"], "EU": ["hi", "tl"]}

DATE_DISPLAY = {"IN": "%d/%m/%Y", "US": "%m/%d/%Y", "EU": "%d.%m.%Y", "PH": "%m/%d/%Y"}


# --------------------------------------------------------------------------- #
# Money helpers (integer minor units throughout)                              #
# --------------------------------------------------------------------------- #

def pct_minor(base_minor: int, rate_percent: float) -> int:
    """Round-half-up application of a percentage rate to an integer minor amount.

    rate_percent is held to two decimals (basis points) so the arithmetic is exact.
    """
    rate_bp = int(round(rate_percent * 100))
    return (base_minor * rate_bp + 5000) // 10000


def dec(minor: int) -> str:
    """Canonical two-decimal string for a signed integer minor amount."""
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    return f"{sign}{minor // 100}.{minor % 100:02d}"


def group_indian(integer_part: str) -> str:
    if len(integer_part) <= 3:
        return integer_part
    head, tail = integer_part[:-3], integer_part[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def fmt_money(minor: int, currency: str) -> str:
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    ip, fp = str(minor // 100), f"{minor % 100:02d}"
    if currency == "INR":
        return f"{sign}{group_indian(ip)}.{fp}"
    return f"{sign}{int(ip):,}.{fp}"


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
         "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digit_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three_digit_words(n: int) -> str:
    out = []
    if n >= 100:
        out.append(_ONES[n // 100] + " Hundred")
        n %= 100
    if n:
        out.append(_two_digit_words(n))
    return " ".join(out)


def words_indian(rupees: int) -> str:
    if rupees == 0:
        return "Zero"
    parts = []
    crore, rupees = divmod(rupees, 10_000_000)
    lakh, rupees = divmod(rupees, 100_000)
    thousand, rupees = divmod(rupees, 1000)
    if crore:
        parts.append(_three_digit_words(crore) + " Crore")
    if lakh:
        parts.append(_two_digit_words(lakh) + " Lakh")
    if thousand:
        parts.append(_two_digit_words(thousand) + " Thousand")
    if rupees:
        parts.append(_three_digit_words(rupees))
    return " ".join(parts)


def words_western(units: int) -> str:
    if units == 0:
        return "Zero"
    scales = [(1_000_000_000, "Billion"), (1_000_000, "Million"), (1000, "Thousand")]
    parts = []
    for size, label in scales:
        chunk, units = divmod(units, size)
        if chunk:
            parts.append(_three_digit_words(chunk) + " " + label)
    if units:
        parts.append(_three_digit_words(units))
    return " ".join(parts)


def amount_in_words(minor: int, currency: str) -> str:
    major, minorpart = divmod(abs(minor), 100)
    if currency == "INR":
        body = words_indian(major)
        tail = f" and {_two_digit_words(minorpart)} Paise" if minorpart else ""
        return f"Rupees {body}{tail} Only"
    names = {"USD": ("Dollars", "Cents"), "EUR": ("Euro", "Cents"), "PHP": ("Pesos", "Centavos")}
    unit, sub = names[currency]
    body = words_western(major)
    tail = f" and {_two_digit_words(minorpart)} {sub}" if minorpart else ""
    return f"{unit} {body}{tail} Only"


# --------------------------------------------------------------------------- #
# Small builders                                                              #
# --------------------------------------------------------------------------- #

def rng_for(master_seed: int, key: str) -> random.Random:
    """Independent per-document stream: changing the document count does not
    change any other document."""
    digest = hashlib.sha256(f"{master_seed}:{key}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def org_name(rng: random.Random, locale: str) -> str:
    root = rng.choice(ORG_ROOT_A) + rng.choice(ORG_ROOT_B)
    return f"{root.capitalize()} {rng.choice(ORG_SECTOR)} {rng.choice(ORG_SUFFIX[locale])}"


def person_name(rng: random.Random, locale: str) -> tuple[str, str]:
    g = GIVEN_SYL[locale]
    f = FAMILY_SYL[locale]
    given = rng.choice(g[0]) + rng.choice(g[1])
    family = rng.choice(f[0]) + rng.choice(f[1])
    return given.capitalize(), family.capitalize()


def address(rng: random.Random, locale: str) -> dict:
    city, region, pin_prefix = rng.choice(CITIES[locale])
    unit = rng.randint(1, 480)
    street = rng.choice(STREET_ROOT) + (
        "" if locale != "EU" else "")
    kind = rng.choice(STREET_KIND[locale])
    if locale == "EU":
        line1 = f"{street}{kind} {unit}"
        postcode = pin_prefix if len(pin_prefix) == 5 else f"{pin_prefix} {rng.choice('ABCDEFGHJKLMNPRSTVWXYZ')}{rng.choice('ABCDEFGHJKLMNPRSTVWXYZ')}"
        line2 = f"Block {rng.randint(1, 9)}"
        return {"line1": line1, "line2": line2, "city": city, "region": region,
                "postcode": postcode, "country": EU_COUNTRY_NAME[region], "country_code": region}
    if locale == "IN":
        line1 = f"Plot {unit}, {street} {kind}"
        line2 = f"{rng.choice(['Sector', 'Phase', 'Zone'])} {rng.randint(1, 9)}"
        postcode = pin_prefix + f"{rng.randint(0, 999):03d}"
        return {"line1": line1, "line2": line2, "city": city, "region": region,
                "postcode": postcode, "country": "India", "country_code": "IN"}
    if locale == "US":
        line1 = f"{unit * 7 + 100} {street} {kind}"
        line2 = f"Suite {rng.randint(100, 940)}"
        postcode = pin_prefix + f"{rng.randint(0, 99):02d}"
        return {"line1": line1, "line2": line2, "city": city, "region": region,
                "postcode": postcode, "country": "United States", "country_code": "US"}
    line1 = f"{unit} {street} {kind}"
    line2 = f"Barangay {rng.choice(STREET_ROOT)}"
    return {"line1": line1, "line2": line2, "city": city, "region": region,
            "postcode": pin_prefix, "country": "Philippines", "country_code": "PH"}


def flat_address(a: dict) -> str:
    return ", ".join([a["line1"], a["line2"], a["city"], f'{a["region"]} {a["postcode"]}', a["country"]])


def pick_lines(rng: random.Random, currency: str, count: int, price_scale: float) -> list[dict]:
    chosen = rng.sample(CATALOGUE, count)
    lines = []
    for i, (desc, hsn, uom, band) in enumerate(chosen, start=1):
        if uom in ("KG", "SQM"):
            quantity = round(rng.uniform(5, 480), 2)
        elif uom in ("HOUR", "SEAT", "TRIP", "LOT", "PAIL"):
            quantity = float(rng.randint(1, 24))
        else:
            quantity = float(rng.randint(1, 600))
        unit_minor = int(round(rng.uniform(band[0], band[1]) * price_scale * 100))
        qty_1000 = int(round(quantity * 1000))
        amount_minor = (unit_minor * qty_1000 + 500) // 1000
        lines.append({
            "sl": i,
            "description": desc,
            "hsn_sac": hsn,
            "uom": uom,
            "quantity": f"{quantity:.2f}" if quantity != int(quantity) else f"{int(quantity)}",
            "quantity_thousandths": qty_1000,
            "unit_price": dec(unit_minor),
            "unit_price_minor": unit_minor,
            "amount": dec(amount_minor),
            "amount_minor": amount_minor,
        })
    return lines


def date_between(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=rng.randint(0, (end - start).days))
