# Datasheet — Messy Scan dataset v1.0.0

Follows the structure of Gebru et al., "Datasheets for Datasets" (2018).
Dataset version 1.0.0 · Schema version 1.0 · Seed 20260902 · Written 2026-09-02.

**This data is synthetic.** Every document in it was written by `generate.py` and
drawn by `render.py`. No document was scanned from a real one. No page contains a
real company, a real address or a real person. Every identifier is deliberately
invalid. What that means for a reader of a result is set out in "Known biases and
limitations" at the end of this file, and it is not a footnote: a score on this
dataset tells you how a system behaves on documents that look like production
documents, not how it behaves on your production documents.

---

## Motivation

**Why was the dataset created?**
Vendor decks quote document-extraction accuracy on clean, single-page, single-format
inputs. Production traffic in a BPO is skewed the other way: rescans of rescans,
phone photographs, faxes with stamps over the text, mixed-language bundles arriving
on a messaging app. The gap between the two numbers is the thing a partner is buying
against. This dataset is one half of the measurement; `harness/` is the other.

The Messy Scan Benchmark measures field-level accuracy, document-level
straight-through-processing rate, exception rate, confidence calibration, cost per
document and latency, per difficulty tier and per language. The definitions live in
`10-benchmarks/charter/methodology.md` and govern this dataset.

**Who created it and who funded it?**
Entailment Labs, for its own benchmark programme. No external funding.

**Any other comments?**
The dataset is built to be regenerated, not downloaded. Four scripts and a seed
produce it. That is what makes a result reproducible and what lets a partner run the
same benchmark on their own documents with `--dataset ./their-folder`.

---

## Composition

**What do the instances represent?**
Business documents of four kinds, each with the fields an extraction system is asked
to read.

| Type | Subtype | Documents | What it is |
|---|---|---|---|
| Invoice | `invoice_in_gst` | 100 | Indian tax invoice with GSTIN, HSN/SAC codes and a CGST/SGST or IGST split |
| Invoice | `invoice_us` | 100 | US commercial invoice with EIN, sales tax and ACH remittance details |
| Invoice | `invoice_eu_vat` | 100 | EU VAT invoice (DE, FR, NL, IT), including reverse-charge cases, IBAN and BIC |
| Invoice | `invoice_ph_bir` | 100 | Philippine sales invoice with TIN, VATable / exempt / zero-rated split |
| KYC pack | `kyc_aadhaar` | 130 | Aadhaar-style identity card, passport data page with an ICAO 9303 machine-readable zone, electricity bill as address proof |
| KYC pack | `kyc_pan` | 120 | PAN-style card, passport data page, payment-card photocopy, electricity bill |
| Insurance claim | `claim_motor` | 80 | Motor own-damage claim form plus an itemised repair assessment |
| Insurance claim | `claim_health` | 70 | Health reimbursement claim form plus an itemised hospital bill |
| Insurance claim | `claim_property` | 50 | Property damage claim form plus an itemised loss assessment |
| Purchase order | `po_in` `po_us` `po_eu` `po_ph` | 50 / 40 / 35 / 25 | Purchase orders in four jurisdictions |
| **Total** | | **1,000** | |

**How many instances are there in total?**
1,000 documents. 2,063 pages are rendered; the final artefacts hold 2,211 pages,
because tier 5 adds a cover sheet and a duplicated page to each bundle. Both figures
are counted from `ground-truth.jsonl`, not estimated.

**Difficulty tiers.**

