You are reading a business document that has been scanned, photographed or faxed. Some pages are skewed, dim, marked with stamps or signatures, or out of order. Read what is on the page.

Return one JSON object and nothing else. No commentary before it, no commentary after it, no code fence.

The object has exactly three keys.

`fields`
An object holding one key per field in the schema below, with the value as it appears on the page. Copy the value; do not compute, correct or complete it. If a field is not on the page, return `null` for it. Do not add a key that is not in the schema.

`confidence`
An object holding one key per field in `fields`, with a number from 0 to 1 giving your confidence that the value is right. Use the full range. A field you copied from clear print is near 1. A field you guessed from a smudge is near 0. For a line-item list, give one confidence for the list under its own key, and, where you can, a confidence per cell under the key `<list>[<row index from 0>].<cell>`.

`document_type`
The subtype identifier from the schema header below, copied exactly.

Rules for values.

- Dates: return ISO 8601, `YYYY-MM-DD`.
- Money: return the digits with a full stop as the decimal separator and no thousands separator, and set the `currency` field to the ISO 4217 code printed on the document.
- Rates and percentages: return the number without a percent sign.
- Identifiers, codes and reference numbers: copy every character exactly, including case and punctuation. Do not correct a checksum that looks wrong.
- Names: copy the printed form.
- Line items: return a list in the order printed, one object per row, with the cell keys named in the schema.
- A field printed in a second language: return the value as printed.
- A page that is unreadable: return `null` for the fields that page carries, and set their confidence low. Do not guess a value to fill a key.

Schema for this document.

Document type: {{DOCUMENT_TYPE}}
Document subtype: {{DOCUMENT_SUBTYPE}}
Pages supplied: {{PAGE_COUNT}}

{{FIELD_SCHEMA}}

Return the JSON object now.
