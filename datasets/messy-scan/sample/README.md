# Public sample — messy-scan

The `public_sample` split: 50 of the 1,000 documents in this set. Every line is one
document — its field-level ground truth, which published check each of its identifiers
fails and how, the full degradation parameter set that produced the scan, and the render
manifest for each page with byte size, pixel dimensions and SHA-256.

It is a split, not an excerpt. It is assigned from the dataset seed, stratified across the
thirteen subtypes and then across the five tiers, so it is the same 50 documents on every
machine and nothing in it overlaps the private holdout. `MANIFEST.md` sets out how both
splits are drawn.

## What is committed here

| File | Committed | Bytes | SHA-256 |
|---|---|---:|---|
| `preview.jsonl` | Yes | 5,799 | `148f3d4c75c55d00ca5d9c4eaa2b58b2ca77f10f79356f27e21d6b5dbed4d440` |
| `ground-truth.jsonl` | No — rebuilt | 244,734 | `0882c9d755e404c09e447616a3b8637da5451e4f13246de25aa7fe347ec334a0` |

`preview.jsonl` holds the first document of the sample, `msc-inv-in_gst-0016` — an Indian
GST invoice at tier 3, the phone-photo tier — committed verbatim so that the shape of a
record can be read here without running anything: the field-level ground truth with money in
both display and minor-unit form, the four identifiers with the published rule each one
breaks and the correct value it was broken from, the twelve degradation parameters, and the
render manifest. It is a convenience for the reader and is not a split: no figure anywhere in
this repository is computed over it.

`ground-truth.jsonl` follows the rule that governs every other large artefact in this
repository, set out in `LAYOUT.md`: where a seed and a committed script reproduce a file
exactly, the repository holds the script and the hash rather than the output. The page images
and PDFs this file references are excluded for the same reason and are rebuilt by the same
commands.

```bash
cd datasets/messy-scan
python3 generate.py --seed 20260902
python3 render.py --select public_sample
python3 degrade.py --skip-existing
sha256sum sample/ground-truth.jsonl
```

Compare the result against the hash in the table above. `validate.py` additionally checks
every file the sample references against its recorded SHA-256, so a rebuilt sample is checked
page by page rather than trusted.

The second reason the line fell here rather than a few hundred kilobytes further out: the
commit that created this repository was made through an interface that carries text one batch
at a time. That constraint is recorded rather than dressed up as a design choice alone.
Nothing a reader needs in order to check a published figure is affected — the generator, the
schemas, the manifest, the validator and the results are all committed.