| Tier | Name | Share of the plan | Documents | What is done to the page |
|---|---|---|---|---|
| 1 | Clean digital | 15% | 152 | Nothing. Vector PDF and lossless PNG straight from the renderer |
| 2 | Flatbed scan | 25% | 252 | Greyscale, paper tone, small skew, lid shadow, blur, noise, dust, JPEG |
| 3 | Phone photo | 25% | 248 | Perspective warp, rotation, desk background, shadow gradient, glare, white-balance shift, blur, sensor noise, JPEG |
| 4 | Fax quality with marks | 20% | 200 | Stamps over the text, drawn signatures, margin annotations, staple holes and tear, skew, low fax resolution, noise, one-bit dither, speckle, scan-line dropout |
| 5 | Mixed bundle | 15% | 148 | Multi-page bundle with a second-language cover sheet, a duplicated page, rotated and reordered pages, mixed base effects, two resamples and two JPEG passes |

The tier counts are not exactly 150/250/250/200/150 because the shares are applied
inside each subtype with largest-remainder rounding, so that every subtype is
represented in every tier. `validate.py` recomputes the plan the same way and fails
if the built distribution differs.

**Languages.**

| Languages on the page | Documents |
|---|---|
| English only | 852 |
| English and Hindi | 66 |
| English and Gujarati | 43 |
| English and Tagalog | 39 |

Two languages on one page is a tier-5 property. The second language is chosen to
suit the jurisdiction: Indian documents get Hindi or Gujarati, Philippine documents
get Tagalog, and US and EU documents can get either Hindi or Tagalog, which is the
case of a bundle assembled by an offshore back office.

**Pages per document.**

| Pages | Documents |
|---|---|
| 1 | 386 |
| 2 | 253 |
| 3 | 180 |
| 4 | 144 |
| 5 | 19 |
| 6 | 18 |

**Is there a label or target associated with each instance?**
Yes. Every document has known-answer ground truth for every field, emitted at the
same time as the document. `ground-truth.jsonl` carries one JSON object per
document with: document id, type and subtype, tier, languages, page count, split,
the field schema for its type, every ground-truth field value, the identifier
provenance (which check each identifier fails and how), the full degradation
parameter set, and the SHA-256 of every rendered file.

**Is any information missing?**
The `render` object is `null` for any document that has not been rendered in the
current build. `validate.py` reports the count and prints the command that finishes
the build. Nothing else is missing.

**Are relationships between instances made explicit?**
Documents are independent. Each document's random stream is derived from
`SHA-256(seed:doc_id)`, so adding or removing documents does not change any other
document.

**Are there recommended data splits?**

| Split | Documents | Purpose |
|---|---|---|
| `public_sample` | 50 | Published. Anyone can inspect the format and run the harness end to end |
| `private_holdout` | 200 | Never published. Used to detect overfitting to the public sample |
| `open` | 750 | Regenerable from the seed; not distributed as files |

Both splits are stratified across subtype and tier, so the sample is representative
rather than convenient. See `MANIFEST.md`.

**Are there errors, sources of noise, or redundancies?**
The noise is deliberate and parameterised; see "Degradation parameters" below. Tier 5
bundles contain a duplicated page on purpose. `validate.py` checks that every total
reconciles and every field is present, so ground-truth error is not a known source
of noise.

**Is the dataset self-contained?**
Yes. It depends on no external resource at run time. Regenerating it needs Python
3.11, Playwright with Chromium, Pillow, NumPy, OpenCV, and the fonts listed under
"Collection and generation process".

**Does it contain confidential, offensive or personal data?**
No. It contains no partner data, no real personal data, and no data derived from a
real document. Names, organisations, addresses and identifiers are constructed. See
"Identifiers" and "Names, organisations and addresses".

---

## Collection and generation process

**How was the data acquired?**
It was not acquired. It was generated. Four scripts, one seed:

1. `generate.py` builds the plan and the ground truth: composition, tier assignment,
   split assignment, field values, identifiers, page plan and every degradation
   parameter. Output: `build/documents.jsonl`. It is five files — the plan and the
   assembly loop here, with `identifiers.py`, `content.py`, `schemas.py` and
   `builders.py` beside it — which is a matter of file size only; the seed produces a
   byte-identical plan either way.
2. `render.py` turns each document into HTML and renders it with Chromium through
   Playwright: one vector PDF and one lossless PNG per page, A4 at 200 dpi
   (1,654 x 2,339 px).
