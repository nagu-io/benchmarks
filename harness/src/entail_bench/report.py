"""Markdown reports and the charts that go with them.

Every figure carries its sample size, its dataset version, its harness version
and its run date (charter 3.1.3). Every rate is reported to one decimal place,
money to four significant figures, times to the precision of the source clock
(charter 3.1.5). A figure that has not been produced by a run is written `not
run` with the reason (charter 3.1.8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import charts as C
from .util import fmt_money, fmt_rate, fmt_ratio, fmt_seconds

SYNTHETIC_BANNER = (
    "> **This is a dry run over a recorded synthetic fixture. It is not a "
    "result.**\n>\n"
    "> No model was called. Every figure below is an artefact of the fixed "
    "arithmetic cycle in `src/entail_bench/data/dry-run-fixture.yaml` and of "
    "nothing else. It measures no system, ours or anyone's. It exists to prove "
    "the harness runs end to end. Nothing here may be quoted, charted outside "
    "this folder, or entered into a leaderboard.\n"
)


def _pm(spread: dict, formatter, *, unit: str = "") -> str:
    """A three-run figure as mean, then the spread beside it."""
    if not spread or spread.get("mean") is None:
        return "not run"
    mean = formatter(spread["mean"])
    sd = spread.get("sd")
    lo, hi = spread.get("min"), spread.get("max")
    if sd is None:
        return f"{mean} (1 run)"
    return (
        f"{mean} · sd {formatter(sd)} · min {formatter(lo)} · max {formatter(hi)} "
        f"(n={spread.get('runs_with_a_figure')})"
    )


def _rate(v):
    return fmt_rate(v)


def _secs(v):
    return fmt_seconds(v)


def _ece(v):
    return fmt_ratio(v, 4)


def write_report(
    run_dir: Path,
    *,
    aggregate: dict,
    provenance: dict,
    runs: list[dict],
    prompt_text: str,
    prompt_name: str,
    prompt_sha256: str,
    cost: dict | None,
    spend: dict | None,
    model: str,
    not_run: dict | None = None,
    synthetic: bool = False,
    interface_notes: list[str] | None = None,
    chart_files: list[str] | None = None,
) -> Path:
    lines: list[str] = []
    add = lines.append

    add(f"# {provenance['suite']} — {model}")
    add("")
    if synthetic:
        add(SYNTHETIC_BANNER)
        add("")
    if not_run:
        add("## Status: not run")
        add("")
        add(f"**Reason.** {not_run.get('reason')}")
        add("")
        add(
            "Charter section 3.1.8: a figure that has not been produced by a run "
            "is written `not run` with the reason. It is never estimated, "
            "extrapolated, interpolated from a neighbouring tier, or replaced "
            "with a plausible-looking figure, in a table, a chart, a code fixture "
            "or a sentence."
        )
        add("")
        if not_run.get("env_var"):
            add(
                f"To run this row, set `{not_run['env_var']}` in the environment "
                "and repeat the command below."
            )
            add("")
    else:
        add(_status_line(aggregate))
        add("")

    add(_provenance_block(provenance, prompt_name, prompt_sha256))
    add("")

    if not not_run:
        add(_headline_table(aggregate, cost, runs))
        add("")
        add(_counts_table(runs))
        add("")
        add(_tier_table(aggregate, runs))
        add("")
        add(_language_table(aggregate))
        add("")
        add(_exception_table(runs))
        add("")
        add(_calibration_block(runs, aggregate))
        add("")
        add(_latency_block(aggregate, runs))
        add("")
        add(_cost_block(cost, spend))
        add("")
        add(_field_table(aggregate))
        add("")
        add(_exclusions_block(runs))
        add("")

    if interface_notes:
        add("## Interface differences")
        add("")
        add(
            "Charter section 5.2 permits only the mechanical requirements of an "
            "interface to differ between models. Every difference for this "
            "system is listed here."
        )
        add("")
        for note in interface_notes:
            add(f"- {note}")
        add("")

    if chart_files:
        add("## Charts")
        add("")
        add(f"Typeface: {C.font_note()}.")
        add("")
        for name in chart_files:
            add(f"- `charts/{name}`")
        add("")

    add("## Prompt")
    add("")
    add(
        f"File `prompts/{prompt_name}`, SHA-256 `{prompt_sha256}`. The same "
        "prompt goes to every model. The hash is taken over the file before any "
        "placeholder is filled; each document's rendered prompt is stored with "
        "that document's raw response."
    )
    add("")
    add("```text")
    add(prompt_text.rstrip("\n"))
    add("```")
    add("")

    add("## Reproduce")
    add("")
    add("```bash")
    add(provenance.get("command", "entail-bench run --suite messy-scan"))
    add("```")
    add("")

    path = run_dir / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Blocks                                                                       #
# --------------------------------------------------------------------------- #


def _status_line(aggregate: dict) -> str:
    status = aggregate.get("status")
    if status == "complete":
        return (
            f"Status: complete. {aggregate['runs_completed']} runs at identical "
            "settings. Every figure below is the mean of those runs, with the "
            "sample standard deviation and the minimum and maximum beside it."
        )
    if status == "incomplete":
        return (
            f"Status: **incomplete**. {aggregate['runs_completed']} of "
            f"{aggregate['runs_requested']} runs completed. "
            f"{aggregate.get('publishable_reason')}"
        )
    return f"Status: **not run**. {aggregate.get('reason')}"


def _provenance_block(prov: dict, prompt_name: str, prompt_sha: str) -> str:
    dataset = prov.get("dataset") or {}
    commit = prov.get("harness_commit") or {}
    rows = [
        ("Dataset", f"{dataset.get('dataset')} v{dataset.get('dataset_version')}"),
        ("Dataset content hash", f"`{dataset.get('ground_truth_sha256')}`"),
        ("Documents in the scored split", str(dataset.get("documents"))),
        ("Harness version", prov.get("harness_version")),
        ("Harness commit", f"`{commit.get('commit')}`" if commit.get("commit") else "not recorded"),
        ("Working tree clean at run start",
         "yes" if commit.get("clean") else ("no" if commit.get("clean") is False else "not recorded")),
        ("Prompt", f"`{prompt_name}` sha256 `{prompt_sha}`"),
        ("Model name", (prov.get("model") or {}).get("name")),
        ("Model identifier requested", (prov.get("model") or {}).get("model_id_requested") or "not set"),
        ("Model version reported by the provider",
         (prov.get("model") or {}).get("model_version_reported") or "not run"),
        ("Run date, UTC", prov.get("run_date_utc")),
        ("Price list date", prov.get("price_list_date") or "not set"),
        ("Match rules", f"field-rules v{(prov.get('match_rules') or {}).get('field_rules_version')} "
                        f"sha256 `{(prov.get('match_rules') or {}).get('field_rules_sha256', '')[:16]}…`"),
        ("Confidence threshold", str((prov.get("scoring_settings") or {}).get("confidence_threshold"))),
        ("Calibration bins", str((prov.get("scoring_settings") or {}).get("calibration_bins"))),
        ("Sampled-audit rate", str((prov.get("scoring_settings") or {}).get("audit_rate"))),
        ("Python", prov.get("python")),
    ]
    out = ["## Reproducibility", "", "| Item | Value |", "|---|---|"]
    for name, value in rows:
        out.append(f"| {name} | {value} |")
    if commit.get("note"):
        out += ["", f"Note: {commit['note']}."]
    return "\n".join(out)


def _headline_table(aggregate: dict, cost: dict | None, runs: list[dict]) -> str:
    h = aggregate.get("headline", {})
    admitted = h.get("documents_admitted", {}).get("mean")
    cost_text = "not priced"
    if cost and cost.get("cost_per_document"):
        cost_text = fmt_money(float(cost["cost_per_document"]), cost.get("currency", "USD"))
    out = [
        "## Headline",
        "",
        "Straight-through rate is the headline column, field-level accuracy is "
        "second and cost per document is third. Straight-through rate on its own "
        "is not a result: a system that releases everything untouched scores 100 "
        "per cent and may be wrong on most of it (charter 3.4.6).",
        "",
        "| Measure | Figure | Denominator |",
        "|---|---|---|",
        f"| Straight-through-processing rate | {_pm(h.get('straight_through_rate'), _rate)} | "
        f"{int(admitted) if admitted else 'not run'} documents admitted |",
        f"| Field-level accuracy, exact and normalised classes | "
        f"{_pm(h.get('field_accuracy'), _rate)} | "
        f"{_assessed(runs)} field instances assessed |",
        f"| Cost per document | {cost_text} | "
        f"{int(admitted) if admitted else 'not run'} documents admitted |",
        f"| Exception rate | {_pm(h.get('exception_rate'), _rate)} | "
        f"{int(admitted) if admitted else 'not run'} documents admitted |",
        f"| Expected calibration error | {_pm(h.get('expected_calibration_error'), _ece)} | "
        f"{_calibrated(runs)} field instances carrying a confidence |",
        f"| Accuracy at confidence 0.95 and above | "
        f"{_pm(h.get('high_confidence_accuracy'), _rate)} | "
        f"{_high_conf_n(runs)} field instances |",
        f"| Latency, 95th percentile | {_pm(h.get('latency_p95_s'), _secs)} | "
        f"{_completed(runs)} documents completed |",
        f"| Field-level accuracy, free-text class | "
        f"{_pm(h.get('free_text_accuracy'), _rate)} | "
        f"{_free_text_n(runs)} field instances, tolerance rule stated below |",
        f"| Exact string match, no normalisation | "
        f"{_pm(h.get('field_accuracy_exact_strict'), _rate)} | "
        f"{_assessed(runs)} field instances, diagnostic |",
    ]
    if runs:
        rule = (runs[0].get("free_text_accuracy") or {}).get("tolerance_rule")
        if rule:
            out += ["", f"Free-text tolerance rule: {rule}"]
    out += ["", aggregate.get("difference_rule", "")]
    return "\n".join(out)


def _counts_table(runs: list[dict]) -> str:
    if not runs:
        return ""
    counts = runs[0].get("counts", {})
    identity = runs[0].get("identity_check", {})
    rows = [
        ("Documents received", counts.get("documents_received")),
        ("Documents rejected before processing by a named rule",
         counts.get("documents_rejected_before_processing")),
        ("Documents not attempted", counts.get("documents_not_attempted")),
        ("Documents admitted to processing", counts.get("documents_admitted_to_processing")),
        ("Documents straight through", counts.get("documents_straight_through")),
        ("Documents that entered review", counts.get("documents_exception")),
        ("Documents that failed to process", counts.get("documents_processing_failure")),
        ("Documents drawn into the sampled audit", counts.get("documents_audited")),
        ("Sampled audits that changed nothing", counts.get("documents_audited_unchanged")),
        ("Queue re-entries", counts.get("queue_re_entries")),
    ]
    out = ["## Counts, first run", "", "| Count | Documents |", "|---|---|"]
    for name, value in rows:
        out.append(f"| {name} | {value if value is not None else 'not recorded'} |")
    holds = identity.get("holds")
    out += [
        "",
        f"Identity check, charter 3.5.3: straight-through rate plus exception "
        f"rate equals one — **{'holds' if holds else 'does not hold' if holds is False else 'not run'}**.",
        "",
        f"Basis for queue re-entries: {counts.get('queue_re_entries_basis')}.",
    ]
    return "\n".join(out)


def _tier_table(aggregate: dict, runs: list[dict]) -> str:
    tiers = aggregate.get("by_tier") or {}
    if not tiers:
        return ""
    mix = (runs[0].get("tier_mix") if runs else {}) or {}
    out = [
        "## By tier",
        "",
        "Every headline figure travels with the tier mix that produced it "
        "(charter 3.1.7 and 4.1.4). A headline moves when the mix moves.",
        "",
    ]
    if mix:
        out += [
            "Tier mix in this split: "
            + ", ".join(f"T{k}: {v}" for k, v in sorted(mix.items())) + ".",
            "",
        ]
    out += [
        "| Tier | Documents | Straight-through rate | Field accuracy | Exception rate | Latency p95 | Processing failures |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, block in tiers.items():
        out.append(
            f"| {name} | {block.get('documents')} | "
            f"{_pm(block.get('straight_through_rate'), _rate)} | "
            f"{_pm(block.get('field_accuracy'), _rate)} | "
            f"{_pm(block.get('exception_rate'), _rate)} | "
            f"{_pm(block.get('latency_p95_s'), _secs)} | "
            f"{_pm(block.get('processing_failures'), lambda v: f'{v:.1f}')} |"
        )
    return "\n".join(out)


def _language_table(aggregate: dict) -> str:
    langs = aggregate.get("by_language") or {}
    if not langs:
        return ""
    out = [
        "## By language",
        "",
        "A second language on a page is a tier-5 property in this dataset. The "
        "datasheet states that the second-language text is a set of field labels "
        "and one sentence, so a per-language figure here is not a multilingual "
        "capability score.",
        "",
        "| Languages | Documents | Straight-through rate | Field accuracy | Exception rate |",
        "|---|---|---|---|---|",
    ]
    for name, block in langs.items():
        out.append(
            f"| {name} | {block.get('documents')} | "
            f"{_pm(block.get('straight_through_rate'), _rate)} | "
            f"{_pm(block.get('field_accuracy'), _rate)} | "
            f"{_pm(block.get('exception_rate'), _rate)} |"
        )
    return "\n".join(out)


def _exception_table(runs: list[dict]) -> str:
    if not runs:
        return ""
    out = [
        "## Exceptions by entry code, first run",
        "",
        "The exception rate is a function of the confidence threshold and moves "
        "the moment the threshold does (charter 3.5.6). The threshold in force is "
        "in the reproducibility table above.",
        "",
        "| Code | Documents |",
        "|---|---|",
    ]
    for code, count in (runs[0].get("exception", {}).get("by_code") or {}).items():
        out.append(f"| {code} | {count} |")
    out += [
        "",
        "`LOWCONF` low confidence · `VALFAIL` validation failure · `FAIL` "
        "processing failure · `FLAG` partner flag · `DRIFT` drift response · "
        "`AUDIT` a sampled audit that changed the output. Codes come from "
        "`06-delivery/build-standards.md` section 7.1.",
    ]
    return "\n".join(out)


def _calibration_block(runs: list[dict], aggregate: dict) -> str:
    if not runs:
        return ""
    cal = runs[0].get("calibration", {})
    h = aggregate.get("headline", {})
    out = ["## Calibration", ""]
    if cal.get("status") != "measured":
        out += [
            "**No confidence output.** " + str(cal.get("basis", "")),
            "",
            "Charter 3.6.4: a system that reports no confidence at all is "
            "reported as `no confidence output`. It is never reported as an "
            "expected calibration error of zero.",
        ]
        return "\n".join(out)
    high = cal.get("high_confidence_check", {})
    out += [
        f"Binning: {cal.get('binning')}. Unit: {cal.get('unit')}.",
        "",
        f"- Expected calibration error: {_pm(h.get('expected_calibration_error'), _ece)}",
        f"- Accuracy at confidence 0.95 and above: "
        f"{_pm(h.get('high_confidence_accuracy'), _rate)} over "
        f"{high.get('denominator')} instances",
        f"- Field instances carrying a confidence: {cal.get('instances_with_confidence')}",
        f"- Field instances with no confidence, unscored for calibration: "
        f"{cal.get('instances_without_confidence')} "
        f"({fmt_rate(cal.get('share_without_confidence'))} of assessed)",
        "",
        "Reliability diagram, first run:",
        "",
        "| Bin | Instances | Weight | Accuracy | Mean confidence | Gap | Contribution |",
        "|---|---|---|---|---|---|---|",
    ]
    for b in cal.get("reliability_diagram", []):
        if not b["instances"]:
            continue
        out.append(
            f"| {b['bin']} | {b['instances']} | {b['weight']:.3f} | "
            f"{fmt_rate(b['accuracy'])} | {b['mean_confidence']:.3f} | "
            f"{b['gap']:.3f} | {b['contribution']:.4f} |"
        )
    return "\n".join(out)


def _latency_block(aggregate: dict, runs: list[dict]) -> str:
    h = aggregate.get("headline", {})
    lat = (runs[0].get("latency") if runs else {}) or {}
    excl = lat.get("excluding_backoff", {})
    fail = lat.get("failure_times", {})
    out = [
        "## Latency",
        "",
        f"{lat.get('definition', '')} Percentiles by the nearest-rank method over "
        f"{lat.get('count')} documents that completed. A percentile over a handful "
        "of documents is one document, so the population size is printed with it.",
        "",
        "| Percentile | With backoff | Without backoff |",
        "|---|---|---|",
        f"| p50 | {_pm(h.get('latency_p50_s'), _secs)} | {fmt_seconds(excl.get('p50_s'))} |",
        f"| p95 | {_pm(h.get('latency_p95_s'), _secs)} | {fmt_seconds(excl.get('p95_s'))} |",
        f"| p99 | {_pm(h.get('latency_p99_s'), _secs)} | {fmt_seconds(excl.get('p99_s'))} |",
        f"| mean | {_pm(h.get('latency_mean_s'), _secs)} | — |",
        f"| maximum | {fmt_seconds(lat.get('max_s'))} | — |",
        "",
        f"Time in rate-limit backoff, first run: "
        f"{fmt_seconds(excl.get('total_backoff_s'))}. {excl.get('basis', '')}",
        "",
        f"Documents that failed to process: {fail.get('count')}, "
        f"p50 {fmt_seconds(fail.get('p50_s'))}, max {fmt_seconds(fail.get('max_s'))}. "
        "Their times are reported here and excluded from the percentiles above.",
        "",
        f"{lat.get('queue_age', '')}.",
    ]
    return "\n".join(out)


def _cost_block(cost: dict | None, spend: dict | None) -> str:
    out = ["## Cost per document", ""]
    if not cost:
        out.append("not run")
        return "\n".join(out)
    price = cost.get("price_list") or {}
    if cost.get("status") != "priced":
        out += [
            f"**not priced.** {cost.get('not_priced_reason')}",
            "",
            "Charter section 3.7.2 takes charges from published list prices on a "
            "stated date. `prices.yaml` ships with every figure marked as a list "
            "price to verify and none filled in, so no cost figure is produced "
            "until a person reads the prices from each provider's own page and "
            "sets `verified: true` with the date.",
        ]
    else:
        currency = cost.get("currency", "USD")
        out += [
            "| Measure | Figure |",
            "|---|---|",
            f"| Cost per document | {fmt_money(float(cost['cost_per_document']), currency)} |",
            f"| Cost per page | "
            f"{fmt_money(float(cost['cost_per_page']), currency) if cost.get('cost_per_page') else 'not recorded'} |",
            f"| Cost per thousand documents | "
            f"{fmt_money(float(cost['cost_per_thousand_documents']), currency)} |",
            f"| Total run cost | {fmt_money(float(cost['total_run_cost']), currency)} |",
            f"| Documents admitted | {cost.get('documents_admitted')} |",
            "",
            f"Price list date: {price.get('price_list_date') or 'not set'}. "
            f"Source: {price.get('source_url') or 'not recorded'}. "
            f"{price.get('basis', '')}",
        ]
    out += ["", f"Excluded: {cost.get('excluded', '')}"]
    if spend:
        out += [
            "",
            "### Spend control",
            "",
            f"- Spend cap: "
            + (f"{spend['spend_cap']} {spend.get('currency')}"
               if spend.get("spend_cap") else "not set"),
            f"- Spent: {spend.get('spent')} over {spend.get('documents_done')} documents",
            f"- Documents not priced: {spend.get('documents_not_priced')}",
            f"- Run stopped by the cap: {'yes' if spend.get('stopped') else 'no'}",
        ]
        if spend.get("stop_reason"):
            out.append(f"- Stop reason: {spend['stop_reason']}")
        out.append(f"- Projection note: {spend.get('projection_note')}")
    return "\n".join(out)


def _field_table(aggregate: dict) -> str:
    fields = aggregate.get("by_field") or {}
    if not fields:
        return ""
    out = [
        "## By field",
        "",
        "| Field | Class | Match rule | Instances assessed | Accuracy |",
        "|---|---|---|---|---|",
    ]
    for name, block in fields.items():
        out.append(
            f"| `{name}` | {block.get('class')} | {block.get('rule')} | "
            f"{block.get('assessed')} | {_pm(block.get('accuracy'), _rate)} |"
        )
    return "\n".join(out)


def _exclusions_block(runs: list[dict]) -> str:
    if not runs:
        return ""
    ex = runs[0].get("exclusions", {})
    out = [
        "## Exclusions, counted and reported",
        "",
        "Charter 3.1.2: nothing is silently dropped. Each exclusion is counted "
        "and reported beside the figure it was excluded from.",
        "",
        "| Exclusion | Count | Basis |",
        "|---|---|---|",
        f"| Returned fields outside the published schema | "
        f"{ex.get('out_of_schema_returns')} | {ex.get('out_of_schema_basis')} |",
        f"| Ground-truth instances marked unreadable | "
        f"{ex.get('unreadable_ground_truth_instances')} | "
        "Counted and reported as a separate line rather than scored. |",
        f"| Line-item cells not scored | {ex.get('line_item_cells_excluded')} | "
        f"{ex.get('line_item_cells_excluded_basis')} |",
        f"| Documents excluded from field accuracy | "
        f"{ex.get('documents_excluded_from_field_accuracy')} | "
        f"{ex.get('documents_excluded_basis')} |",
        f"| Returned keys mapped by the published alias table | "
        f"{ex.get('keys_mapped_by_alias_table')} | "
        "One shared function applied identically to every system, charter 5.3. |",
    ]
    return "\n".join(out)


# -- small helpers over the first run --------------------------------------- #


def _assessed(runs: list[dict]) -> str:
    if not runs:
        return "not run"
    return str((runs[0].get("field_accuracy") or {}).get("denominator_assessed"))


def _free_text_n(runs: list[dict]) -> str:
    if not runs:
        return "not run"
    return str((runs[0].get("free_text_accuracy") or {}).get("denominator_assessed"))


def _calibrated(runs: list[dict]) -> str:
    if not runs:
        return "not run"
    return str((runs[0].get("calibration") or {}).get("instances_with_confidence"))


def _high_conf_n(runs: list[dict]) -> str:
    if not runs:
        return "not run"
    return str(((runs[0].get("calibration") or {}).get("high_confidence_check") or {})
               .get("denominator"))


def _completed(runs: list[dict]) -> str:
    if not runs:
        return "not run"
    return str((runs[0].get("latency") or {}).get("count"))


# --------------------------------------------------------------------------- #
# Charts                                                                       #
# --------------------------------------------------------------------------- #


def write_charts(
    run_dir: Path,
    *,
    aggregate: dict,
    runs: list[dict],
    cost: dict | None,
    model: str,
    suite: str,
    not_run: dict | None = None,
    synthetic: bool = False,
) -> list[str]:
    chart_dir = run_dir / "charts"
    subtitle = f"{suite} · {model}"
    if synthetic:
        subtitle += " · synthetic dry-run fixture, not a result"
    written: list[str] = []

    def name(file: str) -> str:
        written.append(file)
        return file

    if not_run:
        reason = not_run.get("reason", "no reason recorded")
        for file, title in (
            ("straight-through-by-tier.png", "Straight-through rate by tier"),
            ("accuracy-by-tier.png", "Field-level accuracy by tier"),
            ("reliability-diagram.png", "Reliability diagram"),
            ("latency-percentiles.png", "Latency percentiles"),
            ("cost-per-document.png", "Cost per document"),
        ):
            C.empty_state(chart_dir / name(file), title, reason, subtitle=subtitle)
        return written

    tiers = aggregate.get("by_tier") or {}
    labels = list(tiers)
    if labels:
        C.stacked_share_chart(
            chart_dir / name("straight-through-by-tier.png"),
            labels,
            [tiers[l]["straight_through_rate"].get("mean") for l in labels],
            "Straight-through rate by tier",
            subtitle,
            counts=[tiers[l].get("documents") for l in labels],
            spreads=[(tiers[l]["straight_through_rate"].get("min"),
                      tiers[l]["straight_through_rate"].get("max")) for l in labels],
        )
        instances_by_tier = (runs[0].get("breakdowns", {}).get("by_tier", {}) if runs else {})
        C.accuracy_by_group_chart(
            chart_dir / name("accuracy-by-tier.png"),
            labels,
            [tiers[l]["field_accuracy"].get("mean") for l in labels],
            "Field-level accuracy by tier",
            subtitle,
            counts=[
                (instances_by_tier.get(l, {}).get("field_accuracy", {})
                 .get("denominator_assessed"))
                for l in labels
            ],
            spreads=[(tiers[l]["field_accuracy"].get("min"),
                      tiers[l]["field_accuracy"].get("max")) for l in labels],
        )

    cal = (runs[0].get("calibration") if runs else {}) or {}
    if cal.get("status") == "measured" and cal.get("reliability_diagram"):
        C.reliability_diagram(
            chart_dir / name("reliability-diagram.png"),
            cal["reliability_diagram"],
            "Reliability diagram",
            subtitle,
        )
    else:
        C.empty_state(
            chart_dir / name("reliability-diagram.png"),
            "Reliability diagram",
            cal.get("basis", "the system reported no confidence"),
            subtitle=subtitle,
            headline="no confidence output",
        )

    lat = (runs[0].get("latency") if runs else {}) or {}
    if lat.get("count"):
        C.latency_chart(
            chart_dir / name("latency-percentiles.png"), lat,
            f"Latency percentiles, n={lat.get('count')}", subtitle,
        )
    else:
        C.empty_state(chart_dir / name("latency-percentiles.png"),
                      "Latency percentiles",
                      "no document completed, so there is no distribution to draw",
                      subtitle=subtitle, headline="no figure")

    if cost and cost.get("status") == "priced":
        per_doc = float(cost["cost_per_document"])
        C.single_value_chart(
            chart_dir / name("cost-per-document.png"),
            "per document",
            per_doc,
            f"Cost per document, {cost.get('currency')}",
            subtitle,
            value_text=fmt_money(per_doc, cost.get("currency", "USD")),
            axis_label=cost.get("currency", "USD"),
        )
    else:
        C.empty_state(
            chart_dir / name("cost-per-document.png"),
            "Cost per document",
            (cost or {}).get("not_priced_reason")
            or "no verified list price was supplied in prices.yaml",
            subtitle=subtitle,
            headline="not priced",
        )
    return written
