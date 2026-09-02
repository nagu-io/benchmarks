# Prompts

One prompt file per suite, versioned in the filename. `messy-scan-v1.0.0.md` is the Messy Scan prompt.

Charter section 5.1 and 5.2 govern this folder.

1. The same prompt goes to every model. There is no private prompt and no per-model variant.
2. The only permitted differences between models are the mechanical requirements of an interface: where a system instruction is placed, how an image is encoded, the maximum output tokens, and whether a structured-output mode is used where the interface has one. Every such difference is listed per model in the report, under "interface differences".
3. Every report prints the prompt in full and records its SHA-256. The hash is taken over the file as it sits here, before any placeholder is filled.
4. Placeholders are filled from the item, not from the model. `{{DOCUMENT_TYPE}}`, `{{DOCUMENT_SUBTYPE}}`, `{{PAGE_COUNT}}` and `{{FIELD_SCHEMA}}` come from the dataset record and are rendered identically for every model. The rendered prompt for each document is stored in that run's raw responses, so a reader can check it.
5. A change to a prompt file is a new version file, not an edit in place. A result names the prompt file and hash that produced it, and a table never mixes two prompt hashes.

## Adding a suite

Add `<suite>-v<version>.md`, and set `prompt:` in the config to that filename. The harness reads no prompt from anywhere else.