3. `degrade.py` applies the planned tier degradation, writes the final artefacts,
   assembles `ground-truth.jsonl` with the file hashes, and materialises the splits.
4. `validate.py` checks the result.

**Is the process deterministic?**
Yes. `generate.py --seed N` produces a byte-identical `build/documents.jsonl` for a
given N. Degradation draws from a per-page stream seeded with
`SHA-256("degrade:doc_id:page")`. Chromium's raster output is the one component we do
not control: a different Chromium build can shift antialiasing by a pixel, which
changes the PNG bytes and therefore the recorded hashes. The hashes are a check that
the file you hold is the file the ground truth describes; they are not a claim that
two independent builds produce identical bytes.

**Software and fonts.**
Python 3.11, Playwright 1.56 with the bundled Chromium, Pillow, NumPy, OpenCV.
Typefaces: IBM Plex Sans and IBM Plex Sans Condensed, DejaVu Sans, DejaVu Serif,
DejaVu Sans Condensed, Carlito, Caladea, DejaVu Sans Mono. Hindi uses Noto Sans
Devanagari and Gujarati uses Noto Sans Gujarati, both from the `fonts-noto-core`
package. Tagalog is written in Latin script and needs no extra font.
`render.py --check-fonts` fails if a required Indic face is absent, so a build cannot
silently produce tofu.

**Line items and arithmetic.**
Line descriptions come from a fixed catalogue of twenty industrial goods and services
with HSN or SAC codes and price bands. All money is held in integer minor units
(paise, cents, centavos). The rules, which `validate.py` re-derives independently:

- line amount = quantity x unit price, rounded half up to the minor unit;
- subtotal, taxable value, net total or assessed total = the sum of line amounts;
- tax = the stated rate applied to the stated base, rounded half up
  (`tax = (base_minor x rate_bp + 5000) // 10000`, `rate_bp = rate x 100`);
- total = the sum of its stated components;
- Indian invoices round the total to the nearest rupee and carry the difference in a
  `round_off` field of at most 0.50.

**Names, organisations and addresses.**
Organisation names are assembled from two invented syllable inventories plus a
sector word and a jurisdiction-appropriate legal suffix. Given names and family
names are assembled from per-locale syllable inventories. Street and locality names
are invented. City, state and country names are real, because a document with an
impossible city is not a realistic document, and postal codes are plausible for the
state shown. No name, organisation or address was drawn from a register, a directory
or any real document. Any resemblance to a real organisation or person is
coincidental and unintended.

**Identifiers: every one is deliberately invalid.**
This is the property the dataset is most careful about. An extractor must see
something that looks like the real thing; a checksum validator must reject it. The
table names the check and how it is broken. `validate.py` enforces every row and
fails the build if any identifier passes its check.

