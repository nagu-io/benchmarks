# Artefacts this repository does not carry, and how to check yours

Every path below is produced by a script in this repository from a published seed. None of
them is committed. Each one is listed with the size and the SHA-256 of the copy that produced
the results published here, so a rebuild can be checked rather than trusted.

The rule is the one in `LAYOUT.md`: the repository holds what a reader has to trust — the
generators, the schemas, the manifests, the harness, the charter and the results — and not
what those can produce for themselves. A clone plus the commands below reproduces the rest.

## The files

| Path | Bytes | SHA-256 of the copy used here |
|---|---:|---|
| `datasets/messy-scan/ground-truth.jsonl` | 4,999,001 | `b7452d7e90e3bc61d3726e015b68c2ae8e32a16e5a3099c504382f39f0b582bf` |
| `datasets/exception-economics/ground-truth.jsonl` | 3,175,920 | `49af7a5ee30fb3fcdd458458c4194ec2ff9409d96e0ff432556cedf8580e5733` |
| `datasets/honest-containment/scenarios.jsonl` | 1,584,548 | `2a4cdf7688c47e86cc0b71a3eb79c056d3e71af7a9977ded45c4176070c5afd9` |
| `datasets/honest-containment/transcripts/` | 1,282,354 in 300 files | `db5d1c7f31e4d672e6cae437a395c4c15d912fb4e4a6b3ee71ec10c781561f2b` |
| `datasets/honest-containment/audio-manifest.jsonl` | 657,860 | `fc4909db5a0427c9f075a74f6330c90f1bef4005475a1cdac29c738b8ebcee6f` |
| `results/exception-economics-v1.0/drift.json` | 491,275 | `128473d24d112ad6c5ed3966c6781581b82646049d9654c8ed69b5a77448f636` |
| `results/honest-containment-v1.0/runs/voice-platform-a/run-1/contacts.jsonl` | 292,452 | `9bff9b1776384d8c090d61a3c78145599cdaaada328260b4687f44452d45c302` |
| `results/honest-containment-v1.0/runs/voice-platform-b/run-1/contacts.jsonl` | 292,452 | `74603ff8ecf0786bcbd436aa8b3ac964ca56efc2adc3ce44a412668d034cfff7` |
| `datasets/messy-scan/sample/ground-truth.jsonl` | 244,734 | `0882c9d755e404c09e447616a3b8637da5451e4f13246de25aa7fe347ec334a0` |
| `datasets/honest-containment/audio-specs.jsonl` | 218,373 | `9a29ab3a386019ecd91f1b055c704d3bebe03977faaa6030329813785bed9c5c` |
| `results/honest-containment-v1.0/runs/entailment-agent/run-1/contacts.jsonl` | 191,352 | `06ab3be4975b05afd5694b74cad0729b3bb1aaea24fa6005c5ad626356561888` |
| `results/honest-containment-v1.0/runs/general-llm/run-1/contacts.jsonl` | 190,152 | `f46271881254d3df3ed30c3fc00d411f156d47922fdad3c58d46bfc43d867297` |
| `datasets/exception-economics/sample/ground-truth.jsonl` | 159,359 | `9fdf4810de072df3cee7338b08f6ea6748eb809bac9e1347020c39630b96b150` |
| `notes/methodology-for-procurement.pdf` | 127,889 | `0c19fe604b92f6fb047b0e09ae86bcb60a4aea265a278d204b1f0cb6ec14a054` |
| `results/exception-economics-v1.0/scores-baseline.json` | 45,248 | `e139c9a9bbe525c57fd9e3e949d8c8e90c5199137a3e5dd26f399515ca0598ec` |
| `bakeoff/bakeoff-scorecard.xlsx` | 34,117 | `9982b319a3cd3193823815d60eb2cc7f69093c766ddd5967861db39365ab6709` |
| `results/exception-economics-v1.0/scores-all.json` | 29,861 | `89c86c309f2d78622f8b0b96ae7d8c565b90838b33864ea6478c5fe0dce5614b` |
| `bakeoff/bakeoff-offer.docx` | 29,517 | `e816f7acad30c68316716b2db8f61d00c2590bb4924394d83300934ef73f7c11` |
| `bakeoff/wordmark-3x.png` | 18,109 | `afcbf3ae0ae0f6f68bffb7f96684fc6f54e8413abb4984dd026be0dada8ecb5d` |

