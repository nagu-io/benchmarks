# Runs

One folder per system, one folder per run inside it.

```
runs/<system>/run-<n>/run.json             the run header: versions, hashes, preflight, status
runs/<system>/run-<n>/contacts.jsonl       one contact record per scenario
runs/<system>/run-<n>/scored-contacts.jsonl written by the scorer
runs/<system>/run-<n>/metrics.json          written by the scorer
```

Every folder here currently holds `not run` records. They were written by
`suite/runner.py --dry-run`, which checks every preflight and calls nothing. The reason is
in each `run.json` under `not_run_reason` and in each contact record. It is the same reason
in every case: no interface key is set, the voice-platform endpoints still read
`placeholder`, and this environment cannot reach a model interface.

`reproduce.md` has the commands that replace these files with a real run. Charter 5.4 wants
three runs per system at identical settings; only `run-1` is scaffolded here, and runs 2 and
3 are produced by the same command with `--run-index 2` and `--run-index 3`.

Raw model responses are retained per charter 7.5 so that a disputed figure can be re-scored
without re-running the model. There are none yet.
