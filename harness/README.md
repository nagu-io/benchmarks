# entail-bench

The evaluation harness for the Entailment Labs benchmark suites. Messy Scan is implemented; the other three suites in `../charter/methodology.md` are not built yet.

It scores a large language model, a document service and a partner's own pipeline through one interface, with one prompt and one scorer, so the rows in a table are comparable. Metric definitions come from `../charter/methodology.md` and that document wins wherever this code and it disagree.

**No suite has been run here.** This build had no interface keys and the environment it was built in cannot reach model interfaces, so every results row reads `not run` with the reason. Nothing in this folder is a measurement of any system, ours or anyone's. `--dry-run` exercises the whole path with a recorded synthetic fixture; its output is stamped `synthetic: true`, is written under a folder named `dry-run-fixture`, carries a `NOT-A-RESULT.md`, and is refused a figure by the leaderboard builder.

Licence: MIT. Dataset licence: CC BY 4.0.

---

## Five-minute quickstart, on your own documents

You need Python 3.11 and about five minutes. Nothing below reaches a network until step 5, and step 5 is the only step that costs money.

### 1. Install

```bash
cd 10-benchmarks/harness
pip install -e .
```

If your Python is managed by the system package manager, add `--break-system-packages`.

Check it:

```bash
entail-bench --version
entail-bench list-models
```

`list-models` prints every system the harness can score, the environment variable each one reads, and whether it is available right now. A model whose variable is absent shows `not run` with the reason. No key is stored in this package.

### 2. Put your documents where the harness can find them

A dataset folder holds two things:

```
their-folder/
  ground-truth.jsonl        one JSON object per document
  documents/<doc_id>/       the page images, and a PDF if you have one
```

One line of `ground-truth.jsonl` per document. The minimum is `doc_id`, `schema` and `fields`; everything else is optional and improves the report:

```json
{
  "doc_id": "acme-inv-0001",
  "doc_type": "invoice",
  "doc_subtype": "invoice_us",
  "tier": 3,
  "languages": ["en"],
  "page_count": 1,
  "display_formats": {"date": "%m/%d/%Y", "decimal_separator": "."},
  "schema": {"invoice_number": "string", "invoice_date": "date",
             "currency": "string", "invoice_total": "money",
             "line_items": "line_items"},
  "fields": {"invoice_number": "INV-1001", "invoice_date": "2026-01-15",
             "currency": "USD", "invoice_total": "1300.00",
             "line_items": [{"sl": 1, "description": "Widget", "uom": "NOS",
                             "quantity": "10", "unit_price": "100.00",
                             "amount": "1000.00"}]},
  "render": {"pages": [{"page": 1, "path": "documents/acme-inv-0001/page-01.jpg"}]}
}
```

Field types the scorer knows: `identifier`, `string`, `date`, `money`, `rate`, `number`, `bool`, `enum`, `line_items`. The match rule each type gets is in `src/entail_bench/data/field-rules.yaml`, which is published with the harness so you can check which rule scored which field.

`tier` and `languages` drive the per-tier and per-language breakdowns. If your documents have no tiers, leave `tier` out and the breakdown collapses to one row.

### 3. Point the harness at it

```bash
cp config.example.yaml entail-bench.yaml
```

Edit two lines:

```yaml
dataset: ./their-folder
split: null
```

Or skip the file and pass `--dataset ./their-folder` on the command line.

### 4. Check it before you spend anything

```bash
entail-bench validate-config
```

This reads your dataset, counts the documents, prints the tier and language mix, hashes the prompt, and tells you which models are available and which will be recorded `not run`. It calls nothing.

Then prove the whole path runs, with no network and no key:

```bash
entail-bench run --dry-run --dataset ./their-folder --runs 3
```

That writes a full report from a recorded synthetic fixture. Read it. Every table you will get from a real run is in it, and every figure in it is an artefact of the fixture, not a measurement.