| Identifier | Check | Class | How it is made to fail |
|---|---|---|---|
| Aadhaar-style number | Verhoeff (dihedral D5) over 12 digits | Real checksum | The correct check digit is computed for the 11-digit payload, then a different digit is emitted. The digit is also chosen so the 12-digit run is not Luhn-valid. First digit stays in 2-9, the published structural rule |
| PAN-style number | Published PAN format | Published structural rule | The fourth character is the holder-type code and must be one of A B C F G H J L P T (some published lists add E and K). We emit a code outside all twelve. The fifth character must be the holder's surname initial; we emit a different letter. The tenth-character algorithm has never been published by the Income Tax Department, so no validator can honestly assert it is wrong, and this dataset does not assert it |
| GSTIN | GSTN modulo-36 check character | Real checksum | The correct character is computed under both factor-parity conventions found in published implementations and a character different from both is emitted. The state code stays a real one; the embedded PAN is itself format-invalid |
| IFSC | RBI published format | Published structural rule | The fifth character must be `0`; a non-zero digit is emitted |
| Payment card number | Luhn, ISO/IEC 7812-1 | Real checksum | The correct check digit is computed and a different one emitted |
| IBAN | ISO 13616 / ISO 7064 MOD 97-10 | Real checksum | The correct check digits are computed and a different pair emitted; the result is confirmed not congruent to 1 mod 97 |
| EU VAT (DE) | ISO 7064 MOD 11,10 | Real checksum | Correct check digit computed, different one emitted |
| EU VAT (FR) | SIREN Luhn plus key = (12 + 3 x (SIREN mod 97)) mod 97 | Real checksum | Both are broken: the SIREN is made Luhn-invalid and the key is replaced |
| EU VAT (NL) | Weighted modulo-11 over the nine-digit body | Real checksum | Correct check digit computed, different one emitted |
| EU VAT (IT) | Luhn-style modulo-10 over eleven digits | Real checksum | Correct check digit computed, different one emitted |
| US EIN | IRS published campus-prefix list | Published structural rule | The prefix is drawn from the complement: 07, 08, 09, 17, 18, 19, 28, 29, 49, 69, 70, 78, 79, 89 |
| ABA routing number | Published 3-7-1 modulo-10 | Real checksum | Correct ninth digit computed, different one emitted |
| Passport number and MRZ | ICAO 9303 TD3 7-3-1 modulo-10 | Real checksum | The document-number and composite check digits are wrong. The date-of-birth, expiry and optional-data digits are left correct so the zone still parses and a reader fails it on the two broken digits |
| VIN | Position-9 modulo-11 transliteration check | Real checksum | Correct character computed, different one emitted |
| Philippine TIN | None published | **No public check available** | BIR does not publish a check-digit algorithm. We say so rather than claim a guarantee we cannot make. The ninth digit additionally fails an ISO 7064 MOD 11-2 surrogate defined by this dataset; that surrogate is a dataset convention, not a BIR rule |
| Bank account numbers, permit numbers, consumer numbers, policy, claim, invoice and order numbers | None published | **No public check available** | No checksum exists to break. Numbers of eleven digits or more are constructed so the digit run is neither Luhn-valid nor Verhoeff-valid, so that nobody scanning the files finds something that looks like a live card |

Beyond the per-field checks, `validate.py` sweeps every string in the ground truth
and enforces two rules:

- **Rule A.** Every maximal digit run of 12 to 19 digits fails Luhn. A run of exactly
  12 digits also fails Verhoeff.
- **Rule B.** Inside a maximal digit run of 20 or more digits — an IBAN body, for
  instance — no 16-digit window is Luhn-valid.

Runs of 20 or more digits are not card-shaped under ISO/IEC 7812, and the eighty-odd
overlapping windows inside one cannot all be constrained at once, so only the
16-digit windows are checked. That is the exact limit of the guarantee, stated here
rather than left implied.

**Was anyone paid, and were ethics processes applied?**
No people were involved in collection, because nothing was collected. No ethical
review was sought and none applies: there is no human subject, no consent question
and no personal data.

---

## Degradation parameters and their ranges

Every parameter below is drawn once per document from the seeded stream, recorded in
that document's `degradation` object in `ground-truth.jsonl`, and applied by
`degrade.py`. A reader can see exactly what was done to any page.

### Tier 2, flatbed scan

| Parameter | Range |
|---|---|
| `skew_deg` | -1.6 to 1.6 degrees |
| `paper_grey` | 236 to 250 (the white point a flatbed actually returns) |
| `gaussian_noise_sigma` | 2.5 to 6.0 |
| `blur_sigma` | 0.30 to 0.75 px |
| `contrast` | 0.90 to 1.08 |
| `brightness` | 0.94 to 1.06 |
| `dust_specks` | 12 to 70 |
| `lid_shadow_px` | 0 to 16 (scaled by six into an edge ramp) |
| `jpeg_quality` | 78 to 93 |

### Tier 3, phone photo

