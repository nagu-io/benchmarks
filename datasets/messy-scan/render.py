#!/usr/bin/env python3
"""Messy Scan dataset v1.0 — clean render stage.

Turns each planned document from ``build/documents.jsonl`` into HTML, then renders
it with Chromium through Playwright:

    build/render/<doc_id>/clean.pdf     one PDF, one page per logical page
    build/render/<doc_id>/page-NN.png   one lossless PNG per logical page

The PNGs are what ``degrade.py`` consumes. The PDF is the tier-1 artefact and the
reference for anything that wants the document before any degradation.

Resolution: an A4 page is 210 x 297 mm, which CSS renders at 793.7 x 1122.5 px.
The device scale factor is set to 200/96 so a page comes out at 1654 x 2339 px,
which is 200 dpi. That is the ``render_dpi`` recorded in the degradation plan.

Fonts. IBM Plex Sans, DejaVu Sans, DejaVu Serif, DejaVu Sans Condensed, Carlito
and Caladea are installed and used to vary the look across four layout variants.
Hindi and Gujarati are rendered with Noto Sans Devanagari and Noto Sans Gujarati
(Debian/Ubuntu package ``fonts-noto-core``). Tagalog uses the Latin script and
needs no extra font. If those Noto faces are absent, tier-5 Devanagari and
Gujarati text renders as tofu; ``render.py --check-fonts`` reports this before a
run rather than producing unreadable pages silently.

Chromium is expected at /opt/pw-browsers (PLAYWRIGHT_BROWSERS_PATH). Do not run
``playwright install``.

Usage
-----
    python3 render.py                               # every planned document
    python3 render.py --select splits               # public sample + private split
    python3 render.py --select splits --stratified 100
    python3 render.py --only msc-inv-in_gst-0001
    python3 render.py --check-fonts

Licence: MIT.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import (  # noqa: E402
    BILINGUAL, DATE_DISPLAY, DEFAULT_PLAN_PATH, fmt_money, load_documents,
)

HERE = Path(__file__).resolve().parent
DEFAULT_RENDER_DIR = HERE / "build" / "render"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")

A4_W_CSS = 793.7
A4_H_CSS = 1122.5
TARGET_DPI = 200
DEVICE_SCALE = TARGET_DPI / 96.0

REQUIRED_FONT_LANGS = {"hi": "Noto Sans Devanagari", "gu": "Noto Sans Gujarati"}

VARIANT_FONTS = [
    ("'IBM Plex Sans', 'DejaVu Sans', sans-serif", "'IBM Plex Sans Condensed', 'IBM Plex Sans', sans-serif"),
    ("'DejaVu Sans', sans-serif", "'DejaVu Serif', serif"),
    ("'Carlito', 'DejaVu Sans', sans-serif", "'Caladea', 'DejaVu Serif', serif"),
    ("'DejaVu Sans Condensed', 'DejaVu Sans', sans-serif", "'DejaVu Sans Condensed', sans-serif"),
]
INDIC_STACK = "'Noto Sans Devanagari', 'Noto Sans Gujarati', 'Noto Serif Devanagari', sans-serif"


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #

def e(value) -> str:
    return html.escape(str(value), quote=True)


def disp_date(iso: str, locale: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso
    return d.strftime(DATE_DISPLAY.get(locale, "%d/%m/%Y"))


def money(value: str, currency: str) -> str:
    minor = int(round(float(value) * 100))
    return fmt_money(minor, currency)


def sym(currency: str) -> str:
    return {"INR": "Rs.", "USD": "$", "EUR": "&euro;", "PHP": "PHP"}.get(currency, currency)


def label(rec: dict, key: str, english: str) -> str:
    """Bilingual label for tier 5, plain English elsewhere."""
    bl = rec.get("bilingual_labels")
    if not bl:
        return e(english)
    second = bl["labels"].get(key)
    if not second:
        return e(english)
    cls = "indic" if bl["iso"] in ("hi", "gu") else "latin2"
    return f'{e(english)} <span class="{cls}">/ {e(second)}</span>'


def logo_svg(rec: dict, name: str) -> str:
    """Deterministic invented wordmark. No real logo is used anywhere."""
    seed = sum(ord(c) for c in rec["doc_id"] + name)
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    hue = seed % 360
    shape = seed % 3
    if shape == 0:
        art = '<rect x="2" y="2" width="40" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>'
    elif shape == 1:
        art = '<circle cx="22" cy="22" r="19" fill="none" stroke="currentColor" stroke-width="2"/>'
    else:
        art = '<path d="M4 40 L22 4 L40 40 Z" fill="none" stroke="currentColor" stroke-width="2"/>'
    return (f'<svg class="mark" width="44" height="44" viewBox="0 0 44 44" '
            f'style="color:hsl({hue},32%,28%)">{art}'
            f'<text x="22" y="28" text-anchor="middle" font-size="15" font-family="sans-serif" '
            f'fill="currentColor">{e(initials)}</text></svg>')


def addr_block(addr: str) -> str:
    return "<br>".join(e(part.strip()) for part in addr.split(","))


# --------------------------------------------------------------------------- #
# Stylesheet                                                                  #
# --------------------------------------------------------------------------- #

def stylesheet(variant: int) -> str:
    body_font, head_font = VARIANT_FONTS[variant % len(VARIANT_FONTS)]
    border = ["1px solid #999", "1px solid #444", "1px solid #7a7a7a", "1px solid #333"][variant % 4]
    head_bg = ["#eeeeee", "#ffffff", "#e9e9e9", "#dddddd"][variant % 4]
    return f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #ffffff; }}
body {{ font-family: {body_font}; color: #111; font-size: 10.2pt; line-height: 1.34; }}
.page {{ width: 210mm; height: 297mm; padding: 14mm 13mm; background: #fff;
         position: relative; overflow: hidden; page-break-after: always; }}
.page:last-child {{ page-break-after: auto; }}
h1, h2, h3, .doctitle {{ font-family: {head_font}; margin: 0; }}
.doctitle {{ font-size: 15pt; letter-spacing: 0.2px; }}
.sub {{ font-size: 8.6pt; color: #444; }}
.hdr {{ display: flex; justify-content: space-between; align-items: flex-start;
        border-bottom: {border}; padding-bottom: 3mm; margin-bottom: 4mm; }}
.hdr .mark {{ margin-right: 3mm; vertical-align: top; }}
.orgline {{ display: flex; align-items: flex-start; }}
.org {{ font-family: {head_font}; font-size: 12.4pt; }}
.two {{ display: flex; gap: 6mm; margin-bottom: 4mm; }}
.two > div {{ flex: 1; }}
.box {{ border: {border}; padding: 2.4mm 2.8mm; }}
.k {{ color: #333; font-size: 8.4pt; }}
.v {{ font-size: 9.6pt; }}
table {{ width: 100%; border-collapse: collapse; font-size: 9.1pt; }}
th, td {{ border: {border}; padding: 1.3mm 1.6mm; vertical-align: top; }}
th {{ background: {head_bg}; text-align: left; font-weight: 600; font-size: 8.6pt; }}
td.num, th.num {{ text-align: right; white-space: nowrap; }}
.totals {{ width: 84mm; margin-left: auto; margin-top: 4mm; }}
.totals td {{ padding: 1.1mm 1.6mm; }}
.grand td {{ font-weight: 700; }}
.words {{ margin-top: 3mm; font-size: 9pt; }}
.foot {{ position: absolute; bottom: 12mm; left: 13mm; right: 13mm;
         font-size: 8.2pt; color: #333; border-top: {border}; padding-top: 2.2mm; }}
.sig {{ margin-top: 12mm; text-align: right; font-size: 9pt; }}
.sigline {{ display: inline-block; width: 56mm; border-top: 1px solid #555;
            padding-top: 1.4mm; text-align: center; }}
.kv {{ width: 100%; font-size: 9.2pt; }}
.kv td {{ border: none; padding: 0.7mm 0; }}
.kv td.k2 {{ width: 42%; color: #333; }}
.mono {{ font-family: 'DejaVu Sans Mono', monospace; }}
.mrz {{ font-family: 'DejaVu Sans Mono', monospace; font-size: 11.6pt;
        letter-spacing: 1.1px; background: #f3f3ef; padding: 2mm; border-top: 1px dashed #888; }}
.indic {{ font-family: {INDIC_STACK}; }}
.latin2 {{ font-style: italic; }}
.card {{ border: {border}; padding: 4mm; width: 128mm; }}
.cardhead {{ display: flex; justify-content: space-between; align-items: center;
             border-bottom: {border}; padding-bottom: 2mm; margin-bottom: 3mm; }}
.photo {{ width: 26mm; height: 32mm; border: 1px solid #666; background:
          repeating-linear-gradient(45deg,#e8e8e8,#e8e8e8 3px,#d6d6d6 3px,#d6d6d6 6px);
          display: inline-block; }}
.note {{ font-size: 8.6pt; color: #333; margin-top: 3mm; }}
.stampzone {{ height: 22mm; }}
.small {{ font-size: 8.2pt; }}
.wide {{ letter-spacing: 0.6px; }}
"""