### 5. Run a model

Set the key for the model you want, as an environment variable. Then:

```bash
export OPENAI_API_KEY=...
entail-bench run --suite messy-scan --model openai --model-id <the model you are scoring> \
  --dataset ./their-folder --runs 3 --max-spend 25.00
```

Three runs, because a single-run figure is never published (charter 3.1.4). `--max-spend` stops the run when the projected cost would exceed the cap; it needs a verified price in `prices.yaml`, which ships empty on purpose. See "Cost" below.

The results land in:

```
results/<suite>-v<dataset version>/<model>/<timestamp>/
  report.md              the tables, the prompt in full, and how to reproduce it
  aggregate.json         three-run mean, standard deviation, minimum, maximum
  provenance.json        dataset version and hash, harness commit, prompt hash, command
  cost.json  spend.json  cost per document, running totals, the cap
  run-1/ run-2/ run-3/   raw/responses.jsonl and scored.json for each run
  charts/*.png           the charts
```

Open `report.md`. That is the deliverable.

### 6. Re-score or rebuild without paying again

```bash
entail-bench score  --run-dir results/messy-scan-v1.0.0/openai/<timestamp> --threshold 0.9
entail-bench report --run-dir results/messy-scan-v1.0.0/openai/<timestamp>
entail-bench report --suite-dir results/messy-scan-v1.0.0        # index across models
```

Raw responses are retained, so a disputed figure can be re-scored at a different threshold without re-running the model.

---

## Environment variables, per adapter

Every adapter reads its credential from an environment variable. When the variable is absent the adapter reports itself unavailable, the run records that model as `not run` with the reason, and no figure is written. It never falls back to a stub, and a stub result is never written into a results file. No key is hard-coded anywhere in this package, and no key value is ever written into a results folder: request and response payloads are redacted before they are stored.

