#!/usr/bin/env python3
"""Messy Scan — document builders.

Split out of ``generate.py`` so that each part of the generator sits in a file small
enough to read in one sitting. ``generate.py`` imports these modules and assembles the
dataset; the code and the data are unchanged by the split, and the seed still produces
a byte-identical ``ground-truth.jsonl``.

One builder per subtype. Each returns the field values and the ground truth for one
document, drawing every identifier from ``identifiers.py`` and every name, address and
line item from ``content.py``, so a document's arithmetic and its identifiers can be
re-derived independently by ``validate.py``.
"""

from __future__ import annotations

import datetime as dt
import random

from content import (
    CURRENCY, EU_COUNTRY_NAME, EU_VAT_RATES, STREET_KIND, STREET_ROOT, address,
    amount_in_words, date_between, dec, flat_address, org_name, pct_minor, person_name,
    pick_lines,
)
from identifiers import (
    GST_STATE_CODES, make_aadhaar, make_aba, make_card, make_ein, make_eu_vat, make_gstin,
    make_iban, make_ifsc, make_opaque_number, make_pan, make_passport, make_ph_tin, make_vin,
)


# --------------------------------------------------------------------------- #
# Document builders                                                           #
# --------------------------------------------------------------------------- #

def build_invoice_in_gst(rng: random.Random) -> tuple[dict, dict]:
    supplier_addr = address(rng, "IN")
    buyer_addr = address(rng, "IN")
    supplier_name = org_name(rng, "IN")
    buyer_name = org_name(rng, "IN")
    s_state_code = GST_STATE_CODES[supplier_addr["region"]]
    b_state_code = GST_STATE_CODES[buyer_addr["region"]]

    s_pan = make_pan(rng, supplier_name[0])
    b_pan = make_pan(rng, buyer_name[0])
    s_gstin = make_gstin(rng, s_state_code, s_pan["value"])
    b_gstin = make_gstin(rng, b_state_code, b_pan["value"])
    ifsc = make_ifsc(rng, rng.choice(["HDFC", "ICIC", "SBIN", "UTIB", "KKBK", "BARB"]))

    lines = pick_lines(rng, "INR", rng.randint(3, 8), 1.0)
    taxable = sum(l["amount_minor"] for l in lines)
    rate = rng.choice([5.0, 12.0, 18.0, 18.0, 28.0])
    intra = s_state_code == b_state_code
    if intra:
        cgst = pct_minor(taxable, rate / 2)
        sgst = cgst
        igst = 0
        cgst_rate, sgst_rate, igst_rate = rate / 2, rate / 2, 0.0
    else:
        cgst = sgst = 0
        igst = pct_minor(taxable, rate)
        cgst_rate, sgst_rate, igst_rate = 0.0, 0.0, rate
    total_tax = cgst + sgst + igst
    pre_round = taxable + total_tax
    rounded = int(round(pre_round / 100.0)) * 100
    round_off = rounded - pre_round

    inv_date = date_between(rng, dt.date(2025, 4, 1), dt.date(2026, 6, 30))
    fy_start = inv_date.year if inv_date.month >= 4 else inv_date.year - 1
    fields = {
        "supplier_name": supplier_name,
        "supplier_address": flat_address(supplier_addr),
        "supplier_gstin": s_gstin["value"],
        "supplier_pan": s_pan["value"],
        "supplier_state": supplier_addr["region"],
        "supplier_state_code": s_state_code,
        "buyer_name": buyer_name,
        "buyer_address": flat_address(buyer_addr),
        "buyer_gstin": b_gstin["value"],
        "place_of_supply": f'{buyer_addr["region"]} ({b_state_code})',
        # Indian financial year runs April to March, so the series year is the FY start.
        "invoice_number": f'{rng.choice(["INV", "TI", "GST"])}/{fy_start % 100:02d}-{(fy_start + 1) % 100:02d}/{rng.randint(1, 9999):04d}',
        "invoice_date": inv_date.isoformat(),
        "due_date": (inv_date + dt.timedelta(days=rng.choice([15, 30, 45]))).isoformat(),
        "line_items": lines,
        "taxable_value": dec(taxable),
        "tax_kind": "intra_state" if intra else "inter_state",
        "cgst_rate": f"{cgst_rate:.2f}", "cgst_amount": dec(cgst),
        "sgst_rate": f"{sgst_rate:.2f}", "sgst_amount": dec(sgst),
        "igst_rate": f"{igst_rate:.2f}", "igst_amount": dec(igst),
        "total_tax": dec(total_tax),
        "round_off": dec(round_off),
        "invoice_total": dec(rounded),
        "amount_in_words": amount_in_words(rounded, "INR"),
        "currency": "INR",
        "bank_account_number": make_opaque_number(rng, rng.choice([11, 14, 16])),
        "bank_ifsc": ifsc["value"],
    }
    provenance = {
        "supplier_gstin": s_gstin, "supplier_pan": s_pan, "buyer_gstin": b_gstin,
        "bank_ifsc": ifsc,
    }
    aux = {"supplier_addr": supplier_addr, "buyer_addr": buyer_addr, "tax_rate": rate,
           "locale": "IN"}
    return fields, {"provenance": provenance, "aux": aux}