# --------------------------------------------------------------------------- #
# Page templates                                                              #
# --------------------------------------------------------------------------- #

def line_table(rec: dict, lines: list[dict], currency: str, *, show_hsn: bool,
               hsn_label: str = "HSN/SAC", start: int = 0, end: int | None = None) -> str:
    end = len(lines) if end is None else end
    cols = ["#", label(rec, "description", "Description")]
    if show_hsn:
        cols.append(e(hsn_label))
    cols += ["UOM", label(rec, "quantity", "Qty"), label(rec, "rate", "Rate"),
             label(rec, "amount", "Amount")]
    head = "".join(
        f'<th class="num">{c}</th>' if i >= 4 else f"<th>{c}</th>"
        for i, c in enumerate(cols))
    body = []
    for ln in lines[start:end]:
        cells = [f'<td class="num">{ln["sl"]}</td>', f'<td>{e(ln["description"])}</td>']
        if show_hsn:
            cells.append(f'<td>{e(ln["hsn_sac"])}</td>')
        cells += [f'<td>{e(ln["uom"])}</td>',
                  f'<td class="num">{e(ln["quantity"])}</td>',
                  f'<td class="num">{money(ln["unit_price"], currency)}</td>',
                  f'<td class="num">{money(ln["amount"], currency)}</td>']
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def totals_table(rows: list[tuple[str, str]], grand_index: int = -1) -> str:
    out = []
    for i, (k, v) in enumerate(rows):
        cls = ' class="grand"' if i == len(rows) + grand_index or i == grand_index else ""
        out.append(f'<tr{cls}><td>{k}</td><td class="num">{v}</td></tr>')
    return f'<table class="totals">{"".join(out)}</table>'