| Model name | What it is | Required | Optional |
|---|---|---|---|
| `openai` | OpenAI chat completions | `OPENAI_API_KEY` | — |
| `anthropic` | Anthropic messages | `ANTHROPIC_API_KEY` | — |
| `google` | Google Gemini generateContent | `GOOGLE_API_KEY` | — |
| `mistral` | Mistral chat completions | `MISTRAL_API_KEY` | — |
| `local-vllm` | vLLM, OpenAI-compatible | `LOCAL_OPENAI_BASE_URL` | `LOCAL_OPENAI_API_KEY` |
| `local-ollama` | Ollama, OpenAI-compatible | `LOCAL_OPENAI_BASE_URL` | `LOCAL_OPENAI_API_KEY` |
| `aws-textract` | Textract AnalyzeDocument | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | `AWS_REGION`, `AWS_SESSION_TOKEN` |
| `azure-document-intelligence` | Azure AI Document Intelligence | `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY` | — |
| `google-document-ai` | Google Document AI | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_DOCAI_PROCESSOR` | `GOOGLE_DOCAI_PROJECT`, `GOOGLE_DOCAI_LOCATION` |
| `http-endpoint` | Any IDP vendor, over HTTP | `ENTAIL_HTTP_ENDPOINT_URL` | `ENTAIL_HTTP_ENDPOINT_TOKEN` |
| `entail-pipeline` | Our own pipeline, same adapter | `ENTAIL_HTTP_ENDPOINT_URL` | `ENTAIL_HTTP_ENDPOINT_TOKEN` |
| `dry-run-fixture` | Recorded synthetic fixture | none | — |

For a self-hosted server the required variable is the base URL, because that is the piece without which the adapter cannot run; a key is optional, since a local server often has none.

Two adapters need a client package that is not installed by default:

```bash
pip install 'entail-bench[aws]'    # boto3, for Textract
pip install 'entail-bench[gcp]'    # google-cloud-documentai
```

Without them the adapter reports itself unavailable with that reason, which is recorded as `not run` in the same way.

### Scoring your own pipeline, or any IDP vendor

`http-endpoint` posts the same prompt and the same page images to a URL of yours and scores the reply by exactly the code that scores a hosted model. The contract is at the top of `src/entail_bench/adapters/http_endpoint.py`. In short: you receive `{doc_id, doc_type, doc_subtype, page_count, schema, prompt, pages[]}` and reply with `{fields, confidence}`, optionally with `model_version`, `pages_billed` and `tokens`.

---

## What the harness measures

Definitions are in `../charter/methodology.md`. Each one states its numerator, its denominator and its exclusions, and the harness carries all three into the report.

| Measure | Section | Note |
|---|---|---|
| Field-level accuracy | 3.3 | Correct field instances over instances assessed. The denominator holds every ground-truth instance **plus** every returned instance with no counterpart, so accuracy cannot be raised by inventing fields or by returning fewer |
| Straight-through-processing rate | 3.4 | Documents released with no human touch, over documents admitted. Zero human touch, not "little" |
| Exception rate | 3.5 | Documents that entered review, over the same denominator. The harness asserts that the two rates sum to one |
| Expected calibration error | 3.6 | Ten equal-width bins by default, with the reliability diagram and the accuracy of instances at confidence 0.95 and above |
| Cost per document | 3.7 | From `prices.yaml`, at list prices on a stated date |
| Latency | 3.8 | p50, p95 and p99 by nearest rank, with the population size, reported with and without rate-limit backoff |

Reported overall, per tier, per language, per document type and per field, as a three-run mean with the sample standard deviation and the minimum and maximum.

### Match rules

One shared normalisation function, applied identically to every system's output. There is no per-model post-processing anywhere in this package.

- **Identifiers and codes:** exact, after Unicode NFKC and an outer whitespace strip. Case is kept.
- **Dates:** compared as ISO 8601 calendar dates. `15/01/2026`, `2026-01-15` and `15 January 2026` are the same date. One day out is wrong; there is no date tolerance.
- **Amounts:** a numeric value plus a currency code, with separators, symbols and whitespace removed. `₹4,83,265.00` and `483265.00` agree. By default a money value returned with no currency anywhere in the reply is incorrect, and the count of those instances is reported; set `scoring.currency_required: false` to score the number alone and have it flagged instead.
- **Names:** case, punctuation, diacritics, honorifics and multiple spaces normalised.
- **Free text:** scored under a stated tolerance rule and **reported separately** from the exact and normalised classes, as the charter requires. The rule is printed in every report.
- **Absent fields:** a field the ground truth marks absent is correct only if the system returns an explicit null or empty value. A key the system omitted is not.

Field-name to class mapping, the excluded line-item cells and the cross-field validation rules are in `src/entail_bench/data/field-rules.yaml`. The shared key-alias table, which maps a vendor's own field names onto your schema and is applied to every system identically, is in `src/entail_bench/data/field-aliases.yaml`.

### The review queue

The harness simulates the queue codes from `../../06-delivery/build-standards.md` section 7.1, so that the straight-through and exception figures mean what they mean in production:

| Code | Raised when |
|---|---|
| `LOWCONF` | Any assessed field's confidence is below `scoring.confidence_threshold` |
| `VALFAIL` | A schema field is missing, or a published cross-field rule fails |
| `FAIL` | The document failed to process: an unparseable reply, or retries exhausted |
| `AUDIT` | A sampled-audit draw whose reviewer changed the output |
| `FLAG`, `DRIFT` | Not generated by the benchmark; carried for parity with production and reported as zero |

The exception rate is a function of the threshold and moves the moment the threshold does, so the threshold in force is printed with every exception figure.

---

## Prompts

`prompts/messy-scan-v1.0.0.md`. One file per suite, versioned in the filename, identical for every model. Every report prints the prompt in full and records its SHA-256, taken over the file before any placeholder is filled. Each document's rendered prompt is stored with that document's raw response.

The only permitted differences between models are the mechanical requirements of an interface — where a system instruction goes, how an image is encoded, the maximum output tokens, whether a structured-output mode is used. Every such difference is listed per model in the report under "interface differences".

---

## Cost

`prices.yaml` ships with **every figure empty and marked as a list price to verify**, and no price list date. Nothing in it was read from a provider's page and nothing was invented to look plausible. Until a person fills it in, cost per document is reported `not priced` with the reason, and a spend cap cannot be enforced.

To fill it in: open the provider's published price page, copy the list price into the row, record the page URL in `source_url` and the date you read it in `verified_on`, set `verified: true`, and set `price_list_date` at the top. The report prints all of that beside every cost figure.

Cost includes input, output and separately billed reasoning tokens, per-page and per-request charges for document services, the charges for retries and repeated calls, and, for a self-hosted model, the compute rate multiplied by the measured occupancy. It excludes human review labour, one-off build and integration cost, the cost of running the harness, and any negotiated or committed-use rate.

### Spend control

`--max-spend 25.00`, or `spend_cap: 25.00` in the config. Before each document the harness compares the running total plus a projection for the documents not yet processed against the cap, and stops the run if the projection would exceed it. The projection's basis is written down beside it; it is a control figure, not a result, and it never enters a results table. Running totals are written to `spend.json` in the run folder and to `run-N/spend.json` per run. A run stopped by the cap is marked incomplete, the documents it did not reach are counted as not attempted, and it is not promoted into a headline table.

If a cap is set and the price for that model is not verified, the run stops before the first call and says so. That is deliberate: a cap that cannot be computed is not a cap.

---

## Reproducibility

Every report records the dataset version and content hash, the harness version and commit hash (and whether the working tree was clean), the prompt file and its SHA-256, the model version string as the provider reported it, the run date in UTC, the price list date, the scoring settings, and the exact command line. Raw responses are retained so a disputed figure can be re-scored without re-running the model.

---

## Charts

PNG, in the brand marks: extraction yellow `#F5E9A0` for the automated share, review red `#B8321A` for the human-reviewed share, rule grey `#B7BEC3` hairlines, IBM Plex Sans where it is installed and a stated fallback where it is not. One baseline, no other gridlines, no shadows, no gradients.

