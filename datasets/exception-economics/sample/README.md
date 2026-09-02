# Public sample — exception-economics

The `public_sample` split: 100 of the 2000 items in this set. Every line is one exception
item — an invoice-to-purchase-order reconciliation, a KYC case or a support ticket — with
its source record, its ground-truth outcome, its difficulty tier and the six parameters that
set it, its lifecycle state, and the labour-model keys the scorer prices it with.

It is a split, not an excerpt. `generate.py` assigns it at generation time from the dataset
seed, so it is the same 100 items on every machine, it is stratified across work type and
tier like the private split, and nothing in it overlaps the private holdout.

## What is committed here

| File | Committed | Bytes | SHA-256 |
|---|---|---:|---|
| `preview.jsonl` | Yes | 6,495 | `29b9e384b0198908be89856a04d73873f6998dc62ee1b9e1edbef6f34423be90` |
| `ground-truth.jsonl` | No — rebuilt | 159,359 | `9fdf4810de072df3cee7338b08f6ea6748eb809bac9e1347020c39630b96b150` |

`preview.jsonl` is the first 4 lines of the sample — `EE-0011`, `EE-0026`, `EE-0027` and
`EE-0052` — committed verbatim so that the shape of an item can be read here without running
anything. It is a convenience for the reader and is not a split: no figure anywhere in this
repository is computed over it.

`ground-truth.jsonl` follows the rule that governs every other large artefact in this
repository, set out in `LAYOUT.md`: where a seed and a committed script reproduce a file
exactly, the repository holds the script and the hash rather than the output. Rebuild it with

```bash
cd datasets/exception-economics
python3 generate.py --seed 20260902
sha256sum sample/ground-truth.jsonl
```

and compare the result against the hash in the table above.

The second reason the line fell here rather than a few hundred kilobytes further out: the
commit that created this repository was made through an interface that carries text one batch
at a time. That constraint is recorded rather than dressed up as a design choice alone.
Nothing a reader needs in order to check a published figure is affected — the generator, the
schema, the manifest, the scorer and the results are all committed.