def build_invoice_us(rng: random.Random) -> tuple[dict, dict]:
    vendor_addr = address(rng, "US")
    bill_addr = address(rng, "US")
    ship_addr = address(rng, "US")
    vendor_name = org_name(rng, "US")
    bill_name = org_name(rng, "US")
    ein = make_ein(rng)
    aba = make_aba(rng)

    lines = pick_lines(rng, "USD", rng.randint(3, 7), 0.014)
    subtotal = sum(l["amount_minor"] for l in lines)
    discount = pct_minor(subtotal, rng.choice([0.0, 0.0, 2.0, 5.0]))
    taxable = subtotal - discount
    tax_rate = rng.choice([4.00, 5.75, 6.25, 7.00, 8.25, 8.875])
    tax = pct_minor(taxable, tax_rate)
    shipping = rng.randint(0, 45000)
    total = taxable + tax + shipping

    inv_date = date_between(rng, dt.date(2025, 4, 1), dt.date(2026, 6, 30))
    terms = rng.choice(["Net 30", "Net 45", "Net 15", "2/10 Net 30"])
    fields = {
        "vendor_name": vendor_name,
        "vendor_address": flat_address(vendor_addr),
        "vendor_ein": ein["value"],
        "vendor_phone": f"({rng.randint(201, 989)}) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
        "bill_to_name": bill_name,
        "bill_to_address": flat_address(bill_addr),
        "ship_to_address": flat_address(ship_addr),
        "invoice_number": f"{rng.randint(100000, 999999)}",
        "invoice_date": inv_date.isoformat(),
        "due_date": (inv_date + dt.timedelta(days=int(terms.split()[-1]))).isoformat(),
        "payment_terms": terms,
        "po_reference": f"PO-{rng.randint(10000, 99999)}",
        "line_items": lines,
        "subtotal": dec(subtotal),
        "discount": dec(discount),
        "sales_tax_rate": f"{tax_rate:.3f}",
        "sales_tax_amount": dec(tax),
        "shipping": dec(shipping),
        "invoice_total": dec(total),
        "amount_in_words": amount_in_words(total, "USD"),
        "currency": "USD",
        "ach_routing_number": aba["value"],
        "ach_account_number": make_opaque_number(rng, rng.choice([9, 10, 12])),
    }
    return fields, {"provenance": {"vendor_ein": ein, "ach_routing_number": aba},
                    "aux": {"locale": "US", "tax_rate": tax_rate}}


