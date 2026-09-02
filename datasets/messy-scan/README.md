# Messy Scan dataset v1.0.0

One thousand synthetic business documents with known-answer ground truth, degraded
across five difficulty tiers. Built for the Messy Scan Benchmark, which measures what
document extraction actually does on the traffic a BPO sees: rescans, phone photos,
faxes with stamps over the text, mixed-language bundles from a messaging app.

The data is synthetic. Every document was written and drawn by the scripts in this
folder. Read `datasheet.md` before quoting a number from it.

---

## Regenerate the whole dataset from a seed

Three commands. About 40 minutes on two cores, or about 25 if the degradation is
sharded across both (see "partial builds"). Measured on this build: generate 0.3 s,
render 377 s for 1,000 documents, degrade about 17 minutes as two parallel shards,
validate 3 s.

```bash
python3 generate.py --seed 20260902     # plan + ground truth for 1,000 documents
python3 render.py                       # HTML -> Chromium -> PDF + PNG per page
python3 degrade.py                      # tier degradation, hashes, splits
```

Then check it:

```bash
python3 validate.py
```

`validate.py` exits non-zero if anything is wrong and prints a summary table. Add
`--strict-render` to fail when any document has no rendered artefact.

### Prerequisites

- Python 3.11 with `pillow`, `numpy`, `opencv-python`, `playwright`
  (`pip install X --break-system-packages`)
- Chromium already installed for Playwright. In this environment it is at
  `/opt/pw-browsers`; `render.py` sets `PLAYWRIGHT_BROWSERS_PATH` itself. Do not run
  `playwright install`.
- Fonts: IBM Plex Sans, DejaVu, Carlito, Caladea, and `fonts-noto-core` for Hindi and
  Gujarati. Check with `python3 render.py --check-fonts`, which exits non-zero if an
  Indic face is missing rather than letting a tier-5 page render as tofu.

### Partial builds

Rendering and degradation are resumable and shardable.

```bash
python3 render.py --select splits                 # public sample + private split only
python3 render.py --select splits --stratified 100  # plus 100 more across every subtype and tier
python3 render.py --skip-existing                 # finish an interrupted run
python3 degrade.py --shards 2 --shard 0 --no-splits &   # one core
python3 degrade.py --shards 2 --shard 1 --no-splits &   # the other
python3 degrade.py --skip-existing                # final pass: ground truth + splits
```

`ground-truth.jsonl` always carries all 1,000 documents. A document that has not been
rendered has `"render": null`, and `validate.py` reports how many and prints the
command that finishes the build.

---

## Tier distribution

| Tier | Name | Planned share | Documents | What is done to the page |
|---|---|---|---|---|
| 1 | Clean digital | 15% | 152 | Nothing. Vector PDF, lossless PNG |
| 2 | Flatbed scan | 25% | 252 | Greyscale, paper tone, skew, lid shadow, blur, noise, dust, JPEG |
| 3 | Phone photo | 25% | 248 | Perspective warp, rotation, desk background, shadow gradient, glare, white-balance shift, blur, sensor noise, JPEG |
| 4 | Fax quality with marks | 20% | 200 | Stamps over text, signatures, margin notes, staple holes and tear, low fax resolution, one-bit dither, speckle, scan-line dropout |
| 5 | Mixed bundle | 15% | 148 | Multi-page bundle, second-language cover sheet, duplicated page, rotated and reordered pages, mixed base effects, two resamples, two JPEG passes |
| | **Total** | 100% | **1,000** | |

The counts are not exactly 150/250/250/200/150 because the shares are applied inside
each subtype with largest-remainder rounding, so every subtype appears in every tier.
`validate.py` recomputes the plan the same way and fails on any difference.

### Composition

| Type | Documents | Subtypes |
|---|---|---|
| Invoices | 400 | Indian GST 100, US 100, EU VAT 100, Philippine BIR 100 |
| KYC packs | 250 | Aadhaar-style 130, PAN-style 120 |
| Insurance claims | 200 | Motor 80, health 70, property 50 |
| Purchase orders | 150 | India 50, US 40, EU 35, Philippines 25 |

### Languages

| Languages on the page | Documents |
|---|---|
| English only | 852 |
| English and Hindi | 66 |
| English and Gujarati | 43 |
| English and Tagalog | 39 |

Two languages on one page is a tier-5 property.

---

## What is in this folder

| Path | What it is |
|---|---|
| `generate.py` | The composition plan, the tier and split allocation, and the assembly loop. Deterministic from `--seed` |
| `identifiers.py` | The real check-digit algorithms, and the `make_*` functions that compute a correct value and emit a broken one |
| `content.py` | Invented names, addresses and catalogue; money formatting |
| `schemas.py` | The field schema per document type, and the published rule each identifier is broken against |
| `builders.py` | One builder per subtype, plus the logical page plan |
| `render.py` | HTML templates and the Chromium render. A4 at 200 dpi |
| `degrade.py` | The five tiers, the final artefacts, the hashes, the splits |
| `validate.py` | Nine checks, self-tested checksum code, summary table |
| `ground-truth.jsonl` | One JSON object per document, all 1,000. Rebuilt from the seed rather than committed; hash in the repository's `REGENERATED.md` |
| `datasheet.md` | Datasheets for Datasets: motivation, composition, generation, degradation ranges, uses, distribution, maintenance, biases, limitations |
| `MANIFEST.md` | The public and private splits and why the private one exists |
| `build/` | Intermediate: the plan and the clean renders. Not distributed |
| `documents/` | Final artefacts, one folder per document |
| `sample/` | The 50-document public split. `preview.jsonl` is committed; the full split is rebuilt — see `sample/README.md` |
| `private/` | The 200-document held-out split. Never published |

Rendered binaries are not committed, and neither is `ground-truth.jsonl`. All of them are
rebuilt with the three commands above; `LAYOUT.md` at the root of this repository explains
every exclusion and gives the sizes, so the decision can be checked rather than trusted.

## One ground-truth record

```
doc_id, dataset, dataset_version, schema_version, seed
doc_type, doc_subtype, locale, tier, languages, page_count, split, layout_variant
display_formats          how the date and the money are printed on the page
schema                   field name -> field kind, for this document's type
fields                   every ground-truth value, including the line items
identifier_provenance    which check each identifier fails, and how
degradation              every parameter used, by name
render                   the PDF and every page: path, SHA-256, bytes, size
```

## What validate.py checks

Nine checks. It exits non-zero if any of them fails.

1. Its own checksum code, against published vectors and round-trip properties, before
   it judges anything.
2. Structure: parses, no duplicate ids, subtype counts match the plan.
3. Fields: every field in a document's schema is present and non-empty.
4. Arithmetic: every line amount, subtotal, tax and total reconciles, re-derived
   independently of the generator.
5. Identifiers: every one fails its check, with the check named and classified as a
   real checksum, a published structural rule, or "no public check available".
6. A sweep over every string: no card-shaped digit run is Luhn-valid, no 12-digit run
   is Verhoeff-valid.
7. Tier distribution against the plan; split sizes and disjointness.
8. Every referenced rendered file exists and its SHA-256 matches.
9. The rendered page says what the ground truth says. Three documents per subtype are
   read back out of the PDF text layer and every identifier and total is looked for
   literally.

## Licence

Data: CC BY 4.0. Code: MIT. Attribution: "Messy Scan dataset v1.0.0, Entailment Labs,
CC BY 4.0".
