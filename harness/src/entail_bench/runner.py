"""The run loop: admission, calls, spend control, scoring, report.

Output layout, one folder per invocation:

    results/<suite>-v<dataset version>/<model>/<timestamp>/
        provenance.json      dataset, harness commit, prompt hash, run date, command
        run-1/raw/responses.jsonl    raw responses, retained for re-scoring
        run-1/scored.json            the scored run
        run-2/…  run-3/…
        aggregate.json       three-run mean, standard deviation, minimum, maximum
        cost.json            cost per document, or `not priced` with the reason
        spend.json           running totals and the cap
        report.md            the Markdown table and the prompt in full
        charts/*.png         the charts in the brand marks
        not-run.json         written instead of the above when a model is not run
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .adapters import Adapter, build_adapter, get_spec, is_synthetic
from .adapters.base import Response
from .aggregate import aggregate_runs
from .config import Config
from .cost import PriceList, SpendTracker, cost_report, document_cost, load_prices
from .dataset import Dataset, Document, load_dataset
from .errors import AdapterUnavailable, ReconciliationError, SpendCapReached
from .fieldrules import load_field_rules
from .prompts import Prompt, default_prompt_name, load_prompt
from .report import write_charts, write_report
from .repro import command_line, provenance
from .scoring import Admission, ScoringSettings, score_run
from .util import append_jsonl, iso_now, redact, timestamp_slug, write_json

NOT_A_RESULT = """# Not a result

This folder holds the output of `entail-bench run --dry-run`.

No model was called. The responses were produced by the recorded synthetic
fixture at `src/entail_bench/data/dry-run-fixture.yaml`, which spoils field
values on a fixed arithmetic cycle: every seventh instance is replaced with a
marker string, every eleventh is dropped. Every number in this folder is an
artefact of that cycle.

It measures no system. It is not ours, it is not anyone's, and it belongs in no
table. It exists to prove the harness runs end to end with no network and no key.