def tpl_invoice_in_gst(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    lines = f["line_items"]
    split_at = 6 if part else len(lines)
    start, end = (0, split_at) if part in (None, 1) else (split_at, len(lines))
    header = f"""
<div class="hdr">
  <div class="orgline">{logo_svg(rec, f["supplier_name"])}
    <div><div class="org">{e(f["supplier_name"])}</div>
      <div class="sub">{addr_block(f["supplier_address"])}</div>
      <div class="sub">GSTIN {e(f["supplier_gstin"])} &nbsp; PAN {e(f["supplier_pan"])}</div>
    </div></div>
  <div style="text-align:right">
    <div class="doctitle">{label(rec, "tax_invoice", "Tax invoice")}</div>
    <div class="sub">Original for recipient</div>
    <div class="sub">No. {e(f["invoice_number"])}</div>
    <div class="sub">{label(rec, "date", "Date")} {disp_date(f["invoice_date"], "IN")}</div>
    {'<div class="sub">Page 2 of 2 (continued)</div>' if part == 2 else ''}
  </div>
</div>"""
    parties = f"""
<div class="two">
  <div class="box"><div class="k">{label(rec, "buyer", "Bill to")}</div>
    <div class="v">{e(f["buyer_name"])}</div>
    <div class="sub">{addr_block(f["buyer_address"])}</div>
    <div class="sub">GSTIN {e(f["buyer_gstin"])}</div></div>
  <div class="box"><div class="k">Place of supply</div>
    <div class="v">{e(f["place_of_supply"])}</div>
    <div class="sub">Supply type: {e(f["tax_kind"].replace("_", " "))}</div>
    <div class="sub">Due {disp_date(f["due_date"], "IN")}</div>
    <div class="sub">Reverse charge: No</div></div>
</div>"""
    table = line_table(rec, lines, cur, show_hsn=True, start=start, end=end)
    if part == 1:
        return header + parties + table + '<div class="note">Continued on page 2.</div>'
    rows = [(label(rec, "total", "Taxable value"), money(f["taxable_value"], cur))]
    if f["tax_kind"] == "intra_state":
        rows.append((f'CGST @ {f["cgst_rate"]}%', money(f["cgst_amount"], cur)))
        rows.append((f'SGST @ {f["sgst_rate"]}%', money(f["sgst_amount"], cur)))
    else:
        rows.append((f'IGST @ {f["igst_rate"]}%', money(f["igst_amount"], cur)))
    rows.append((label(rec, "tax", "Total tax"), money(f["total_tax"], cur)))
    rows.append(("Round off", money(f["round_off"], cur)))
    rows.append((label(rec, "total", "Invoice total") + f" ({cur})", money(f["invoice_total"], cur)))
    body = header + ("" if part == 2 else parties) + table + totals_table(rows)
    body += f'<div class="words">Amount in words: {e(f["amount_in_words"])}</div>'
    body += f"""
<div class="two" style="margin-top:5mm">
  <div class="box small"><div class="k">Bank details</div>
    A/c {e(f["bank_account_number"])}<br>IFSC {e(f["bank_ifsc"])}</div>
  <div class="box small"><div class="k">Declaration</div>
    We declare that this invoice shows the actual price of the goods described and
    that all particulars are true and correct.</div>
</div>
<div class="sig">For {e(f["supplier_name"])}<div class="stampzone"></div>
  <div class="sigline">{label(rec, "signature", "Authorised signatory")}</div></div>
<div class="foot">Invoice {e(f["invoice_number"])} &middot; {e(f["supplier_name"])} &middot;
  This is a synthetic document generated for benchmark use.</div>"""
    return body


def tpl_invoice_us(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    lines = f["line_items"]
    split_at = 6 if part else len(lines)
    start, end = (0, split_at) if part in (None, 1) else (split_at, len(lines))
    header = f"""
<div class="hdr">
  <div class="orgline">{logo_svg(rec, f["vendor_name"])}
    <div><div class="org">{e(f["vendor_name"])}</div>
      <div class="sub">{addr_block(f["vendor_address"])}</div>
      <div class="sub">EIN {e(f["vendor_ein"])} &nbsp; Tel {e(f["vendor_phone"])}</div></div></div>
  <div style="text-align:right">
    <div class="doctitle">INVOICE</div>
    <div class="sub">Invoice # {e(f["invoice_number"])}</div>
    <div class="sub">{label(rec, "date", "Date")} {disp_date(f["invoice_date"], "US")}</div>
    <div class="sub">Terms {e(f["payment_terms"])}</div>
    {'<div class="sub">Page 2 of 2</div>' if part == 2 else ''}
  </div>
</div>"""
    parties = f"""
<div class="two">
  <div class="box"><div class="k">Bill to</div><div class="v">{e(f["bill_to_name"])}</div>
    <div class="sub">{addr_block(f["bill_to_address"])}</div></div>
  <div class="box"><div class="k">Ship to</div>
    <div class="sub">{addr_block(f["ship_to_address"])}</div></div>
  <div class="box"><div class="k">Reference</div>
    <div class="sub">PO {e(f["po_reference"])}<br>Due {disp_date(f["due_date"], "US")}</div></div>
</div>"""
    table = line_table(rec, lines, cur, show_hsn=True, hsn_label="SKU", start=start, end=end)
    if part == 1:
        return header + parties + table + '<div class="note">Continued on page 2.</div>'
    rows = [("Subtotal", money(f["subtotal"], cur)),
            ("Discount", "-" + money(f["discount"], cur)),
            (f'Sales tax @ {f["sales_tax_rate"]}%', money(f["sales_tax_amount"], cur)),
            ("Shipping and handling", money(f["shipping"], cur)),
            (f"Total due ({cur})", money(f["invoice_total"], cur))]
    body = header + ("" if part == 2 else parties) + table + totals_table(rows)
    body += f'<div class="words">{e(f["amount_in_words"])}</div>'
    body += f"""
<div class="box small" style="margin-top:5mm">Remit by ACH: routing
  {e(f["ach_routing_number"])}, account {e(f["ach_account_number"])}.
  Please quote invoice {e(f["invoice_number"])} with payment.</div>
<div class="sig"><div class="stampzone"></div>
  <div class="sigline">Authorized by</div></div>
<div class="foot">{e(f["vendor_name"])} &middot; Invoice {e(f["invoice_number"])} &middot;
  Synthetic document generated for benchmark use.</div>"""
    return body


def tpl_invoice_eu_vat(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    lines = f["line_items"]
    split_at = 6 if part else len(lines)
    start, end = (0, split_at) if part in (None, 1) else (split_at, len(lines))
    header = f"""
<div class="hdr">
  <div class="orgline">{logo_svg(rec, f["supplier_name"])}
    <div><div class="org">{e(f["supplier_name"])}</div>
      <div class="sub">{addr_block(f["supplier_address"])}</div>
      <div class="sub">VAT {e(f["supplier_vat_number"])}</div></div></div>
  <div style="text-align:right">
    <div class="doctitle">Invoice / Rechnung / Factuur</div>
    <div class="sub">No. {e(f["invoice_number"])}</div>
    <div class="sub">{label(rec, "date", "Invoice date")} {disp_date(f["invoice_date"], "EU")}</div>
    <div class="sub">Supply date {disp_date(f["supply_date"], "EU")}</div>
    {'<div class="sub">Page 2 of 2</div>' if part == 2 else ''}
  </div>
</div>"""
    parties = f"""
<div class="two">
  <div class="box"><div class="k">{label(rec, "buyer", "Customer")}</div>
    <div class="v">{e(f["customer_name"])}</div>
    <div class="sub">{addr_block(f["customer_address"])}</div>
    <div class="sub">VAT {e(f["customer_vat_number"])}</div></div>
  <div class="box"><div class="k">Payment</div>
    <div class="sub">IBAN {e(f["iban"])}<br>BIC {e(f["bic"])}</div></div>
</div>"""
    table = line_table(rec, lines, cur, show_hsn=False, start=start, end=end)
    if part == 1:
        return header + parties + table + '<div class="note">Continued on page 2.</div>'
    rows = [("Net total", money(f["net_total"], cur)),
            (f'VAT @ {f["vat_rate"]}%', money(f["vat_amount"], cur)),
            (f"Gross total ({cur})", money(f["gross_total"], cur))]
    body = header + ("" if part == 2 else parties) + table + totals_table(rows)
    if f["reverse_charge"] == "true":
        body += ('<div class="note"><b>Reverse charge.</b> VAT is accounted for by the '
                 'recipient under Article 196 of Council Directive 2006/112/EC.</div>')
    body += f'<div class="words">{e(f["amount_in_words"])}</div>'
    body += f"""
<div class="sig"><div class="stampzone"></div>
  <div class="sigline">{label(rec, "signature", "Signature")}</div></div>
<div class="foot">{e(f["supplier_name"])} &middot; {e(f["supplier_country"])} &middot;
  Synthetic document generated for benchmark use.</div>"""
    return body


def tpl_invoice_ph_bir(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    lines = f["line_items"]
    split_at = 6 if part else len(lines)
    start, end = (0, split_at) if part in (None, 1) else (split_at, len(lines))
    header = f"""
<div class="hdr">
  <div class="orgline">{logo_svg(rec, f["seller_name"])}
    <div><div class="org">{e(f["seller_name"])}</div>
      <div class="sub">{addr_block(f["seller_address"])}</div>
      <div class="sub">TIN {e(f["seller_tin"])} &nbsp; VAT registered</div></div></div>
  <div style="text-align:right">
    <div class="doctitle">{label(rec, "tax_invoice", "Sales invoice")}</div>
    <div class="sub">SI No. {e(f["si_number"])}</div>
    <div class="sub">{label(rec, "date", "Date")} {disp_date(f["invoice_date"], "PH")}</div>
    {'<div class="sub">Page 2 of 2</div>' if part == 2 else ''}
  </div>
</div>"""
    parties = f"""
<div class="two">
  <div class="box"><div class="k">{label(rec, "buyer", "Sold to")}</div>
    <div class="v">{e(f["buyer_name"])}</div>
    <div class="sub">{addr_block(f["buyer_address"])}</div>
    <div class="sub">TIN {e(f["buyer_tin"])}</div></div>
  <div class="box"><div class="k">Authority to print</div>
    <div class="sub">Permit no. {e(f["permit_number"])}<br>
      BIR accreditation on file</div></div>
</div>"""
    table = line_table(rec, lines, cur, show_hsn=False, start=start, end=end)
    if part == 1:
        return header + parties + table + '<div class="note">Continued on page 2.</div>'
    rows = [("VATable sales", money(f["vatable_sales"], cur)),
            ("VAT-exempt sales", money(f["vat_exempt_sales"], cur)),
            ("Zero-rated sales", money(f["zero_rated_sales"], cur)),
            (f'VAT @ {f["vat_rate"]}%', money(f["vat_amount"], cur)),
            (f"Total amount due ({cur})", money(f["total_amount_due"], cur))]
    body = header + ("" if part == 2 else parties) + table + totals_table(rows)
    body += f'<div class="words">{e(f["amount_in_words"])}</div>'
    body += f"""
<div class="sig"><div class="stampzone"></div>
  <div class="sigline">{label(rec, "signature", "Authorized representative")}</div></div>
<div class="foot">THIS DOCUMENT IS NOT VALID FOR CLAIMING INPUT TAX &middot;
  Synthetic document generated for benchmark use.</div>"""
    return body


def tpl_id_card_aadhaar(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, "Identity Authority")}
  <div><div class="org">Unique identity enrolment slip</div>
  <div class="sub">Synthetic specimen &mdash; not issued by any authority</div></div></div>
  <div style="text-align:right" class="sub">Enrolment {e(f["enrolment_number"])}</div></div>
<div class="card">
  <div class="cardhead"><div class="org">Identity card</div>
    <div class="sub wide">{e(f["aadhaar_number"][0:4])} {e(f["aadhaar_number"][4:8])} {e(f["aadhaar_number"][8:12])}</div></div>
  <div style="display:flex; gap:5mm">
    <div class="photo"></div>
    <table class="kv">
      <tr><td class="k2">{label(rec, "name", "Name")}</td><td>{e(f["holder_name"])}</td></tr>
      <tr><td class="k2">Father / guardian</td><td>{e(f["father_or_guardian"])}</td></tr>
      <tr><td class="k2">Date of birth</td><td>{disp_date(f["holder_dob"], "IN")}</td></tr>
      <tr><td class="k2">Gender</td><td>{e(f["holder_gender"])}</td></tr>
      <tr><td class="k2">{label(rec, "address", "Address")}</td>
          <td>{addr_block(f["holder_address"])}</td></tr>
    </table>
  </div>
  <div class="note">Identity number {e(f["aadhaar_number"])}. This specimen carries a
    deliberately invalid Verhoeff check digit.</div>
</div>
<div class="stampzone"></div>
<div class="note">Submitted as proof of identity with the attached passport data page and
  utility bill.</div>
<div class="foot">KYC pack {e(rec["doc_id"])} &middot; page 1 of {rec["page_count"]} &middot;
  synthetic</div>"""


def tpl_id_card_pan(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, "Tax Department")}
  <div><div class="org">Permanent account card</div>
  <div class="sub">Synthetic specimen &mdash; not issued by any authority</div></div></div>
  <div style="text-align:right" class="sub">Issued {disp_date(f["pan_issue_date"], "IN")}</div></div>
<div class="card">
  <div class="cardhead"><div class="org">Account number</div>
    <div class="mono wide" style="font-size:13pt">{e(f["pan_number"])}</div></div>
  <div style="display:flex; gap:5mm">
    <div class="photo"></div>
    <table class="kv">
      <tr><td class="k2">{label(rec, "name", "Name")}</td><td>{e(f["holder_name"])}</td></tr>
      <tr><td class="k2">Father's name</td><td>{e(f["father_or_guardian"])}</td></tr>
      <tr><td class="k2">Date of birth</td><td>{disp_date(f["holder_dob"], "IN")}</td></tr>
      <tr><td class="k2">{label(rec, "signature", "Signature")}</td>
          <td><i>{e(f["holder_name"].split()[0])}</i></td></tr>
    </table>
  </div>
  <div class="note">Holder-type character and surname character are deliberately outside the
    published format.</div>
</div>
<div class="stampzone"></div>
<div class="note">{label(rec, "address", "Address")}: {e(f["holder_address"])}</div>
<div class="foot">KYC pack {e(rec["doc_id"])} &middot; page 1 of {rec["page_count"]} &middot;
  synthetic</div>"""


def tpl_passport_page(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, "Passport Office")}
  <div><div class="org">Passport data page (photocopy)</div>
    <div class="sub">Machine-readable travel document, TD3 specimen</div></div></div>
  <div class="sub" style="text-align:right">Type P &middot; Code {e(f["passport_country"])}</div></div>
<div class="card" style="width:150mm">
  <div style="display:flex; gap:5mm">
    <div class="photo" style="width:32mm;height:40mm"></div>
    <table class="kv">
      <tr><td class="k2">Surname</td><td>{e(f["holder_name"].split()[-1].upper())}</td></tr>
      <tr><td class="k2">Given names</td><td>{e(" ".join(f["holder_name"].split()[:-1]).upper())}</td></tr>
      <tr><td class="k2">Passport no.</td><td class="mono">{e(f["passport_number"])}</td></tr>
      <tr><td class="k2">Nationality</td><td>{e(f["passport_country"])}</td></tr>
      <tr><td class="k2">Date of birth</td><td>{disp_date(f["holder_dob"], "IN")}</td></tr>
      <tr><td class="k2">Sex</td><td>{e(f["holder_gender"][0])}</td></tr>
      <tr><td class="k2">Date of issue</td><td>{disp_date(f["passport_issue_date"], "IN")}</td></tr>
      <tr><td class="k2">Date of expiry</td><td>{disp_date(f["passport_expiry_date"], "IN")}</td></tr>
    </table>
  </div>
  <div class="mrz">{e(f["mrz_line1"])}<br>{e(f["mrz_line2"])}</div>
</div>
<div class="note">The document-number and composite check digits in the machine-readable zone
  are deliberately wrong. Date-of-birth and expiry check digits are correct so the zone still
  parses.</div>
<div class="stampzone"></div>
<div class="foot">KYC pack {e(rec["doc_id"])} &middot; passport data page &middot; synthetic</div>"""


def tpl_utility_bill(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    start, end = f["utility_billing_period"].split("/")
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, f["utility_provider"])}
  <div><div class="org">{e(f["utility_provider"])}</div>
    <div class="sub">Electricity bill &mdash; address proof copy</div></div></div>
  <div style="text-align:right" class="sub">Consumer {e(f["utility_consumer_number"])}<br>
    Bill period {disp_date(start, "IN")} to {disp_date(end, "IN")}</div></div>
<div class="two">
  <div class="box"><div class="k">Consumer</div><div class="v">{e(f["holder_name"])}</div>
    <div class="sub">{addr_block(f["holder_address"])}</div></div>
  <div class="box"><div class="k">Reading</div>
    <div class="sub">Units consumed {e(f["units_consumed"])} kWh<br>
      Tariff {money(f["tariff_rate"], cur)} per kWh<br>
      Due date {disp_date(f["utility_due_date"], "IN")}</div></div>
</div>
<table>
  <thead><tr><th>Charge</th><th class="num">Basis</th><th class="num">Amount ({cur})</th></tr></thead>
  <tbody>
    <tr><td>Energy charge</td><td class="num">{e(f["units_consumed"])} kWh x {money(f["tariff_rate"], cur)}</td>
        <td class="num">{money(f["energy_charge"], cur)}</td></tr>
    <tr><td>Fixed charge</td><td class="num">Sanctioned load</td>
        <td class="num">{money(f["fixed_charge"], cur)}</td></tr>
    <tr><td>Electricity duty</td>
        <td class="num">{e(f["electricity_duty_rate"])}% on energy plus fixed</td>
        <td class="num">{money(f["electricity_duty"], cur)}</td></tr>
    <tr><td>Arrears brought forward</td><td class="num">Previous bill</td>
        <td class="num">{money(f["utility_arrears"], cur)}</td></tr>
  </tbody>
</table>
{totals_table([("Total payable (" + cur + ")", money(f["utility_total"], cur))])}
<div class="note">Pay by the due date to avoid a late payment charge. This copy is
  submitted as proof of address.</div>
<div class="stampzone"></div>
<div class="foot">KYC pack {e(rec["doc_id"])} &middot; utility bill &middot; synthetic</div>"""


def tpl_card_photocopy(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    grouped = " ".join(f["card_number"][i:i + 4] for i in range(0, 16, 4))
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, "Bank Card")}
  <div><div class="org">Payment card photocopy</div>
    <div class="sub">Submitted with the KYC pack</div></div></div></div>
<div class="card" style="width:110mm; height:66mm; position:relative">
  <div class="sub">Debit card</div>
  <div class="mono wide" style="font-size:16pt; margin-top:12mm">{e(grouped)}</div>
  <div style="display:flex; justify-content:space-between; margin-top:8mm">
    <div class="sub">Valid thru<br><span class="mono">{e(f["card_expiry"])}</span></div>
    <div class="sub" style="text-align:right">{e(f["card_holder"])}</div>
  </div>
</div>
<div class="note">The card number carries a deliberately invalid Luhn check digit. It is not,
  and cannot be, a live card number.</div>
<div class="stampzone"></div>
<div class="foot">KYC pack {e(rec["doc_id"])} &middot; card copy &middot; synthetic</div>"""


PAGE_KIND_LABELS = {
    "invoice_in_gst": "Tax invoice (GST)",
    "invoice_in_gst_continued": "Tax invoice, continuation sheet",
    "invoice_us": "Commercial invoice",
    "invoice_us_continued": "Commercial invoice, continuation sheet",
    "invoice_eu_vat": "VAT invoice",
    "invoice_eu_vat_continued": "VAT invoice, continuation sheet",
    "invoice_ph_bir": "Sales invoice (BIR)",
    "invoice_ph_bir_continued": "Sales invoice, continuation sheet",
    "id_card_aadhaar": "Identity card copy",
    "id_card_pan": "Permanent account card copy",
    "passport_page": "Passport data page",
    "utility_bill": "Electricity bill, address proof",
    "card_photocopy": "Payment card copy",
    "claim_motor": "Motor claim form",
    "claim_health": "Health claim form",
    "claim_property": "Property claim form",
    "claim_estimate": "Assessment and settlement sheet",
    "purchase_order": "Purchase order",
}

CLAIM_TITLES = {"claim_motor": "Motor own-damage claim form",
                "claim_health": "Health reimbursement claim form",
                "claim_property": "Property damage claim form"}


def tpl_claim(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    sub = rec["doc_subtype"]
    rows = [("Policy number", e(f["policy_number"])),
            ("Claim number", e(f["claim_number"])),
            ("Claim date", disp_date(f["claim_date"], "IN")),
            ("Insured name", e(f["insured_name"])),
            ("Contact", e(f["insured_phone"])),
            ("Address", addr_block(f["insured_address"]))]
    if sub == "claim_motor":
        rows += [("Date of loss", disp_date(f["incident_date"], "IN")),
                 ("Place of loss", e(f["incident_location"])),
                 ("Registration", e(f["vehicle_registration"])),
                 ("Make and model", e(f["vehicle_make_model"])),
                 ("Chassis / VIN", f'<span class="mono">{e(f["vehicle_vin"])}</span>'),
                 ("Repairer", e(f["garage_name"])),
                 ("Surveyor", e(f["surveyor_name"])),
                 ("How the loss occurred", e(f["incident_description"]))]
    elif sub == "claim_health":
        rows += [("Hospital", e(f["hospital_name"])),
                 ("Admission", disp_date(f["admission_date"], "IN")),
                 ("Discharge", disp_date(f["discharge_date"], "IN")),
                 ("Diagnosis", e(f["diagnosis"])),
                 ("Treating doctor", e(f["treating_doctor"])),
                 ("Sum insured", money(f["sum_insured"], "INR"))]
    else:
        rows += [("Peril", e(f["peril"])),
                 ("Date of loss", disp_date(f["incident_date"], "IN")),
                 ("Risk location", addr_block(f["risk_location"])),
                 ("Surveyor", e(f["surveyor_name"])),
                 ("Sum insured", money(f["sum_insured"], "INR")),
                 ("How the loss occurred", e(f["incident_description"]))]
    body_rows = "".join(
        f'<tr><td style="width:38%">{k}</td><td>{v}</td></tr>' for k, v in rows)
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, f["insurer_name"])}
  <div><div class="org">{e(f["insurer_name"])}</div>
    <div class="sub">Claims department</div></div></div>
  <div style="text-align:right"><div class="doctitle">{e(CLAIM_TITLES[sub])}</div>
    <div class="sub">Form CL-{rec["doc_id"][-4:]}</div></div></div>
<table>{body_rows}</table>
<div class="note">I declare that the particulars given above are true to the best of my
  knowledge and that no material fact has been withheld.</div>
<div class="sig">Claimant<div class="stampzone"></div>
  <div class="sigline">{label(rec, "signature", "Signature and date")}</div></div>
<div class="foot">{e(f["claim_number"])} &middot; page 1 of {rec["page_count"]} &middot;
  synthetic document generated for benchmark use</div>"""


def tpl_claim_estimate(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    lines = f["estimate_lines"]
    head = ("<tr><th>#</th><th>Item</th><th>UOM</th><th class='num'>Qty</th>"
            "<th class='num'>Rate</th><th class='num'>Amount</th></tr>")
    body = "".join(
        f'<tr><td class="num">{ln["sl"]}</td><td>{e(ln["description"])}</td>'
        f'<td>{e(ln["uom"])}</td><td class="num">{e(ln["quantity"])}</td>'
        f'<td class="num">{money(ln["unit_price"], cur)}</td>'
        f'<td class="num">{money(ln["amount"], cur)}</td></tr>' for ln in lines)
    rows = [("Assessed total", money(f["assessed_total"], cur))]
    if rec["doc_subtype"] == "claim_health":
        rows.append((f'Co-pay @ {f["co_pay_rate"]}%', "-" + money(f["co_pay_amount"], cur)))
    else:
        rows.append(("Salvage value", "-" + money(f["salvage_value"], cur)))
    rows.append(("Policy excess", "-" + money(f["policy_excess"], cur)))
    rows.append((f"Net payable ({cur})", money(f["net_payable"], cur)))
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, f["insurer_name"])}
  <div><div class="org">{e(f["insurer_name"])}</div>
    <div class="sub">Assessment and settlement sheet</div></div></div>
  <div style="text-align:right" class="sub">Claim {e(f["claim_number"])}<br>
    Policy {e(f["policy_number"])}</div></div>
