#!/usr/bin/env python3
"""Messy Scan — field schemas and checksum rules per document type.

Split out of ``generate.py`` so that each part of the generator sits in a file small
enough to read in one sitting. ``generate.py`` imports these modules and assembles the
dataset; the code and the data are unchanged by the split, and the seed still produces
a byte-identical ``ground-truth.jsonl``.

``SCHEMAS`` names every field a document type carries and its kind, which is what
``validate.py`` checks completeness against. ``IDENTIFIER_CHECKS`` names, for each
identifier field, the published rule the value is broken against.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# Field schemas per document type                                             #
# --------------------------------------------------------------------------- #

SCHEMAS = {
    "invoice_in_gst": {
        "supplier_name": "string", "supplier_address": "string", "supplier_gstin": "identifier",
        "supplier_pan": "identifier", "supplier_state": "string", "supplier_state_code": "string",
        "buyer_name": "string", "buyer_address": "string", "buyer_gstin": "identifier",
        "place_of_supply": "string", "invoice_number": "string", "invoice_date": "date",
        "due_date": "date", "line_items": "line_items", "taxable_value": "money",
        "tax_kind": "enum", "cgst_rate": "rate", "cgst_amount": "money", "sgst_rate": "rate",
        "sgst_amount": "money", "igst_rate": "rate", "igst_amount": "money",
        "total_tax": "money", "round_off": "money", "invoice_total": "money",
        "amount_in_words": "string", "currency": "string",
        "bank_account_number": "string", "bank_ifsc": "identifier",
    },
    "invoice_us": {
        "vendor_name": "string", "vendor_address": "string", "vendor_ein": "identifier",
        "vendor_phone": "string", "bill_to_name": "string", "bill_to_address": "string",
        "ship_to_address": "string", "invoice_number": "string", "invoice_date": "date",
        "due_date": "date", "payment_terms": "string", "po_reference": "string",
        "line_items": "line_items", "subtotal": "money", "discount": "money",
        "sales_tax_rate": "rate", "sales_tax_amount": "money", "shipping": "money",
        "invoice_total": "money", "amount_in_words": "string", "currency": "string",
        "ach_routing_number": "identifier", "ach_account_number": "string",
    },
    "invoice_eu_vat": {
        "supplier_name": "string", "supplier_address": "string", "supplier_country": "string",
        "supplier_vat_number": "identifier", "customer_name": "string",
        "customer_address": "string", "customer_country": "string",
        "customer_vat_number": "identifier", "invoice_number": "string",
        "invoice_date": "date", "supply_date": "date", "line_items": "line_items",
        "net_total": "money", "vat_rate": "rate", "vat_amount": "money",
        "gross_total": "money", "reverse_charge": "bool", "currency": "string",
        "iban": "identifier", "bic": "string", "amount_in_words": "string",
    },
    "invoice_ph_bir": {
        "seller_name": "string", "seller_address": "string", "seller_tin": "identifier",
        "buyer_name": "string", "buyer_address": "string", "buyer_tin": "identifier",
        "si_number": "string", "invoice_date": "date", "permit_number": "string",
        "line_items": "line_items", "vatable_sales": "money", "vat_exempt_sales": "money",
        "zero_rated_sales": "money", "vat_rate": "rate", "vat_amount": "money",
        "total_amount_due": "money", "amount_in_words": "string", "currency": "string",
    },
    "kyc_aadhaar": {
        "holder_name": "string", "holder_dob": "date", "holder_gender": "enum",
        "holder_address": "string", "father_or_guardian": "string",
        "aadhaar_number": "identifier", "enrolment_number": "string",
        "passport_number": "identifier", "passport_country": "string",
        "passport_issue_date": "date", "passport_expiry_date": "date",
        "mrz_line1": "string", "mrz_line2": "string",
        "utility_provider": "string", "utility_consumer_number": "string",
        "utility_billing_period": "string", "units_consumed": "number",
        "tariff_rate": "rate", "energy_charge": "money", "fixed_charge": "money",
        "electricity_duty_rate": "rate", "electricity_duty": "money",
        "utility_arrears": "money", "utility_total": "money",
        "utility_due_date": "date", "currency": "string",
    },
    "kyc_pan": {
        "holder_name": "string", "holder_dob": "date", "holder_gender": "enum",
        "holder_address": "string", "father_or_guardian": "string",
        "pan_number": "identifier", "pan_issue_date": "date",
        "passport_number": "identifier", "passport_country": "string",
        "passport_issue_date": "date", "passport_expiry_date": "date",
        "mrz_line1": "string", "mrz_line2": "string",
        "card_number": "identifier", "card_expiry": "string", "card_holder": "string",
        "utility_provider": "string", "utility_consumer_number": "string",
        "utility_billing_period": "string", "units_consumed": "number",
        "tariff_rate": "rate", "energy_charge": "money", "fixed_charge": "money",
        "electricity_duty_rate": "rate", "electricity_duty": "money",
        "utility_arrears": "money", "utility_total": "money",
        "utility_due_date": "date", "currency": "string",
    },
    "claim_motor": {
        "insurer_name": "string", "policy_number": "string", "claim_number": "string",
        "claim_date": "date", "insured_name": "string", "insured_address": "string",
        "insured_dob": "date", "insured_phone": "string", "incident_date": "date",
        "incident_location": "string", "incident_description": "string",
        "vehicle_registration": "string", "vehicle_make_model": "string",
        "vehicle_vin": "identifier", "garage_name": "string",
        "estimate_lines": "line_items", "assessed_total": "money",
        "policy_excess": "money", "salvage_value": "money", "net_payable": "money",
        "settlement_account": "string", "settlement_ifsc": "identifier",
        "currency": "string", "surveyor_name": "string",
    },
    "claim_health": {
        "insurer_name": "string", "policy_number": "string", "claim_number": "string",
        "claim_date": "date", "insured_name": "string", "insured_address": "string",
        "insured_dob": "date", "insured_phone": "string", "hospital_name": "string",
        "admission_date": "date", "discharge_date": "date", "diagnosis": "string",
        "treating_doctor": "string", "sum_insured": "money",
        "estimate_lines": "line_items", "assessed_total": "money",
        "co_pay_rate": "rate", "co_pay_amount": "money", "policy_excess": "money",
        "net_payable": "money", "settlement_account": "string",
        "settlement_ifsc": "identifier", "currency": "string",
    },
    "claim_property": {
        "insurer_name": "string", "policy_number": "string", "claim_number": "string",
        "claim_date": "date", "insured_name": "string", "insured_address": "string",
        "insured_phone": "string", "peril": "enum", "incident_date": "date",
        "risk_location": "string", "incident_description": "string",
        "estimate_lines": "line_items", "assessed_total": "money",
        "policy_excess": "money", "salvage_value": "money", "net_payable": "money",
        "settlement_account": "string", "settlement_ifsc": "identifier",
        "currency": "string", "surveyor_name": "string", "sum_insured": "money",
    },
    "purchase_order": {
        "buyer_org": "string", "buyer_address": "string", "ship_to_address": "string",
        "vendor_name": "string", "vendor_address": "string", "vendor_code": "string",
        "vendor_tax_id": "identifier", "po_number": "string", "po_date": "date",
        "required_by": "date", "payment_terms": "string", "incoterm": "string",
        "line_items": "line_items", "subtotal": "money", "tax_rate": "rate",
        "tax_amount": "money", "freight": "money", "po_total": "money",
        "amount_in_words": "string", "currency": "string", "cost_centre": "string",
        "approver_name": "string", "approver_title": "string",
    },
}
SCHEMAS["po_in"] = SCHEMAS["po_us"] = SCHEMAS["po_eu"] = SCHEMAS["po_ph"] = SCHEMAS["purchase_order"]

# Which fields carry an identifier, and which named check each one must fail.
IDENTIFIER_CHECKS = {
    "supplier_gstin": "gstn_mod36",
    "buyer_gstin": "gstn_mod36",
    "supplier_pan": "pan_published_format",
    "pan_number": "pan_published_format",
    "aadhaar_number": "verhoeff",
    "card_number": "luhn",
    "iban": "iso13616_mod97",
    "supplier_vat_number": "eu_vat",
    "customer_vat_number": "eu_vat",
    "vendor_ein": "irs_campus_prefix",
    "ach_routing_number": "aba_371_mod10",
    "bank_ifsc": "rbi_ifsc_format",
    "settlement_ifsc": "rbi_ifsc_format",
    "passport_number": "icao9303_731_mod10",
    "vehicle_vin": "vin_mod11_position9",
    "seller_tin": "none_published",
    "buyer_tin": "none_published",
    "vendor_tax_id": "varies",
}