def build_invoice_eu_vat(rng: random.Random) -> tuple[dict, dict]:
    supplier_addr = address(rng, "EU")
    customer_addr = address(rng, "EU")
    s_country = supplier_addr["country_code"]
    c_country = customer_addr["country_code"]
    supplier_name = org_name(rng, "EU")
    customer_name = org_name(rng, "EU")
    s_vat = make_eu_vat(rng, s_country)
    c_vat = make_eu_vat(rng, c_country)
    iban = make_iban(rng, s_country)

    reverse_charge = s_country != c_country and rng.random() < 0.55
    lines = pick_lines(rng, "EUR", rng.randint(2, 7), 0.012)
    net = sum(l["amount_minor"] for l in lines)
    vat_rate = 0.0 if reverse_charge else EU_VAT_RATES[s_country]
    vat = pct_minor(net, vat_rate)
    gross = net + vat

    inv_date = date_between(rng, dt.date(2025, 4, 1), dt.date(2026, 6, 30))
    fy_start = inv_date.year if inv_date.month >= 4 else inv_date.year - 1
    fields = {
        "supplier_name": supplier_name,
        "supplier_address": flat_address(supplier_addr),
        "supplier_country": EU_COUNTRY_NAME[s_country],
        "supplier_vat_number": s_vat["value"],
        "customer_name": customer_name,
        "customer_address": flat_address(customer_addr),
        "customer_country": EU_COUNTRY_NAME[c_country],
        "customer_vat_number": c_vat["value"],
        "invoice_number": f"{inv_date.year}-{rng.randint(1000, 9999)}",
        "invoice_date": inv_date.isoformat(),
        "supply_date": (inv_date - dt.timedelta(days=rng.randint(0, 12))).isoformat(),
        "line_items": lines,
        "net_total": dec(net),
        "vat_rate": f"{vat_rate:.2f}",
        "vat_amount": dec(vat),
        "gross_total": dec(gross),
        "reverse_charge": "true" if reverse_charge else "false",
        "currency": "EUR",
        "iban": iban["value"],
        "bic": "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(4)) + s_country
               + "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(2)),
        "amount_in_words": amount_in_words(gross, "EUR"),
    }
    return fields, {"provenance": {"supplier_vat_number": s_vat, "customer_vat_number": c_vat,
                                   "iban": iban},
                    "aux": {"locale": "EU", "country": s_country, "tax_rate": vat_rate}}


def build_invoice_ph_bir(rng: random.Random) -> tuple[dict, dict]:
    seller_addr = address(rng, "PH")
    buyer_addr = address(rng, "PH")
    seller_name = org_name(rng, "PH")
    buyer_name = org_name(rng, "PH")
    s_tin = make_ph_tin(rng)
    b_tin = make_ph_tin(rng)

    lines = pick_lines(rng, "PHP", rng.randint(3, 7), 0.72)
    gross_lines = sum(l["amount_minor"] for l in lines)
    exempt = pct_minor(gross_lines, rng.choice([0.0, 0.0, 0.0, 8.0]))
    zero_rated = pct_minor(gross_lines, rng.choice([0.0, 0.0, 0.0, 5.0]))
    vatable = gross_lines - exempt - zero_rated
    vat_rate = 12.0
    vat = pct_minor(vatable, vat_rate)
    total = gross_lines + vat

    inv_date = date_between(rng, dt.date(2025, 4, 1), dt.date(2026, 6, 30))
    fields = {
        "seller_name": seller_name,
        "seller_address": flat_address(seller_addr),
        "seller_tin": s_tin["value"],
        "buyer_name": buyer_name,
        "buyer_address": flat_address(buyer_addr),
        "buyer_tin": b_tin["value"],
        "si_number": f"{rng.randint(100000, 999999)}",
        "invoice_date": inv_date.isoformat(),
        "permit_number": "OCN" + make_opaque_number(rng, 12),
        "line_items": lines,
        "vatable_sales": dec(vatable),
        "vat_exempt_sales": dec(exempt),
        "zero_rated_sales": dec(zero_rated),
        "vat_rate": f"{vat_rate:.2f}",
        "vat_amount": dec(vat),
        "total_amount_due": dec(total),
        "amount_in_words": amount_in_words(total, "PHP"),
        "currency": "PHP",
    }
    return fields, {"provenance": {"seller_tin": s_tin, "buyer_tin": b_tin},
                    "aux": {"locale": "PH", "tax_rate": vat_rate}}