`transcripts/` is a directory rather than a file. The hash is of its 300 files concatenated in
sorted order, and `datasets/honest-containment/manifest.json` records the same value, so the
check does not depend on this page.

## How to rebuild and check

```bash
# Messy Scan: ground truth, renders and degradations
cd datasets/messy-scan
python3 generate.py --seed 20260902
python3 render.py
python3 degrade.py
python3 validate.py --strict-render
sha256sum ground-truth.jsonl sample/ground-truth.jsonl

# Honest Containment: scenarios, transcripts, audio specifications
cd ../honest-containment
python3 generate.py --seed 20260902
python3 tts.py                        # audio; see the datasheet for the voice limitations
python3 validate.py
sha256sum scenarios.jsonl audio-specs.jsonl audio-manifest.jsonl
find transcripts -type f | sort | xargs cat | sha256sum

# Exception Economics: items, the scored JSON and the drift curve
cd ../exception-economics
python3 generate.py --seed 20260902
python3 validate.py
python3 score.py --out ../../results/exception-economics-v1.0/scores-baseline.json
python3 score.py --population all --out ../../results/exception-economics-v1.0/scores-all.json
python3 drift.py --out ../../results/exception-economics-v1.0/drift.json
python3 report.py --results ../../results/exception-economics-v1.0
sha256sum ground-truth.jsonl sample/ground-truth.jsonl
cd ../../results/exception-economics-v1.0
sha256sum scores-baseline.json scores-all.json drift.json

# The bake-off kit: the wordmark, the offer document and the scorecard
cd ../../bakeoff
node render-wordmark.mjs
node build_offer.js
python3 build_scorecard.py
python3 verify_scorecard.py            # recomputes every formula independently
sha256sum bakeoff-offer.docx bakeoff-scorecard.xlsx wordmark-3x.png

# The procurement note, as a PDF
cd ../notes/methodology-pdf-source
python3 build.py
sha256sum ../methodology-for-procurement.pdf
```

`report.py` rewrites the markdown files in `results/exception-economics-v1.0/` from the two
JSON files it has just been given. Those markdown files are committed, so after a rebuild
`git status` should report no change to them. If it reports one, a figure has moved and the
cause is worth finding before anything is published.

A rebuilt `.docx`, `.xlsx` or `.pdf` will not hash the same as the copy above unless the
build is byte-deterministic, because those formats record a build timestamp. Where a hash
differs, `verify_scorecard.py` is the check that matters for the scorecard: it recomputes
every formula independently and fails on a mismatch.

The four `contacts.jsonl` files under `results/honest-containment-v1.0/runs/` are the
per-contact records of a run that did not happen: every row carries `not run` and the reason.
They are rebuilt by the same command that would perform a run, and they will be replaced the
first time a run actually occurs.

## Why a hash and not the file

Two reasons, in order of weight.

The first is the one in `LAYOUT.md` and it holds regardless of how this repository was
published: a 2.1 GB working tree has no business in git when a seed and a script reproduce it
exactly, and a hash makes the rebuild checkable.

The second is specific to this build and worth stating plainly. The commit that created this
repository was made through an interface that carries text, one batch at a time, with a
per-file ceiling of a few tens of kilobytes. That constraint decided where the line fell for
several of the files above — the two `sample/ground-truth.jsonl` files and the two scored
JSON files would otherwise have been committed. It does not change what a reader can verify:
every figure published here is reproduced by a clone, the seeds and the commands above, and
checked against these hashes. Where a file was excluded for that reason rather than for size
alone, a small committed substitute stands in its place: `sample/preview.jsonl` for the
samples, and the results pages themselves for the scored JSON.
