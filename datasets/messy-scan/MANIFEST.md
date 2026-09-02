# Manifest — Messy Scan dataset v1.0.0 splits

Dataset version 1.0.0 · Seed 20260902 · Written 2026-09-02.

Three splits. One is published, one is never published, one is regenerated on demand.

| Split | Documents | Folder | Published |
|---|---|---|---|
| `public_sample` | 50 | `sample/` | Yes, as a release archive |
| `private_holdout` | 200 | `private/` | **No. Never.** |
| `open` | 750 | not materialised as a split | Regenerable from the seed |

Every document in `ground-truth.jsonl` carries its `split` field, so the assignment is
part of the ground truth and does not depend on which folders exist on disk.

## How the splits are drawn

Both splits are stratified twice: first across the thirteen subtypes in proportion to
their share of the 1,000 documents, then across the five tiers in proportion to the
tier plan. Within each (subtype, tier) bucket the documents are drawn with a stream
seeded from the dataset seed and the split name, so the assignment is deterministic
and reproducible. Rounding uses the largest-remainder method, so the split sizes are
exactly 50 and 200 and no subtype or tier is skipped where its count allows one.

The result: the 50-document sample is representative rather than convenient, and a
score on the sample is comparable in kind to a score on the private split. If the two
diverge, the divergence is about the system, not about the sampling.

## Why the private split exists

To detect overfitting to the public sample.

The public sample is 50 documents that anyone can download, inspect and iterate
against. That is the point of publishing it: a partner can run the harness end to end
before trusting a number. It is also, exactly, the risk. Prompts get tuned against
visible data. Layouts get memorised. A vendor who has seen the sample can score well
on it without having built anything that generalises — and there are only four layout
variants in this dataset, which makes memorisation cheap.

The 200-document private split is drawn from the same distribution and never leaves
Entailment Labs. Its use is one comparison: the gap between a system's score on the
public sample and its score on the private split.

- A small gap, within the run-to-run spread reported in the results table, means the
  public number can be read at face value.
- A large gap means the public number was fitted to the public sample, and the private
  number is the one that describes the system.

Both numbers are published when a run happens. The private *documents* are not, and
neither are their ground-truth values.

Our own pipeline is measured the same way, in the same table, with no special
formatting. A benchmark that exempts its author is not a benchmark.

## What is on disk

```
sample/
  ground-truth.jsonl        50 records, identical in form to the full file
  documents/<doc_id>/       document.pdf and the page images

private/
  .gitignore                keeps every file in this folder out of any repository
  ground-truth.jsonl        200 records
  documents/<doc_id>/       document.pdf and the page images
```

Each split folder is self-contained: the file paths inside its `ground-truth.jsonl`
resolve relative to the split folder itself, so `sample/` can be zipped and shipped
as it stands and every recorded SHA-256 still checks out. Verified on this build:
154 files referenced by `sample/ground-truth.jsonl`, all present, all matching.

Rendered binaries are not committed to any repository, in either folder. The public
sample is distributed as a release archive; both folders are rebuilt by the three
commands in `README.md`.

## Handling rules for the private split

1. `private/.gitignore` ignores every file in the folder except itself. It is the
   one file in `private/` that is committed, because a fresh clone must rebuild the
   split into a folder that is already protected. Check `git status --ignored` before
   any commit that touches this dataset.
2. The private split is not uploaded to a model provider, an annotation tool, an
   evaluation service or any third party, and no document from it is pasted into a
   prompt outside a scored run.
3. Scored runs against the private split record the model, the prompt hash and the
   date in `results/`, so any exposure is dated and auditable.
4. When the dataset version increments, the private split is redrawn from the new
   seed. A split that has been scored many times against many systems has leaked
   through its scores, however carefully the files were held.
5. If any part of the private split becomes public, it is retired: the version is
   incremented and a new private split is drawn. The compromised split is then treated
   as public data and may be released.

## Rebuilding a split on its own

```bash
python3 generate.py --seed 20260902
python3 render.py --select public_sample     # or private_holdout, or splits for both
python3 degrade.py --skip-existing
```

`degrade.py` writes `sample/` and `private/` from whatever has been rendered, and
`validate.py` reports the sizes and confirms the two are disjoint.
