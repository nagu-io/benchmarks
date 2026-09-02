# Test fixtures — all synthetic

**Every file in this folder is synthetic and was written by hand for the tests.**

No fixture here is a recording of a real provider call, a real document, a real
model output or a real measurement. The values are chosen to exercise a branch of
the code, not to resemble anything a provider would return in production.

Nothing here is a result. Charter section 3.1.8 and section 10.4: a figure that
has not been produced by a run is written `not run` with the reason, and it is
never estimated, extrapolated, illustrated or filled with a plausible-looking
figure — not in a table, not in a chart, and not in a code fixture a reader
could mistake for a result.

## What is in here

| File | What it exercises |
|---|---|
| `openai-response.json` | The OpenAI-shaped chat-completions payload: choices, message content, usage |
| `openai-malformed.json` | A reply whose content is not valid JSON, so the FAIL branch runs |
| `anthropic-response.json` | The Anthropic messages payload: content blocks, usage |
| `google-response.json` | The Gemini payload: candidates, parts, usageMetadata |
| `mistral-response.json` | The Mistral payload, which is the OpenAI shape |
| `local-openai-response.json` | A self-hosted OpenAI-compatible server, no JSON mode |
| `aws-textract-response.json` | Textract blocks: QUERY blocks with ANSWER relationships and confidences |
| `azure-di-response.json` | Document Intelligence: analyzeResult documents with typed field values |
| `google-docai-response.json` | Document AI: entities with types, mention text and confidences |
| `http-endpoint-response.json` | The generic endpoint contract: fields, confidence, tokens |
| `http-endpoint-wrapped.json` | The same contract inside a `result` wrapper |
| `tiny-dataset/` | A three-document dataset in the published ground-truth shape |
| `prices-test.yaml` | A verified price list used only by the cost tests |

`prices-test.yaml` carries numbers. They are invented for the arithmetic of the
cost tests and are marked as such inside the file. They are not a price list,
they are not quoted from any provider, and the shipped `prices.yaml` carries no
figure at all.