<table><thead>{head}</thead><tbody>{body}</tbody></table>
{totals_table(rows)}
<div class="two" style="margin-top:5mm">
  <div class="box small"><div class="k">Settlement account</div>
    A/c {e(f["settlement_account"])}<br>IFSC {e(f["settlement_ifsc"])}</div>
  <div class="box small"><div class="k">Assessment note</div>
    Amounts assessed on the documents produced. Excess and, where applicable, salvage or
    co-pay are deducted before payment.</div>
</div>
<div class="sig">For {e(f["insurer_name"])}<div class="stampzone"></div>
  <div class="sigline">Assessing officer</div></div>
<div class="foot">{e(f["claim_number"])} &middot; assessment sheet &middot; synthetic</div>"""


def tpl_purchase_order(rec: dict, part: int | None) -> str:
    f = rec["fields"]
    cur = f["currency"]
    loc = rec["locale"]
    table = line_table(rec, f["line_items"], cur, show_hsn=True, hsn_label="Material")
    rows = [("Subtotal", money(f["subtotal"], cur)),
            (f'Tax @ {f["tax_rate"]}%', money(f["tax_amount"], cur)),
            ("Freight", money(f["freight"], cur)),
            (f"Order total ({cur})", money(f["po_total"], cur))]
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, f["buyer_org"])}
  <div><div class="org">{e(f["buyer_org"])}</div>
    <div class="sub">{addr_block(f["buyer_address"])}</div></div></div>
  <div style="text-align:right"><div class="doctitle">Purchase order</div>
    <div class="sub">PO {e(f["po_number"])}</div>
    <div class="sub">{label(rec, "date", "Date")} {disp_date(f["po_date"], loc)}</div>
    <div class="sub">Required by {disp_date(f["required_by"], loc)}</div></div></div>
<div class="two">
  <div class="box"><div class="k">{label(rec, "supplier", "Vendor")}</div>
    <div class="v">{e(f["vendor_name"])}</div>
    <div class="sub">{addr_block(f["vendor_address"])}</div>
    <div class="sub">Vendor code {e(f["vendor_code"])} &middot; Tax ID {e(f["vendor_tax_id"])}</div></div>
  <div class="box"><div class="k">Ship to</div>
    <div class="sub">{addr_block(f["ship_to_address"])}</div>
    <div class="sub">Incoterm {e(f["incoterm"])} &middot; {e(f["payment_terms"])}</div>
    <div class="sub">Cost centre {e(f["cost_centre"])}</div></div>
</div>
{table}
{totals_table(rows)}
<div class="words">{e(f["amount_in_words"])}</div>
<div class="box small" style="margin-top:4mm">Deliveries must quote this order number.
  Goods are subject to inspection on receipt. Invoices without the order number will be
  returned unpaid.</div>
<div class="sig">{e(f["approver_name"])}, {e(f["approver_title"])}
  <div class="stampzone"></div>
  <div class="sigline">{label(rec, "signature", "Authorised signatory")}</div></div>
<div class="foot">PO {e(f["po_number"])} &middot; {e(f["buyer_org"])} &middot; synthetic</div>"""