UTILITY_PROVIDERS = ["Torvane Power Distribution", "Meridale Electric Supply",
                     "Calbrent Energy Utility", "Oskira Power Board",
                     "Venhold Electricity Company"]


def _utility_bill(rng: random.Random, addr: dict, holder: str) -> dict:
    units = rng.randint(48, 720)
    tariff_rate = round(rng.uniform(4.2, 9.8), 2)
    energy = int(round(units * tariff_rate * 100))
    fixed = rng.randint(4000, 22000)
    duty_rate = rng.choice([5.0, 7.5, 10.0, 15.0])
    duty = pct_minor(energy + fixed, duty_rate)
    arrears = rng.choice([0, 0, 0, rng.randint(10000, 180000)])
    total = energy + fixed + duty + arrears
    period_end = date_between(rng, dt.date(2025, 6, 1), dt.date(2026, 6, 1))
    period_start = period_end - dt.timedelta(days=rng.choice([28, 30, 31]))
    return {
        "utility_provider": rng.choice(UTILITY_PROVIDERS),
        "utility_consumer_number": f"{rng.randint(10, 99)}-{rng.randint(1000, 9999)}-{rng.randint(100000, 999999)}",
        "utility_billing_period": f"{period_start.isoformat()}/{period_end.isoformat()}",
        "units_consumed": str(units),
        "tariff_rate": f"{tariff_rate:.2f}",
        "energy_charge": dec(energy),
        "fixed_charge": dec(fixed),
        "electricity_duty_rate": f"{duty_rate:.2f}",
        "electricity_duty": dec(duty),
        "utility_arrears": dec(arrears),
        "utility_total": dec(total),
        "utility_due_date": (period_end + dt.timedelta(days=rng.randint(10, 22))).isoformat(),
        "_duty_rate": duty_rate,
        "_holder": holder,
        "_addr": addr,
    }


def build_kyc(rng: random.Random, subtype: str) -> tuple[dict, dict]:
    given, family = person_name(rng, "IN")
    holder = f"{given} {family}"
    g2, f2 = person_name(rng, "IN")
    guardian = f"{g2} {family}"
    addr = address(rng, "IN")
    dob = date_between(rng, dt.date(1962, 1, 1), dt.date(2004, 12, 31))
    sex = rng.choice(["M", "F"])
    issue = date_between(rng, dt.date(2017, 1, 1), dt.date(2023, 12, 31))
    expiry = issue + dt.timedelta(days=365 * 10)
    passport = make_passport(rng, "IND", family, given, dob, expiry, sex)
    util = _utility_bill(rng, addr, holder)

    fields = {
        "holder_name": holder,
        "holder_dob": dob.isoformat(),
        "holder_gender": "Male" if sex == "M" else "Female",
        "holder_address": flat_address(addr),
        "father_or_guardian": guardian,
        "passport_number": passport["number"],
        "passport_country": "India",
        "passport_issue_date": issue.isoformat(),
        "passport_expiry_date": expiry.isoformat(),
        "mrz_line1": passport["mrz_line1"],
        "mrz_line2": passport["mrz_line2"],
    }
    provenance = {"passport_number": passport}
    if subtype == "kyc_aadhaar":
        aadhaar = make_aadhaar(rng)
        fields["aadhaar_number"] = aadhaar["value"]
        fields["enrolment_number"] = (f"{rng.randint(1000, 9999)}/{rng.randint(10000, 99999)}/"
                                      f"{rng.randint(10000, 99999)}")
        provenance["aadhaar_number"] = aadhaar
    else:
        pan = make_pan(rng, family[0])
        card = make_card(rng)
        fields["pan_number"] = pan["value"]
        fields["pan_issue_date"] = date_between(rng, dt.date(2010, 1, 1), dt.date(2024, 12, 31)).isoformat()
        fields["card_number"] = card["value"]
        fields["card_expiry"] = f"{rng.randint(1, 12):02d}/{rng.randint(27, 31)}"
        fields["card_holder"] = holder.upper()
        provenance["pan_number"] = pan
        provenance["card_number"] = card

    for k, v in util.items():
        if not k.startswith("_"):
            fields[k] = v
    fields["currency"] = "INR"
    return fields, {"provenance": provenance,
                    "aux": {"locale": "IN", "addr": addr, "duty_rate": util["_duty_rate"],
                            "holder": holder, "sex": sex, "aadhaar_style": subtype == "kyc_aadhaar"}}


