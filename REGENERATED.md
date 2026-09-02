# Artefacts this repository does not carry, and how to check yours

Every file below is produced by a script in this repository from a published seed. None of
them is committed. Each one is listed with the size and the SHA-256 of the copy that produced
the results published here, so a rebuild can be checked rather than trusted.

The rule is the one in `LAYOUT.md`: the repository holds what a reader has to trust — the
generators, the schemas, the manifests, the harness, the charter and the results — and not
what those can produce for themselves. A clone plus the commands below reproduces the rest.

## The files

| Path | Bytes | SHA-256 of the copy used here |
|---|---|---|
| `datasets/messy-scan/ground-truth.jsonl` | 4,999,001 | `b7452d7e90e3bc61d3726e015b68c2ae8e32a16e5a3099c504382f39f0b582bf` |
| `results/exception-economics-v1.0/drift.json` | 491,275 | `128473d24d112ad6c5ed3966c6781581b82646049d9654c8ed69b5a77448f636` |
| `results/honest-containment-v1.0/runs/voice-platform-a/run-1/contacts.jsonl` | 292,452 | `9bff9b1776384d8c090d61a3c78145599cdaaada328260b4687f44452d45c302` |
| `results/honest-containment-v1.0/runs/voice-platform-b/run-1/contacts.jsonl` | 292,452 | `74603ff8ecf0786bcbd436aa8b3ac964ca56efc2adc3ce44a412668d034cfff7` |
| `datasets/honest-containment/audio-specs.jsonl` | 218,373 | `9a29ab3a386019ecd91f1b055c704d3bebe03977faaa6030329813785bed9c5c` |
| `results/honest-containment-v1.0/runs/entailment-agent/run-1/contacts.jsonl` | 191,352 | `06ab3be4975b05afd5694b74cad0729b3bb1aaea24fa6005c5ad626356561888` |
| `results/honest-containment-v1.0/runs/general-llm/run-1/contacts.jsonl` | 190,152 | `f46271881254d3df3ed30c3fc00d411f156d47922fdad3c58d46bfc43d867297` |
| `notes/methodology-for-procurement.pdf` | 127,889 | `0c19fe604b92f6fb047b0e09ae86bcb60a4aea265a278d204b1f0cb6ec14a054` |
| `bakeoff/bakeoff-scorecard.xlsx` | 34,117 | `9982b319a3cd3193823815d60eb2cc7f69093c766ddd5967861db39365ab6709` |
| `bakeoff/bakeoff-offer.docx` | 29,517 | `e816f7acad30c68316716b2db8f61d00c2590bb4924394d83300934ef73f7c11` |
| `bakeoff/wordmark-3x.png` | 18,109 | `afcbf3ae0ae0f6f68bffb7f96684fc6f54e8413abb4984dd026be0dada8ecb5d` |

## How to rebuild and check

```bash
# Messy Scan: ground truth, renders and degradations
cd datasets/messy-scan
python3 generate.py --seed 20260902
python3 render.py
python3 degrade.py
python3 validate.py --strict-render
sha256sum ground-truth.jsonl          # compare with the table above

# Honest Containment: scenarios, transcripts, audio specifications
cd ../honest-containment
python3 generate.py --seed 20260902
python3 tts.py                        # audio; see the datasheet for the voice limitations
python3 validate.py
sha256sum audio-specs.jsonl

# Exception Economics: items and the drift curve
cd ../exception-economics
python3 generate.py --seed 20260902
python3 score.py && python3 drift.py && python3 report.py
sha256sum ../../results/exception-economics-v1.0/drift.json

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
repository was made through an interface that carries text, one batch at a time, and cannot
carry a five-megabyte data file. That constraint decided where the line fell for the largest
few files. It does not change what a reader can verify: every figure published here is
reproduced by a clone, the seeds and the commands above, and checked against these hashes.