def tpl_cover_note(rec: dict, part: int | None) -> str:
    """Tier-5 bundle cover sheet, written in the bundle's second language."""
    bl = rec["bilingual_labels"]
    lab = bl["labels"]
    cls = "indic" if bl["iso"] in ("hi", "gu") else "latin2"
    items = []
    for i, p in enumerate(rec["logical_pages"], start=1):
        name = PAGE_KIND_LABELS.get(p["kind"], p["kind"].replace("_", " ").capitalize())
        items.append(f'<tr><td class="num">{i}</td><td>{e(name)}</td></tr>')
    return f"""
<div class="hdr"><div class="orgline">{logo_svg(rec, rec["doc_id"])}
  <div><div class="org {cls}">{e(lab["enclosures"])}</div>
    <div class="sub">Enclosure list / cover sheet</div></div></div>
  <div style="text-align:right" class="sub">{e(rec["doc_id"])}<br>
    <span class="{cls}">{e(lab["page"])} 1</span></div></div>
<table><thead><tr><th>#</th><th><span class="{cls}">{e(lab["description"])}</span> /
  Description</th></tr></thead><tbody>{"".join(items)}</tbody></table>
<div class="note {cls}" style="font-size:11pt; margin-top:6mm">{e(lab["note"])}</div>
<div class="note">This cover sheet is attached to the scanned bundle. The bundle also
  contains a duplicated page and pages that are rotated relative to the first page.</div>
<div class="sig"><div class="stampzone"></div>
  <div class="sigline"><span class="{cls}">{e(lab["signature"])}</span></div></div>
<div class="foot">{e(rec["doc_id"])} &middot; bundle cover sheet &middot; synthetic</div>"""