INSURERS = ["Astravell General Insurance", "Corveth Assurance Ltd", "Nimbara Insurance Co.",
            "Trelmont General Insurance", "Vaskiro Assurance"]
GARAGES = ["Rethen Auto Works", "Calmora Motor Garage", "Belmira Body Shop",
           "Torreza Automotive Services"]
HOSPITALS = ["Kestrelane Multispeciality Hospital", "Sundapa Care Institute",
             "Milaro General Hospital", "Ashquin Medical Centre"]
MOTOR_PARTS = [
    ("Front bumper assembly, replace", "NOS", (4200, 18500)),
    ("Bonnet panel, replace", "NOS", (6500, 24000)),
    ("Headlamp assembly RH", "NOS", (3800, 16400)),
    ("Radiator, replace", "NOS", (5200, 19800)),
    ("Windscreen glass, replace", "NOS", (7400, 26500)),
    ("Denting and painting, front section", "HOUR", (450, 1250)),
    ("Wheel alignment and balancing", "LOT", (900, 2400)),
    ("Airbag module, replace", "NOS", (18500, 62000)),
    ("Fender panel LH, repair", "NOS", (2400, 9800)),
    ("Paint material and consumables", "LOT", (3200, 14500)),
]
HEALTH_ITEMS = [
    ("Room rent, semi-private, per day", "DAY", (2400, 9800)),
    ("Consultant visit charges", "NOS", (800, 3200)),
    ("Operation theatre charges", "LOT", (14000, 68000)),
    ("Investigations, pathology", "LOT", (2200, 12500)),
    ("Radiology, CT scan", "NOS", (4500, 14500)),
    ("Pharmacy and consumables", "LOT", (5400, 42000)),
    ("Physiotherapy sessions", "NOS", (600, 2200)),
    ("Nursing charges", "DAY", (900, 3400)),
    ("Implant, orthopaedic", "NOS", (22000, 145000)),
    ("Anaesthesia charges", "LOT", (6500, 28000)),
]
PROPERTY_ITEMS = [
    ("Stock damaged by water ingress", "LOT", (45000, 480000)),
    ("Electrical panel, replace", "NOS", (28000, 145000)),
    ("False ceiling, reinstate", "SQM", (900, 2600)),
    ("Machinery motor rewinding", "NOS", (12000, 68000)),
    ("Building repair, plaster and paint", "SQM", (450, 1400)),
    ("Debris removal and cleaning", "LOT", (18000, 92000)),
    ("Furniture and fixtures, replace", "LOT", (36000, 210000)),
    ("Temporary protection works", "LOT", (9000, 48000)),
]
PERILS = ["Fire", "Flood", "Burglary", "Storm damage", "Impact damage"]
DIAGNOSES = ["Acute appendicitis", "Fracture, left tibia", "Community-acquired pneumonia",
             "Cholelithiasis", "Lumbar disc prolapse", "Dengue fever with thrombocytopenia"]