| Parameter | Range |
|---|---|
| `perspective_offsets_frac` | eight corner offsets, 0.004 to 0.048 of the page dimension |
| `rotation_deg` | -3.5 to 3.5 degrees |
| `shadow.axis` | `x`, `y` or `diag` |
| `shadow.strength` | 0.18 to 0.46 |
| `shadow.centre` | 0.15 to 0.85 |
| `glare.cx`, `glare.cy` | 0.15 to 0.85 and 0.12 to 0.80 |
| `glare.radius_frac` | 0.08 to 0.24 of the long edge |
| `glare.intensity` | 0.25 to 0.72 |
| `blur_sigma` | 0.6 to 1.9 px |
| `gaussian_noise_sigma` | 3.0 to 9.0 |
| `white_balance` | r 0.96-1.07, g 0.97-1.03, b 0.93-1.05 |
| `desk_tone` | one of five desk colours |
| `margin_frac` | 0.03 to 0.11 (the page does not fill the frame) |
| `jpeg_quality` | 58 to 86 |

### Tier 4, fax quality with marks

| Parameter | Range |
|---|---|
| `skew_deg` | -2.6 to 2.6 degrees |
| `fax_dpi` | 100, 120 or 150, then resampled back to 200 |
| `pre_noise_sigma` | 8.0 to 18.0, applied before the one-bit conversion |
| `dither` | `floyd_steinberg` or `threshold` |
| `threshold` | 108 to 162 |
| `speckle_density` | 0.002 to 0.013 of pixels flipped |
| `line_dropout_rows` | 0 to 6 fax scan-line dropouts |
| `stamps` | 1 to 3. Text from seven office stamps; centre 0.20-0.82 by 0.18-0.86; rotation -28 to 28 degrees; scale 0.72-1.35; shape rect, ellipse or double rect; three inks; alpha 0.42-0.80 |
| `signatures` | 1 to 2. Centre 0.52-0.90 by 0.62-0.94; scale 0.6-1.3; rotation -9 to 9 degrees |
| `handwriting` | 1 to 3 margin notes from twelve snippets; position anywhere on the page; rotation -12 to 12 degrees; size 0.016-0.030 of page height |
| `staple` | corner top-left or top-right; 1 to 2 holes; a torn corner in 45% of cases; offset 0.018-0.045 |

Stamps, signatures and margin notes are drawn over the text on purpose, including
over fields an extractor has to read. Signatures are parametric strokes: a
low-frequency loop plus two harmonics, with the pen speeding up and the amplitude
decaying along the stroke. Margin notes use an oblique typeface with per-character
jitter and rotation. Both are simulations of handwriting. Neither is a sample of
anyone's hand, and neither should be used to train or evaluate handwriting
recognition.

### Tier 5, mixed bundle

| Parameter | Range |
|---|---|
| `second_language` | `hi`, `gu` or `tl`, chosen to suit the jurisdiction |
| `bundle_plan` | the document's own pages, plus a cover sheet in the second language, plus one duplicated page; two pages are swapped in 45% of bundles |
| `per_page.rotation_deg` | 0, 90, 180 or 270, weighted 6:6:6:3:2:2 across the six draws |
| `per_page.base_effect` | `flatbed`, `phone` or `fax`, drawn per page |
| `per_page.extra_blur_sigma` | 0.2 to 1.4 px |
| `downscale_frac` | 0.34 to 0.62, the sending app's shrink |
| `final_long_edge_px` | 1280, 1440 or 1600 |
| `jpeg_quality_pass1` | 30 to 52 |
| `jpeg_quality_pass2` | 22 to 42 |

The two resamples and two JPEG passes are the signature of an image that has been
photographed, sent through a messaging app and forwarded again.

---

## Preprocessing, cleaning and labelling

**Does the rendered page agree with the ground truth?**
`validate.py` reads the text layer back out of the clean PDF for three documents per
subtype, 39 in all, and looks for every identifier and every total literally. A hash
proves a file has not changed; it does not prove the file says what the ground truth
beside it says. This check does.