TEMPLATES = {
    "invoice_in_gst": tpl_invoice_in_gst,
    "invoice_in_gst_continued": tpl_invoice_in_gst,
    "invoice_us": tpl_invoice_us,
    "invoice_us_continued": tpl_invoice_us,
    "invoice_eu_vat": tpl_invoice_eu_vat,
    "invoice_eu_vat_continued": tpl_invoice_eu_vat,
    "invoice_ph_bir": tpl_invoice_ph_bir,
    "invoice_ph_bir_continued": tpl_invoice_ph_bir,
    "id_card_aadhaar": tpl_id_card_aadhaar,
    "id_card_pan": tpl_id_card_pan,
    "passport_page": tpl_passport_page,
    "utility_bill": tpl_utility_bill,
    "card_photocopy": tpl_card_photocopy,
    "claim_motor": tpl_claim,
    "claim_health": tpl_claim,
    "claim_property": tpl_claim,
    "claim_estimate": tpl_claim_estimate,
    "purchase_order": tpl_purchase_order,
    "cover_note": tpl_cover_note,
}


def document_html(rec: dict) -> str:
    pages = []
    for spec in rec["logical_pages"]:
        kind = spec["kind"]
        tpl = TEMPLATES[kind]
        pages.append(f'<div class="page">{tpl(rec, spec.get("part"))}</div>')
    if rec["tier"] == 5:
        pages.append(f'<div class="page">{tpl_cover_note(rec, None)}</div>')
    css = stylesheet(rec["layout_variant"])
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<title>{e(rec["doc_id"])}</title><style>{css}</style></head>'
            f'<body>{"".join(pages)}</body></html>')