def _claim_lines(rng: random.Random, catalogue: list, count: int) -> list[dict]:
    chosen = rng.sample(catalogue, count)
    lines = []
    for i, (desc, uom, band) in enumerate(chosen, start=1):
        quantity = float(rng.randint(1, 8)) if uom in ("NOS", "DAY") else float(rng.randint(1, 30))
        unit_minor = int(round(rng.uniform(band[0], band[1]) * 100))
        qty_1000 = int(round(quantity * 1000))
        amount_minor = (unit_minor * qty_1000 + 500) // 1000
        lines.append({
            "sl": i, "description": desc, "hsn_sac": "", "uom": uom,
            "quantity": f"{int(quantity)}", "quantity_thousandths": qty_1000,
            "unit_price": dec(unit_minor), "unit_price_minor": unit_minor,
            "amount": dec(amount_minor), "amount_minor": amount_minor,
        })
    return lines


def build_claim(rng: random.Random, subtype: str) -> tuple[dict, dict]:
    given, family = person_name(rng, "IN")
    insured = f"{given} {family}"
    addr = address(rng, "IN")
    ifsc = make_ifsc(rng, rng.choice(["HDFC", "ICIC", "SBIN", "UTIB", "PUNB"]))
    claim_date = date_between(rng, dt.date(2025, 5, 1), dt.date(2026, 6, 30))
    incident_date = claim_date - dt.timedelta(days=rng.randint(1, 40))
    base = {
        "insurer_name": rng.choice(INSURERS),
        "policy_number": f"{rng.choice(['P', 'MOT', 'HLT', 'FIR'])}/{rng.randint(10, 99)}/"
                         f"{rng.randint(100000, 999999)}",
        "claim_number": f"CLM{claim_date.year}{rng.randint(100000, 999999)}",
        "claim_date": claim_date.isoformat(),
        "insured_name": insured,
        "insured_address": flat_address(addr),
        "insured_phone": f"+91 {rng.randint(70, 99)}{rng.randint(10000000, 99999999)}",
        "settlement_account": make_opaque_number(rng, rng.choice([11, 14, 16])),
        "settlement_ifsc": ifsc["value"],
        "currency": "INR",
    }
    provenance = {"settlement_ifsc": ifsc}

    if subtype == "claim_motor":
        vin = make_vin(rng)
        lines = _claim_lines(rng, MOTOR_PARTS, rng.randint(3, 7))
        assessed = sum(l["amount_minor"] for l in lines)
        excess = rng.choice([100000, 200000, 500000, 1000000])
        salvage = rng.choice([0, 0, rng.randint(20000, 300000)])
        net = assessed - excess - salvage
        fields = dict(base)
        fields.update({
            "insured_dob": date_between(rng, dt.date(1965, 1, 1), dt.date(2002, 12, 31)).isoformat(),
            "incident_date": incident_date.isoformat(),
            "incident_location": f'{addr["city"]}, near {rng.choice(STREET_ROOT)} {rng.choice(STREET_KIND["IN"])}',
            "incident_description": rng.choice([
                "Vehicle struck from the rear while stationary at a signal.",
                "Side impact with a two-wheeler at an unmarked junction.",
                "Front-end damage after collision with a road divider in heavy rain.",
                "Impact with a stationary object while reversing in a parking bay.",
            ]),
            "vehicle_registration": f'{rng.choice(["GJ", "MH", "KA", "TN", "DL"])}'
                                    f'{rng.randint(1, 40):02d}'
                                    f'{rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")}'
                                    f'{rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")}'
                                    f'{rng.randint(1000, 9999)}',
            "vehicle_make_model": rng.choice(["Torvex Sedan 1.5", "Halcyon Hatch 1.2",
                                              "Merida SUV 2.0 D", "Braxen Compact 1.0 T"]),
            "vehicle_vin": vin["value"],
            "garage_name": rng.choice(GARAGES),
            "estimate_lines": lines,
            "assessed_total": dec(assessed),
            "policy_excess": dec(excess),
            "salvage_value": dec(salvage),
            "net_payable": dec(net),
            "surveyor_name": " ".join(person_name(rng, "IN")),
        })
        provenance["vehicle_vin"] = vin
        aux = {"locale": "IN", "reconcile": "motor"}
    elif subtype == "claim_health":
        lines = _claim_lines(rng, HEALTH_ITEMS, rng.randint(4, 8))
        assessed = sum(l["amount_minor"] for l in lines)
        co_pay_rate = rng.choice([0.0, 10.0, 20.0])
        co_pay = pct_minor(assessed, co_pay_rate)
        excess = rng.choice([0, 100000, 250000])
        net = assessed - co_pay - excess
        admission = incident_date
        fields = dict(base)
        fields.update({
            "insured_dob": date_between(rng, dt.date(1955, 1, 1), dt.date(2005, 12, 31)).isoformat(),
            "hospital_name": rng.choice(HOSPITALS),
            "admission_date": admission.isoformat(),
            "discharge_date": (admission + dt.timedelta(days=rng.randint(1, 12))).isoformat(),
            "diagnosis": rng.choice(DIAGNOSES),
            "treating_doctor": "Dr " + " ".join(person_name(rng, "IN")),
            "sum_insured": dec(rng.choice([50000000, 100000000, 200000000, 500000000])),
            "estimate_lines": lines,
            "assessed_total": dec(assessed),
            "co_pay_rate": f"{co_pay_rate:.2f}",
            "co_pay_amount": dec(co_pay),
            "policy_excess": dec(excess),
            "net_payable": dec(net),
        })
        aux = {"locale": "IN", "reconcile": "health"}
    else:
        lines = _claim_lines(rng, PROPERTY_ITEMS, rng.randint(3, 7))
        assessed = sum(l["amount_minor"] for l in lines)
        excess = rng.choice([500000, 1000000, 2500000])
        salvage = rng.choice([0, rng.randint(50000, 700000)])
        net = assessed - excess - salvage
        fields = dict(base)
        fields.update({
            "peril": rng.choice(PERILS),
            "incident_date": incident_date.isoformat(),
            "risk_location": flat_address(address(rng, "IN")),
            "incident_description": rng.choice([
                "Water ingress through a failed roof sheet during heavy rainfall.",
                "Fire originating in an electrical distribution board on the ground floor.",
                "Forced entry through a rear shutter; stock and fixtures removed.",
                "Storm damage to the roof and external cladding of the warehouse.",
            ]),
            "estimate_lines": lines,
            "assessed_total": dec(assessed),
            "policy_excess": dec(excess),
            "salvage_value": dec(salvage),
            "net_payable": dec(net),
            "surveyor_name": " ".join(person_name(rng, "IN")),
            "sum_insured": dec(rng.choice([500000000, 1000000000, 2500000000])),
        })
        aux = {"locale": "IN", "reconcile": "property"}
    return fields, {"provenance": provenance, "aux": aux}


