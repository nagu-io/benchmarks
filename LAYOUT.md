# Layout of the public repository

Which folders of the internal working tree `10-benchmarks/` map to which paths in
`nagu-io/benchmarks`, and which artefacts are deliberately kept out.

The rule behind every decision below: **anything that a seed and a script can rebuild does
not go in git.** The repository holds what a reader has to trust — the generators, the ground
truth, the schemas, the manifests, the hashes, the harness and the results — and nothing it
can produce for itself. That is why a 2.1 GB working tree publishes as a repository of a few
tens of megabytes, and why a clone is enough to reproduce every published figure.

---

## 1. The map

| Working tree | Public repository | Goes in |
|---|---|---|
| `charter/methodology.md` | `charter/methodology.md` | Yes, whole |
| `charter/contract-clauses.md` | `charter/contract-clauses.md` | Yes, whole |
| `harness/` | `harness/` | Yes, except `.pytest_cache/`, `__pycache__/`, `*.egg-info/` |
| `datasets/<suite>/*.py` | `datasets/<suite>/*.py` | Yes — generators, renderers, degraders, scorers, drift, validators |
| `datasets/<suite>/ground-truth.jsonl` | same path | Yes |
| `datasets/<suite>/manifest.json`, `MANIFEST.md` | same path | Yes |
| `datasets/<suite>/datasheet.md`, `README.md` | same path | Yes |
| `datasets/honest-containment/policies/` | same path | Yes — 38 policy documents, the agent's whole world |
| `datasets/honest-containment/transcripts/` | same path | Yes — 1.8 MB of text |
| `datasets/honest-containment/audio-specs.jsonl`, `audio-manifest.jsonl` | — | No — both are rebuilt from the seed. Their sizes and hashes are in `REGENERATED.md`; see 2.6 |
| `datasets/honest-containment/labelling/` | same path | Yes — the guide, the adjudication set, the kappa script |
| `datasets/exception-economics/labour-model.yaml` | same path | Yes |
| `datasets/<suite>/sample/ground-truth.jsonl` | same path | Yes |
| `day-60/` | `day-60/` | Yes, whole — rubric, scripted incidents, scoresheet, self-assessment |
| `results/` | `results/` | Yes, except the five files in 2.6 — leaderboards, findings, reproduce, the scored JSON, the run records |
| `notes/*.mdx`, `notes/release-checklist.md` | — | No. Research notes publish on the main site; the release checklist is internal |
| `site/` | — | No. The site is deployed, not published as source, and its `repo-template/` is this file's own source |
| `.agent-context.md`, `BENCHMARK-PACK.md` | — | No. Internal build instructions |