def render_page_count(rec: dict) -> int:
    """Number of distinct source pages Chromium renders for this document."""
    return len(rec["logical_pages"]) + (1 if rec["tier"] == 5 else 0)


# --------------------------------------------------------------------------- #
# Font check                                                                  #
# --------------------------------------------------------------------------- #

def check_fonts() -> dict:
    report = {}
    for iso, family in REQUIRED_FONT_LANGS.items():
        try:
            out = subprocess.run(["fc-match", family], capture_output=True, text=True, timeout=20)
            matched = out.stdout.strip()
        except Exception as exc:  # pragma: no cover - environment dependent
            matched = f"fc-match failed: {exc}"
        report[iso] = {"requested": family, "fc_match": matched,
                       "ok": family.split()[-1].lower() in matched.lower()}
    return report


# --------------------------------------------------------------------------- #
# Selection                                                                   #
# --------------------------------------------------------------------------- #

def select_documents(records: list[dict], select: str, stratified: int,
                     only: list[str] | None) -> list[dict]:
    if only:
        wanted = set(only)
        return [r for r in records if r["doc_id"] in wanted]
    if select == "all":
        chosen = list(records)
    elif select == "splits":
        chosen = [r for r in records if r["split"] != "open"]
    elif select in ("public_sample", "private_holdout"):
        chosen = [r for r in records if r["split"] == select]
    else:
        raise SystemExit(f"unknown --select {select!r}")
    if stratified > 0 and select != "all":
        picked = {r["doc_id"] for r in chosen}
        pool = [r for r in records if r["doc_id"] not in picked]
        # proportional across (subtype, tier), deterministic by sorted doc_id
        buckets: dict[tuple[str, int], list[dict]] = {}
        for r in pool:
            buckets.setdefault((r["doc_subtype"], r["tier"]), []).append(r)
        total_pool = len(pool)
        extra: list[dict] = []
        for key in sorted(buckets):
            bucket = sorted(buckets[key], key=lambda r: r["doc_id"])
            take = round(stratified * len(bucket) / total_pool)
            extra.extend(bucket[:max(take, 1 if stratified >= len(buckets) else 0)])
        extra.sort(key=lambda r: r["doc_id"])
        chosen = chosen + extra[:stratified]
    return sorted(chosen, key=lambda r: r["doc_id"])