PO_LOCALE = {"po_in": "IN", "po_us": "US", "po_eu": "EU", "po_ph": "PH"}
INCOTERMS = ["EXW", "FOB", "CIF", "DAP", "DDP", "FCA"]


def build_po(rng: random.Random, subtype: str) -> tuple[dict, dict]:
    locale = PO_LOCALE[subtype]
    currency, _ = CURRENCY[subtype]
    buyer_addr = address(rng, locale)
    ship_addr = address(rng, locale)
    vendor_addr = address(rng, locale)
    buyer_org = org_name(rng, locale)
    vendor_name = org_name(rng, locale)

    provenance = {}
    if locale == "IN":
        pan = make_pan(rng, vendor_name[0])
        tax = make_gstin(rng, GST_STATE_CODES[vendor_addr["region"]], pan["value"])
        tax_rate = rng.choice([5.0, 12.0, 18.0, 28.0])
    elif locale == "US":
        tax = make_ein(rng)
        tax_rate = rng.choice([0.0, 6.25, 7.0, 8.25])
    elif locale == "EU":
        tax = make_eu_vat(rng, vendor_addr["country_code"])
        tax_rate = EU_VAT_RATES[vendor_addr["country_code"]]
    else:
        tax = make_ph_tin(rng)
        tax_rate = 12.0
    provenance["vendor_tax_id"] = tax

    scale = {"IN": 1.0, "US": 0.014, "EU": 0.012, "PH": 0.72}[locale]
    lines = pick_lines(rng, currency, rng.randint(2, 8), scale)
    subtotal = sum(l["amount_minor"] for l in lines)
    tax_amount = pct_minor(subtotal, tax_rate)
    freight = rng.choice([0, rng.randint(1000, 90000)])
    total = subtotal + tax_amount + freight

    po_date = date_between(rng, dt.date(2025, 4, 1), dt.date(2026, 6, 30))
    approver_given, approver_family = person_name(rng, locale)
    fields = {
        "buyer_org": buyer_org,
        "buyer_address": flat_address(buyer_addr),
        "ship_to_address": flat_address(ship_addr),
        "vendor_name": vendor_name,
        "vendor_address": flat_address(vendor_addr),
        "vendor_code": f"V{rng.randint(10000, 99999)}",
        "vendor_tax_id": tax["value"],
        "po_number": f'{rng.choice(["PO", "4500", "PUR"])}-{rng.randint(100000, 999999)}',
        "po_date": po_date.isoformat(),
        "required_by": (po_date + dt.timedelta(days=rng.randint(7, 90))).isoformat(),
        "payment_terms": rng.choice(["Net 30", "Net 45", "Net 60", "30 days from GRN",
                                     "50% advance, 50% on delivery"]),
        "incoterm": rng.choice(INCOTERMS),
        "line_items": lines,
        "subtotal": dec(subtotal),
        "tax_rate": f"{tax_rate:.2f}",
        "tax_amount": dec(tax_amount),
        "freight": dec(freight),
        "po_total": dec(total),
        "amount_in_words": amount_in_words(total, currency),
        "currency": currency,
        "cost_centre": f"CC-{rng.randint(1000, 9999)}",
        "approver_name": f"{approver_given} {approver_family}",
        "approver_title": rng.choice(["Head of Procurement", "Purchase Manager",
                                      "Category Lead", "Plant Materials Manager"]),
    }
    return fields, {"provenance": provenance, "aux": {"locale": locale, "tax_rate": tax_rate}}