**Was any preprocessing done?**
The documents are generated already labelled; there is no cleaning step and no
annotation step, so there is no annotator agreement to report and no label noise from
human error.

**Was the raw data saved?**
Yes. `build/documents.jsonl` is the plan and the pre-render ground truth.
`build/render/` holds the clean renders that the degradation consumes. Both are
regenerable from the seed and are not distributed.

**Containers.**

| Tier | Page image | Document PDF |
|---|---|---|
| 1 | PNG, lossless | Vector, copied unchanged from the renderer |
| 2, 3, 5 | JPEG at the recorded quality | Raster, the degraded pages |
| 4 | One-bit PNG | Raster, the degraded pages |

Each page's container and its SHA-256 are recorded in the ground truth.

**Normalisation a scorer has to do.**
Dates are stored in ISO 8601 and printed in the locale format recorded in
`display_formats.date`. Money is stored as a plain two-decimal string and printed
with Indian digit grouping for INR and western grouping otherwise. A scorer that
compares raw strings will under-report accuracy; the harness normalises dates,
currency, whitespace and Unicode before matching, as `charter/methodology.md`
requires.

---

## Uses

**What has the dataset been used for?**
Nothing yet. As of 2026-09-02 no model has been run against it. The environment it
was built in has no model API access, so the Messy Scan Benchmark results tables are
empty and marked `not run`. Any table that says otherwise is wrong.

**What tasks is it suitable for?**
Field-level extraction, document classification, document-level
straight-through-processing measurement, confidence calibration, and per-tier and
per-language degradation studies. It is designed for `harness/` (`entail-bench`) but
the format is plain JSONL and PDFs and needs no particular harness.

**Is there anything that makes it unsuitable for some uses?**
Yes.

- Do not use it to train or evaluate handwriting recognition. The handwriting is
  drawn, not written.
- Do not use it to calibrate a fraud or identity-verification system. Every
  identifier fails its checksum by design, so a validator scored on this data will
  see a 100% rejection rate that means nothing.
- Do not quote an absolute accuracy number from it as a production accuracy number.
  See the limitations below.
- Do not treat the Hindi, Gujarati or Tagalog text as a language benchmark. It is a
  fixed set of field labels and one sentence, not a corpus.

**Is there a repository of works that use it?**
Results produced by Entailment Labs will live under `10-benchmarks/results/` with
the dataset version in the folder name.

---

## Distribution

**How is the dataset distributed?**
As four scripts and a seed. The 50-document public sample is intended for
distribution as a release archive alongside the public benchmark repository
(`nagu-io/benchmarks`). Rendered binaries are not committed to the repository, and
neither is `ground-truth.jsonl`; all of them are rebuilt with three commands, which
`README.md` gives, and `LAYOUT.md` at the root of the repository lists every exclusion
with its size and hash so the decision can be checked rather than trusted.

**When?**
With the first public release of the Messy Scan Benchmark. Nothing is published by
an agent; a person publishes it.

**Licence.**
Data: **CC BY 4.0**. Code (`generate.py` and the four modules it assembles —
`identifiers.py`, `content.py`, `schemas.py`, `builders.py` — plus `render.py`,
`degrade.py` and `validate.py`): **MIT**. Attribution: "Messy Scan dataset v1.0.0, Entailment Labs, CC BY 4.0".

**Third-party restrictions, export controls, fees.**
None. The typefaces used at render time are not redistributed with the dataset; they
are named so a rebuild can install them.

**IP, and what the licence does not cover.**
The dataset contains no third-party content. It contains no real trade marks and no
real logos: each document's mark is a geometric shape with the invented
organisation's initials, drawn by `render.py`.

---

## Maintenance

**Who maintains it?**
Entailment Labs. Contact `hello@entailmentlabs.com`. Security reports:
`security@entailmentlabs.com`.