# --------------------------------------------------------------------------- #
# Render loop                                                                 #
# --------------------------------------------------------------------------- #

def render(records: list[dict], out_dir: Path, skip_existing: bool, progress_every: int) -> dict:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    done, skipped = 0, 0
    started = time.time()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--font-render-hinting=none",
                                           "--disable-lcd-text",
                                           "--force-color-profile=srgb"])
        context = browser.new_context(viewport={"width": int(A4_W_CSS), "height": int(A4_H_CSS)},
                                      device_scale_factor=DEVICE_SCALE)
        page = context.new_page()
        for i, rec in enumerate(records, start=1):
            target = out_dir / rec["doc_id"]
            n_pages = render_page_count(rec)
            expected = [target / "clean.pdf"] + [
                target / f"page-{k + 1:02d}.png" for k in range(n_pages)]
            if skip_existing and all(p.exists() for p in expected):
                skipped += 1
                continue
            target.mkdir(parents=True, exist_ok=True)
            page.set_content(document_html(rec), wait_until="load")
            page.pdf(path=str(target / "clean.pdf"), prefer_css_page_size=True,
                     print_background=True)
            nodes = page.locator(".page")
            count = nodes.count()
            if count != n_pages:
                raise RuntimeError(f"{rec['doc_id']}: {count} rendered pages, expected {n_pages}")
            for k in range(count):
                nodes.nth(k).screenshot(path=str(target / f"page-{k + 1:02d}.png"))
            done += 1
            if progress_every and i % progress_every == 0:
                rate = i / max(time.time() - started, 1e-6)
                print(f"  {i}/{len(records)} documents  ({rate:.1f}/s)", flush=True)
        context.close()
        browser.close()
    return {"rendered": done, "skipped": skipped,
            "seconds": round(time.time() - started, 1)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render Messy Scan documents to PDF and PNG.")
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN_PATH)
    ap.add_argument("--out", type=Path, default=DEFAULT_RENDER_DIR)
    ap.add_argument("--select", default="all",
                    choices=["all", "splits", "public_sample", "private_holdout"])
    ap.add_argument("--stratified", type=int, default=0,
                    help="add this many extra documents, spread across every subtype and tier")
    ap.add_argument("--only", nargs="*", default=None, help="explicit document ids")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--check-fonts", action="store_true")
    ap.add_argument("--dump-html", type=Path, default=None,
                    help="write the HTML of the selected documents here and stop")
    args = ap.parse_args(argv)

    report = check_fonts()
    for iso, info in report.items():
        state = "ok" if info["ok"] else "MISSING"
        print(f"font {iso}: {info['requested']} -> {info['fc_match']} [{state}]")
    if args.check_fonts:
        return 0 if all(i["ok"] for i in report.values()) else 1
    if not all(i["ok"] for i in report.values()):
        print("warning: a required Indic font is missing; tier-5 pages in that language "
              "will render as tofu. Install fonts-noto-core.", file=sys.stderr)

    records = load_documents(args.plan)
    chosen = select_documents(records, args.select, args.stratified, args.only)
    print(f"selected {len(chosen)} of {len(records)} documents")

    if args.dump_html:
        args.dump_html.mkdir(parents=True, exist_ok=True)
        for rec in chosen:
            (args.dump_html / f'{rec["doc_id"]}.html').write_text(document_html(rec),
                                                                  encoding="utf-8")
        print(f"html written to {args.dump_html}")
        return 0

    stats = render(chosen, args.out, args.skip_existing, args.progress_every)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