BUILDERS = {
    "invoice_in_gst": lambda r, s: build_invoice_in_gst(r),
    "invoice_us": lambda r, s: build_invoice_us(r),
    "invoice_eu_vat": lambda r, s: build_invoice_eu_vat(r),
    "invoice_ph_bir": lambda r, s: build_invoice_ph_bir(r),
    "kyc_aadhaar": build_kyc,
    "kyc_pan": build_kyc,
    "claim_motor": build_claim,
    "claim_health": build_claim,
    "claim_property": build_claim,
    "po_in": build_po,
    "po_us": build_po,
    "po_eu": build_po,
    "po_ph": build_po,
}


# --------------------------------------------------------------------------- #
# Logical page plan                                                           #
# --------------------------------------------------------------------------- #

def logical_pages(subtype: str, fields: dict, rng: random.Random) -> list[dict]:
    if subtype.startswith("invoice"):
        pages = [{"kind": subtype}]
        if len(fields["line_items"]) > 6:
            pages = [{"kind": subtype, "part": 1}, {"kind": subtype + "_continued", "part": 2}]
        return pages
    if subtype.startswith("kyc"):
        pages = [{"kind": "id_card_aadhaar" if subtype == "kyc_aadhaar" else "id_card_pan"},
                 {"kind": "passport_page"},
                 {"kind": "utility_bill"}]
        if subtype == "kyc_pan":
            pages.append({"kind": "card_photocopy"})
        return pages
    if subtype.startswith("claim"):
        return [{"kind": subtype}, {"kind": "claim_estimate"}]
    return [{"kind": "purchase_order"}]