A chart for a model that was not run renders an explicit empty state reading "not run" with the reason. It never renders sample bars.

---

## Tests

```bash
pip install 'entail-bench[dev]'
pytest
```

Everything runs with no network and no key. The suite covers the scorer's edge cases (missing field, extra field, extra line-item row, near-match dates, currency formatting, Unicode variants, empty response, malformed JSON), the adapter contract for every adapter driven by recorded fixtures, the calibration and cost arithmetic, the `not run` path, the spend cap, and an end-to-end `--dry-run` over the 50-document public sample that produces a report.

Every fixture in `tests/fixtures/` is synthetic and is labelled as such in `tests/fixtures/README.md`. Nothing there is a recording of a real provider call or a real measurement.

---

## Adding a model

Add a row to `src/entail_bench/data/models.yaml` naming an adapter and the environment variables it reads. If it speaks an existing shape — OpenAI chat completions, or the generic HTTP contract — that is the whole change. A new provider shape is a subclass with `_build_request` and `_parse_response`; splitting those two is what lets the contract tests drive it from a recorded fixture with no network.

Adding an adapter is a minor harness version. Changing a scoring rule, the field-rules file or the alias table can move a figure, so it is a major version (charter 7.1).

---

## What a person has to supply

None of this can be produced by the harness, and the charter says so in section 10.3:

- an interface key per provider, and the client packages for Textract and Document AI;
- a decision on which model version is in scope for each provider, since the harness sets no default model identifier;
- the list prices, read from each provider's own page, with the date;
- a spend cap per provider, set before the run;
- an account whose rate limits allow three runs over the full set.