Charter section 3.1.8 and section 10.4.
"""


@dataclass
class RunOutcome:
    model: str
    run_dir: Path
    status: str                     # complete | incomplete | not run | stopped
    reason: str | None = None
    report_path: Path | None = None
    aggregate: dict | None = None
    synthetic: bool = False


def suite_folder(suite: str, dataset: Dataset) -> str:
    return f"{suite}-v{dataset.version}"


def admit(dataset: Dataset, config: Config) -> tuple[list[Document], Admission]:
    """Apply the named pre-processing rules. Both counts are reported."""
    admitted: list[Document] = []
    rejected: list[dict] = []
    for document in dataset:
        rule = next((r for r in config.reject_rules if r.matches(document)), None)
        if rule:
            rejected.append({"doc_id": document.doc_id, "rule": rule.name})
        else:
            admitted.append(document)
    return admitted, Admission(received=len(dataset.documents), rejected=rejected)


def run_model(
    config: Config,
    model: str,
    *,
    model_id: str | None = None,
    runs: int | None = None,
    out_root: Path | None = None,
    max_spend: str | None = None,
    dry_run: bool = False,
    progress: Callable[[str], None] | None = None,
    transport=None,
) -> RunOutcome:
    say = progress or (lambda _msg: None)
    runs = runs or config.runs
    dataset = load_dataset(
        config.resolve(config.dataset), split=config.split, limit=config.limit,
        require_rendered=not dry_run,
    )
    prompt = load_prompt(
        config.prompt or default_prompt_name(config.suite),
        directory=config.prompt_directory(),
    )
    prices = load_prices(config.resolve(config.prices))
    rules = load_field_rules()
    spec = get_spec(model)
    synthetic = is_synthetic(model)

    out_root = Path(out_root) if out_root else config.resolve(config.out)
    run_dir = out_root / suite_folder(config.suite, dataset) / model / timestamp_slug()
    run_dir.mkdir(parents=True, exist_ok=True)
    if synthetic:
        (run_dir / "NOT-A-RESULT.md").write_text(NOT_A_RESULT, encoding="utf-8")

    prov = provenance(
        suite=config.suite,
        dataset_summary=dataset.summary(),
        prompt_name=prompt.name,
        prompt_sha256=prompt.sha256,
        model=model,
        model_id=model_id or spec.model_id,
        model_version=None,
        price_list_date=prices.price_list_date,
        settings=config.scoring.as_dict(),
        field_rules={
            "field_rules_version": rules.version,
            "field_rules_sha256": rules.source_sha256,
        },
        command=command_line(),
        extra={
            "runs_requested": runs,
            "synthetic": synthetic,
            "is_result": not synthetic,
            "adapter": spec.adapter,
            "provider": spec.provider,
            "environment_variables_read": list(spec.env_vars),
        },
    )

    adapter = build_adapter(model, model_id=model_id, options=config.adapter_options,
                            transport=transport)
    availability = adapter.availability()
    if not availability.available:
        return _write_not_run(
            run_dir, config, prov, prompt, model, availability.reason,
            availability.env_var, dataset, say,
        )

    cap = Decimal(str(max_spend)) if max_spend is not None else config.spend_cap_decimal()
    if cap is not None and not prices.is_verified(spec.price_key):
        reason = (
            f"a spend cap of {cap} {prices.currency} is set, but "
            f"{prices.unverified_reason(spec.price_key)}, so the projected cost "
            "cannot be computed and the cap cannot be enforced. Fill in "
            "prices.yaml from the provider's published page, or remove the cap."
        )
        return _write_not_run(run_dir, config, prov, prompt, model, reason, None, dataset, say)

    scored_runs: list[dict] = []
    cost_blocks: list[dict] = []
    spend_states: list[dict] = []
    model_version: str | None = None
    stopped_reason: str | None = None

    for index in range(1, runs + 1):
        say(f"{model}: run {index} of {runs}")
        sub_dir = run_dir / f"run-{index}"
        adapter.begin_run(index)
        try:
            scored, cost_block, spend, version = _one_run(
                dataset, config, adapter, prompt, prices, spec.price_key,
                sub_dir, cap, say,
            )
        except ReconciliationError as exc:
            write_json(sub_dir / "reconciliation-failure.json", {
                "run": index, "error": str(exc), "when": iso_now(),
                "basis": "charter 3.1.2: the harness fails a run whose reported "
                         "counts do not reconcile with the manifest",
            })
            raise
        except SpendCapReached as exc:
            stopped_reason = str(exc)
            say(f"{model}: {stopped_reason}")
            break
        scored_runs.append(scored)
        cost_blocks.append(cost_block)
        spend_states.append(spend)
        model_version = version or model_version

    prov["model"]["model_version_reported"] = model_version
    aggregate = aggregate_runs(scored_runs, requested_runs=runs,
                               not_run_reason=stopped_reason)
    if stopped_reason:
        aggregate["stopped_by_spend_cap"] = stopped_reason
        aggregate["publishable"] = False
        aggregate["publishable_reason"] = (
            "the run stopped on the spend cap, so it is incomplete and is not "
            "promoted into a headline table (charter 5.8)"
        )
    aggregate["synthetic"] = synthetic
    aggregate["is_result"] = not synthetic

    write_json(run_dir / "provenance.json", prov)
    write_json(run_dir / "aggregate.json", aggregate)
    if cost_blocks:
        write_json(run_dir / "cost.json",
                   {"runs": cost_blocks, "synthetic": synthetic, "is_result": not synthetic})
    if spend_states:
        write_json(run_dir / "spend.json",
                   {"runs": spend_states, "synthetic": synthetic})

    chart_files = write_charts(
        run_dir, aggregate=aggregate, runs=scored_runs,
        cost=cost_blocks[0] if cost_blocks else None,
        model=model, suite=config.suite, synthetic=synthetic,
    )
    report_path = write_report(
        run_dir,
        aggregate=aggregate,
        provenance=prov,
        runs=scored_runs,
        prompt_text=prompt.text,
        prompt_name=prompt.name,
        prompt_sha256=prompt.sha256,
        cost=cost_blocks[0] if cost_blocks else None,
        spend=spend_states[-1] if spend_states else None,
        model=model,
        synthetic=synthetic,
        interface_notes=list(adapter.interface_notes),
        chart_files=chart_files,
    )
    status = "stopped" if stopped_reason else aggregate.get("status", "not run")
    return RunOutcome(model, run_dir, status, stopped_reason, report_path, aggregate, synthetic)


def _one_run(
    dataset: Dataset,
    config: Config,
    adapter: Adapter,
    prompt: Prompt,
    prices: PriceList,
    price_key: str | None,
    sub_dir: Path,
    cap: Decimal | None,
    say,
) -> tuple[dict, dict, dict, str | None]:
    documents, admission = admit(dataset, config)
    spend = SpendTracker(cap=cap, currency=prices.currency, documents_total=len(documents))
    responses: dict[str, Response] = {}
    raw_path = sub_dir / "raw" / "responses.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    per_document_cost: list[Decimal | None] = []
    unpriced_reasons: list[str] = []
    model_version: str | None = None
    stopped = False

    for position, document in enumerate(documents):
        if stopped:
            admission.not_attempted.append({
                "doc_id": document.doc_id,
                "reason": "the run stopped on the spend cap before this document",
            })
            continue
        response = adapter.extract(document, prompt)
        responses[document.doc_id] = response
        model_version = response.model_version or model_version

        cost, reason = document_cost(
            prices, price_key,
            tokens=response.tokens.as_dict(),
            pages_billed=response.pages_billed,
            requests=response.requests,
            elapsed_s=response.latency_s,
        )
        per_document_cost.append(cost)
        if reason and reason not in unpriced_reasons:
            unpriced_reasons.append(reason)
        spend.record(document.doc_id, cost, reason)

        record = response.as_dict()
        record["rendered_prompt"] = prompt.render(document)
        record["prompt_sha256"] = prompt.sha256
        record["position"] = position
        append_jsonl(raw_path, redact(record))

        try:
            spend.check()
        except SpendCapReached:
            stopped = True
            for remaining in documents[position + 1:]:
                admission.not_attempted.append({
                    "doc_id": remaining.doc_id,
                    "reason": "the run stopped on the spend cap before this document",
                })
            write_json(sub_dir / "spend.json", spend.as_dict())
            raise

    scored = score_run(dataset, responses, config.scoring, admission)
    cost_block = cost_report(
        prices, price_key,
        per_document=per_document_cost,
        unpriced_reasons=unpriced_reasons,
        documents_admitted=admission.admitted,
        pages_total=sum(d.page_count for d in documents),
    )
    write_json(sub_dir / "scored.json", scored)
    write_json(sub_dir / "cost.json", cost_block)
    write_json(sub_dir / "spend.json", spend.as_dict())
    return scored, cost_block, spend.as_dict(), model_version


def _write_not_run(
    run_dir: Path,
    config: Config,
    prov: dict,
    prompt: Prompt,
    model: str,
    reason: str,
    env_var: str | None,
    dataset: Dataset,
    say,
) -> RunOutcome:
    """Record the model as `not run` with the reason. Never a stub."""
    say(f"{model}: not run — {reason}")
    not_run = {
        "model": model,
        "status": "not run",
        "reason": reason,
        "env_var": env_var,
        "when": iso_now(),
        "rule": "charter 3.1.8 and 5.8: a system that cannot complete a suite is "
                "reported as `not run` with the reason. No figure is estimated, "
                "extrapolated or stubbed in its place.",
        "documents_in_split": len(dataset),
    }
    aggregate = aggregate_runs([], requested_runs=prov.get("runs_requested", 3),
                               not_run_reason=reason)
    aggregate["synthetic"] = False
    aggregate["is_result"] = False
    write_json(run_dir / "not-run.json", not_run)
    write_json(run_dir / "provenance.json", prov)
    write_json(run_dir / "aggregate.json", aggregate)
    chart_files = write_charts(
        run_dir, aggregate=aggregate, runs=[], cost=None,
        model=model, suite=config.suite, not_run=not_run,
    )
    report_path = write_report(
        run_dir,
        aggregate=aggregate,
        provenance=prov,
        runs=[],
        prompt_text=prompt.text,
        prompt_name=prompt.name,
        prompt_sha256=prompt.sha256,
        cost=None,
        spend=None,
        model=model,
        not_run=not_run,
        chart_files=chart_files,
    )
    return RunOutcome(model, run_dir, "not run", reason, report_path, aggregate, False)


# --------------------------------------------------------------------------- #
# Re-scoring and re-reporting an existing folder                               #
# --------------------------------------------------------------------------- #


def rescore(run_dir: Path, config: Config, *, progress=None) -> list[Path]:
    """Re-score raw responses without calling any provider (charter 7.5)."""
    from .util import read_jsonl

    say = progress or (lambda _m: None)
    run_dir = Path(run_dir)
    prov_path = run_dir / "provenance.json"
    if not prov_path.exists():
        raise FileNotFoundError(f"no provenance.json in {run_dir}")
    dataset = load_dataset(
        config.resolve(config.dataset), split=config.split, limit=config.limit,
        require_rendered=False,
    )
    written: list[Path] = []
    scored_runs: list[dict] = []
    for sub_dir in sorted(run_dir.glob("run-*")):
        raw = sub_dir / "raw" / "responses.jsonl"
        if not raw.exists():
            continue
        responses = {}
        for record in read_jsonl(raw):
            responses[record["doc_id"]] = Response.from_dict(record)
        documents, admission = admit(dataset, config)
        missing = [d.doc_id for d in documents if d.doc_id not in responses]
        for doc_id in missing:
            admission.not_attempted.append(
                {"doc_id": doc_id, "reason": "no raw response recorded for this document"}
            )
        scored = score_run(dataset, responses, config.scoring, admission)
        write_json(sub_dir / "scored.json", scored)
        scored_runs.append(scored)
        written.append(sub_dir / "scored.json")
        say(f"re-scored {sub_dir.name}: {len(responses)} responses")
    if scored_runs:
        aggregate = aggregate_runs(scored_runs,
                                   requested_runs=len(list(run_dir.glob("run-*"))))
        prov = _read_json(prov_path)
        aggregate["synthetic"] = bool(prov.get("synthetic"))
        aggregate["is_result"] = not bool(prov.get("synthetic"))
        write_json(run_dir / "aggregate.json", aggregate)
        written.append(run_dir / "aggregate.json")
    return written


def rebuild_report(run_dir: Path, config: Config) -> Path:
    """Rebuild report.md and the charts from the scored JSON already on disk."""
    from .util import read_jsonl  # noqa: F401  (kept for symmetry)

    run_dir = Path(run_dir)
    prov = _read_json(run_dir / "provenance.json")
    aggregate = _read_json(run_dir / "aggregate.json")
    not_run = _read_json(run_dir / "not-run.json") if (run_dir / "not-run.json").exists() else None
    scored_runs = [
        _read_json(p / "scored.json") for p in sorted(run_dir.glob("run-*"))
        if (p / "scored.json").exists()
    ]
    cost_path = run_dir / "cost.json"
    cost = None
    if cost_path.exists():
        blocks = _read_json(cost_path).get("runs") or []
        cost = blocks[0] if blocks else None
    spend_path = run_dir / "spend.json"
    spend = None
    if spend_path.exists():
        states = _read_json(spend_path).get("runs") or []
        spend = states[-1] if states else None

    prompt = load_prompt(
        config.prompt or default_prompt_name(prov.get("suite", config.suite)),
        directory=config.prompt_directory(),
    )
    model = (prov.get("model") or {}).get("name", run_dir.parent.name)
    synthetic = bool(prov.get("synthetic"))
    chart_files = write_charts(
        run_dir, aggregate=aggregate, runs=scored_runs, cost=cost,
        model=model, suite=prov.get("suite", config.suite),
        not_run=not_run, synthetic=synthetic,
    )
    return write_report(
        run_dir,
        aggregate=aggregate,
        provenance=prov,
        runs=scored_runs,
        prompt_text=prompt.text,
        prompt_name=prov.get("prompt", {}).get("file", prompt.name),
        prompt_sha256=prov.get("prompt", {}).get("sha256", prompt.sha256),
        cost=cost,
        spend=spend,
        model=model,
        not_run=not_run,
        synthetic=synthetic,
        interface_notes=None,
        chart_files=chart_files,
    )


def build_index(suite_dir: Path) -> Path:
    """An index across every model under one suite folder.

    A run stamped synthetic is listed with its status and is never given a
    figure column, so a dry run cannot leak into a leaderboard.
    """
    suite_dir = Path(suite_dir)
    rows: list[tuple[str, str, str, str, str]] = []
    for model_dir in sorted(p for p in suite_dir.iterdir() if p.is_dir()):
        latest = sorted(p for p in model_dir.iterdir() if p.is_dir())
        if not latest:
            continue
        newest = latest[-1]
        prov = _read_json(newest / "provenance.json") if (newest / "provenance.json").exists() else {}
        aggregate = _read_json(newest / "aggregate.json") if (newest / "aggregate.json").exists() else {}
        if aggregate.get("synthetic"):
            rows.append((model_dir.name, "synthetic dry run, not a result",
                         "—", "—", newest.name))
            continue
        status = aggregate.get("status", "not run")
        if status == "not run" or not aggregate.get("publishable"):
            reason = aggregate.get("reason") or aggregate.get("publishable_reason") or ""
            rows.append((model_dir.name, f"{status} — {reason}", "—", "—", newest.name))
            continue
        headline = aggregate.get("headline", {})
        from .util import fmt_rate
        rows.append((
            model_dir.name,
            "complete",
            fmt_rate(headline.get("straight_through_rate", {}).get("mean")),
            fmt_rate(headline.get("field_accuracy", {}).get("mean")),
            newest.name,
        ))

    lines = [
        f"# {suite_dir.name} — index",
        "",
        "One row per model under this suite folder, from the most recent run of "
        "each. A row with no run reads `not run` with the reason. A row is never "
        "estimated (charter 3.1.8), and a synthetic dry run is never given a "
        "figure.",
        "",
        "| Model | Status | Straight-through rate | Field accuracy | Run |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    if not rows:
        lines.append("| — | no run folders under this suite | — | — | — |")
    path = suite_dir / "index.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict:
    import json

    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