Three files in this folder have no working-tree counterpart and are written for the public
repository only: `README.md`, `CONTRIBUTING.md` and `LAYOUT.md`, together with
`CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, the licence files and `.github/`.

---

## 2. What stays out, and why

### 2.1 Rendered documents — 1.4 GB, 4,211 files

`datasets/messy-scan/documents/` holds the page images and PDFs for all 1,000 documents.
`datasets/messy-scan/build/` holds another 373 MB of intermediate render output.

Neither is committed. Both are rebuilt:

```bash
cd datasets/messy-scan
python3 generate.py --seed 20260902   # writes ground-truth.jsonl and manifest
python3 render.py                     # writes build/
python3 degrade.py                    # writes documents/
python3 validate.py
```

`ground-truth.jsonl` carries, per document, the render manifest with each page's path, byte
size and pixel dimensions, and the full degradation parameter set — blur sigma, noise sigma,
skew, glare geometry, colour mode, compression quality. A rebuild is checked against those
values, so a reader can confirm the images they generated are the images that were scored,
without either of us moving a gigabyte.

`.gitignore` in that folder excludes `build/`, `documents/` and `sample/documents/`.

### 2.2 Rendered audio — 79 MB, 970 files

`datasets/honest-containment/audio/` holds the rendered turns for the 120 audio contacts.
Not committed. Rebuilt with `python3 tts.py` from the seed.

The two files that describe it are not committed either, for the reason in 2.6, but both are
rebuilt by the same command: `audio-specs.jsonl`, the 120 specifications with language
condition, accent, noise bed, target signal-to-noise ratio and turn text, and
`audio-manifest.jsonl`, 644 KB carrying the per-file SHA-256 and the *measured* signal-to-noise
ratio for every one of the 970 files. `validate.py --strict-audio` checks a rebuild against the
hashes in the manifest it has just rebuilt, so the check is of internal consistency; the
SHA-256 in `REGENERATED.md` is what ties a rebuild back to the copy described here.

### 2.3 The private splits — never, at any size

| Split | Items | Where it lives | Published |
|---|---|---|---|
| `datasets/messy-scan/private/` | 200 documents | Internal only | **No. Never.** |
| `datasets/honest-containment/private/scenarios.jsonl` | 60 scenarios | Internal only | **No. Never.** |
| Exception Economics private holdout | 300 items | Marked by the `split` field in the committed ground truth | See the note below |

The first two are excluded from the public repository entirely, including their ground truth.
They exist for one comparison: the gap between a system's score on the public sample and its
score on the private split. Publishing them would destroy the only detection method the
charter has for tuning against the public set.

Exception Economics is the exception, and the reason is worth stating plainly. Its ground
truth is a single committed file in which each item carries a `split` field, and the private
holdout is a slice of it rather than a separate file. That means its holdout is visible to
anyone who reads the file. It is therefore not a defence against tuning, and no claim is made
that it is. If that matters for a future release, splitting the file is a major dataset
version.

### 2.4 Caches and build junk

`__pycache__/`, `*.pyc`, `.pytest_cache/`, `*.egg-info/`, `node_modules/`, `.next/`, `out/`.
Excluded by `.gitignore`.

### 2.5 Working files a labeller produces

`datasets/honest-containment/labelling/packets/`, `labels-*.csv` and `judge-agreement.json`
are excluded. Labels are committed deliberately, through the adjudication set, rather than by
accident through a working directory.

`suite/config/agents.json` is excluded because it is the file a person fills with endpoints
and key names. `suite/config/agents.example.json` is committed instead, with every value
reading `placeholder`.

### 2.6 Large regenerable data files

Six files are rebuilt rather than committed, for the reason that governs every other exclusion
above: a seed and a committed script reproduce them exactly, so the repository holds the script
and the hash instead of the output.

| Path | Bytes | Rebuilt by |
|---|---|---|
| `datasets/messy-scan/ground-truth.jsonl` | 4,999,001 | `generate.py --seed 20260902` |
| `results/exception-economics-v1.0/drift.json` | 491,275 | `drift.py` |
| `results/honest-containment-v1.0/runs/*/run-1/contacts.jsonl` | 190,152 to 292,452 each | the same command that would perform a run |
| `datasets/honest-containment/audio-specs.jsonl` | 218,373 | `generate.py --seed 20260902` |
| `datasets/honest-containment/audio-manifest.jsonl` | 644 KB | `tts.py` |

`REGENERATED.md` carries the SHA-256 of every one, so a rebuild is checked rather than trusted,
and it states plainly the second reason these particular files fell outside the line: the commit
that created this repository was made through an interface that carries text one batch at a
time. Nothing a reader needs to verify a published figure is affected — the generators, the
schemas, the manifests, the harness, the charter and the results are all here — but the
constraint is recorded rather than dressed up as a design choice alone.

The four `contacts.jsonl` files are the per-contact records of a run that did not happen: every
row carries `not run` and the reason. They will be replaced the first time a run occurs.

---

## 3. Release assets, not git objects

Two things are published as GitHub release assets attached to each version tag, because they
are binary and large but a reader genuinely wants them without running a renderer.

| Asset | Size | What it is |
|---|---|---|
| `messy-scan-v1.0.0-sample.zip` | about 60 MB | The 50-document public sample: `ground-truth.jsonl` plus the rendered pages and PDFs |
| `honest-containment-v1.0.0-audio-sample.zip` | placeholder — set when the first release is cut | A subset of the rendered audio, enough to hear each language condition and noise level |

Both are reproducible from the seed. They exist so that a BPO engineer can run the harness end
to end in ten minutes without installing a rendering stack, which is the whole point of
publishing a sample at all.

The release also carries the SHA-256 of each asset in the release notes, and each asset's
contents are covered by `MANIFEST.md` in its dataset folder.

---

## 4. Sizes, so the decision is checkable

| Item | Working tree | In the repository |
|---|---|---|
| Messy Scan rendered documents | 1.4 GB | 0 — rebuilt |
| Messy Scan render intermediates | 373 MB | 0 — rebuilt |
| Messy Scan private split | 269 MB | 0 — never published |
| Messy Scan public sample images | 60 MB | 0 — a release asset |
| Honest Containment audio | 79 MB | 0 — rebuilt |
| Messy Scan `ground-truth.jsonl` | 4.8 MB | 0 — rebuilt, hash in `REGENERATED.md` |
| Exception Economics `ground-truth.jsonl` | 3.1 MB | 3.1 MB |
| Honest Containment `scenarios.jsonl` | 1.6 MB | 0 — rebuilt, hash in `REGENERATED.md` |
| Honest Containment `audio-manifest.jsonl` | 644 KB | 0 — rebuilt, hash in `REGENERATED.md` |
| `harness/` | 1.5 MB | 1.5 MB |
| `results/` | 1.7 MB | 460 KB — the five files in 2.6 are rebuilt |
| `day-60/` | 80 KB | 80 KB |
| `charter/` | 140 KB | 140 KB |

Roughly 2.1 GB of working tree, of which about 4 MB is committed.

---

## 5. Before the first push

A checklist for whoever creates the repository. `notes/release-checklist.md` in the working
tree carries the wider list; these are the items specific to the layout.

1. Copy the paths in section 1, in that order. Do not copy `10-benchmarks/site/` or
   `10-benchmarks/notes/`.
2. Copy the files in this folder to the repository root: `README.md`, `CONTRIBUTING.md`,
   `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`, `LICENSE-DATA`, `CITATION.cff`,
   `LAYOUT.md`, `.github/`, and `datasets/LICENSE`.
3. Check the `.gitignore` in each dataset folder is present before the first `git add`. A
   1.4 GB accidental commit cannot be undone by a later deletion; the objects stay in the
   history and the repository stays that size for ever.
4. `git add -A && git status` and read the file count before committing. If it is in the
   thousands, a `documents/` or `audio/` folder has slipped in.
5. Run the CI workflow on a branch before making the repository public. The `no-network` and
   `no-estimated-figures` jobs are the two that would be embarrassing to fail in public.
6. Confirm no key, no partner name and no internal path appears anywhere in the history. The
   `lint` job checks the working tree; the history needs a separate pass.
7. Cut the `v1.0.0` tag, attach the release assets in section 3, and put each asset's SHA-256
   in the release notes.
8. Only then make the repository public.