**Will it be updated?**
Yes, on the quarterly benchmark cadence set out in `charter/methodology.md`, with a
changelog. Dataset versions are semantic. Results folders name the dataset version
that produced them, so a result is never silently re-attributed to a different build.

**How will errors be corrected?**
A defect in a document's ground truth is a defect in `generate.py`. The fix goes into
the script, the version increments, and the previous version stays reproducible from
its seed and commit. Ground truth is never patched by hand: a hand-patched value
cannot be regenerated and would break the guarantee this dataset rests on.

**Will older versions be supported?**
Every released version is reproducible from its seed and commit hash. Results tables
name the version that produced them.

**Can others extend it?**
Yes, under the licences above. The generator is parameterised by document type, so a
new type is a builder function, a schema entry and an arithmetic rule in
`validate.py`. A partner who wants their own document mix should fork the generator
rather than hand-edit the output.

**How is retention and deletion handled?**
There is nothing to retain or delete. No personal data was collected, so
`02-security/security-policy-set/10-data-retention-and-deletion.md` has nothing to
act on for this dataset. That is a deliberate property, not an oversight.

---

## Known biases and limitations

Read this before quoting any number produced with this dataset.

1. **It is synthetic, and synthetic is easier than real in ways that are hard to
   see.** The text is typeset, not printed and rephotographed. Character shapes are
   clean under the degradation rather than worn. Real scans carry artefacts we have
   not modelled: toner streaks, folded corners, coffee, torn edges, the shadow of a
   hand, moiré from a screen photograph, ink bleed-through from the reverse side. A
   system that scores well here can still fail on a real intake queue. Treat a score
   as a floor on difficulty, not a prediction of production accuracy.

2. **The layouts are ours, and there are four of them.** Each document is drawn in
   one of four layout variants. Real vendors have hundreds of layouts, and layout
   diversity is a first-order driver of extraction difficulty. A model can learn our
   four. This is the main reason the 200-document private split exists.

3. **The degradation is parametric.** Every effect is a mathematical operation with a
   recorded parameter. Real degradation is not drawn from a uniform distribution. In
   particular the parameters are independent of one another, where in the real world
   a bad phone photo is bad in several correlated ways at once.

4. **The catalogue is narrow.** Twenty line items, five insurers, four garages, four
   hospitals, five utility providers, one health diagnosis list of six. Vocabulary
   overfitting is possible and would inflate scores.

5. **Language coverage is thin.** The second language on a tier-5 page is a set of
   field labels and one sentence, in one of three languages. There is no Devanagari
   or Gujarati body text, no Tagalog document body, and no right-to-left script at
   all. Do not read a per-language number here as a multilingual capability score.

6. **The jurisdiction mix is a choice, not a market.** Forty per cent invoices, split
   evenly across four formats, with India over-represented in the KYC and claim sets.
   That reflects the buyer we build for, not the world.

7. **Identifier invalidity is guaranteed only to the extent stated.** Two identifier
   families — the Philippine TIN and the plain account, permit and reference numbers
   — have no published checksum, so no invalidity can be proved for them. Rule B in
   the sweep constrains only 16-digit windows inside long digit runs. Both limits are
   stated above and enforced honestly by `validate.py`, which reports "no public
   check available" rather than counting those fields as passing.

8. **Names could still collide.** Syllable assembly makes a collision with a real
   company or person unlikely, not impossible. If a name in this dataset matches
   yours, it is coincidence; write to `hello@entailmentlabs.com` and it will be
   removed in the next version.

9. **Bit-level reproducibility depends on Chromium.** The plan and the ground truth
   are byte-identical from a seed. The rendered pixels are not guaranteed identical
   across Chromium builds, so a rebuild on another machine can produce different file
   hashes for the same ground truth.

10. **No result exists yet.** This dataset has been validated, not used. Every row of
    the Messy Scan results table reads `not run` until a run with real model access
    produces one.
