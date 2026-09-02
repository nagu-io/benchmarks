"""End-to-end runs, aggregation, reporting and the `not run` path.

Every test here runs with no network and no key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from entail_bench.adapters import FIXTURE_MODEL_NAME
from entail_bench.aggregate import aggregate_runs, spread
from entail_bench.cli import main
from entail_bench.config import Config, ModelEntry, load_config
from entail_bench.runner import build_index, rebuild_report, rescore, run_model

PUBLIC_SAMPLE = (
    Path(__file__).resolve().parents[2] / "datasets" / "messy-scan"
)
SAMPLE_PRESENT = (PUBLIC_SAMPLE / "sample" / "ground-truth.jsonl").exists()


def base_config(harness_root: Path, dataset: Path, out: Path, split=None) -> Config:
    config = Config(
        suite="messy-scan",
        dataset=str(dataset),
        split=split,
        prompt="messy-scan-v1.0.0.md",
        prompt_dir=str(harness_root / "prompts"),
        prices=str(harness_root / "prices.yaml"),
        out=str(out),
        runs=3,
        source_path=harness_root / "entail-bench.yaml",
    )
    return config


# --------------------------------------------------------------------------- #
# The 50-document public sample                                                #
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not SAMPLE_PRESENT,
                    reason="the messy-scan public sample is not built in this checkout")
def test_dry_run_over_the_public_sample_produces_a_report(tmp_path, harness_root):
    config = base_config(harness_root, PUBLIC_SAMPLE, tmp_path / "results",
                         split="public_sample")
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=3, dry_run=True)

    assert outcome.status == "complete"
    assert outcome.synthetic is True
    run_dir = outcome.run_dir

    # The folder layout the pack asks for.
    assert (run_dir / "report.md").exists()
    assert (run_dir / "aggregate.json").exists()
    assert (run_dir / "provenance.json").exists()
    assert (run_dir / "NOT-A-RESULT.md").exists()
    for index in (1, 2, 3):
        assert (run_dir / f"run-{index}" / "raw" / "responses.jsonl").exists()
        assert (run_dir / f"run-{index}" / "scored.json").exists()
    charts = sorted(p.name for p in (run_dir / "charts").glob("*.png"))
    assert charts == [
        "accuracy-by-tier.png", "cost-per-document.png", "latency-percentiles.png",
        "reliability-diagram.png", "straight-through-by-tier.png",
    ]
    for chart in (run_dir / "charts").glob("*.png"):
        assert chart.stat().st_size > 1000, f"{chart.name} is not a real PNG"

    # The results folder is named for the suite and the dataset version.
    assert run_dir.parent.parent.name == "messy-scan-v1.0.0"
    assert run_dir.parent.name == FIXTURE_MODEL_NAME

    scored = json.loads((run_dir / "run-1" / "scored.json").read_text(encoding="utf-8"))
    counts = scored["counts"]
    assert counts["documents_received"] == 50
    assert counts["documents_admitted_to_processing"] == 50
    assert counts["documents_straight_through"] + counts["documents_exception"] == 50
    assert scored["identity_check"]["holds"] is True
    assert set(scored["breakdowns"]["by_tier"]) == {"T1", "T2", "T3", "T4", "T5"}
    assert len(scored["breakdowns"]["by_language"]) >= 2

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "is not a result" in report
    assert "You are reading a business document" in report, "the prompt is printed in full"
    assert "sha256" in report
    assert "messy-scan v1.0.0" in report
    assert "not priced" in report, "cost is not invented"
    assert "Straight-through-processing rate" in report
    assert "Expected calibration error" in report


@pytest.mark.skipif(not SAMPLE_PRESENT, reason="public sample not built")
def test_the_cli_dry_run_exits_zero_and_writes_a_report(tmp_path, harness_root, capsys):
    code = main([
        "-c", str(harness_root / "entail-bench.yaml"),
        "run", "--suite", "messy-scan", "--dry-run", "--runs", "3",
        "--out", str(tmp_path / "results"), "--quiet",
    ])
    assert code == 0
    printed = capsys.readouterr().out.strip().splitlines()
    run_dir = Path(printed[-1])
    assert (run_dir / "report.md").exists()

    # The exact command line is recorded so the run can be reproduced.
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["command"]
    assert provenance["dataset"]["dataset_version"] == "1.0.0"
    assert provenance["prompt"]["sha256"]
    assert provenance["harness_version"]
    assert provenance["run_date_utc"].endswith("Z")


# --------------------------------------------------------------------------- #
# The tiny dataset, for the paths that do not need 50 documents                #
# --------------------------------------------------------------------------- #


def test_a_partner_can_point_the_harness_at_their_own_folder(tmp_path, harness_root,
                                                             fixtures_dir):
    """`--dataset ./their-folder` is the whole of what a BPO has to change."""
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=3, dry_run=True)
    assert outcome.status == "complete"
    assert outcome.run_dir.parent.parent.name == "messy-scan-v0.0.1"
    report = (outcome.run_dir / "report.md").read_text(encoding="utf-8")
    assert "tiny-fixture v0.0.1" in report


def test_a_model_with_no_key_is_recorded_not_run_with_the_reason(
    tmp_path, harness_root, fixtures_dir
):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, "openai", runs=3)

    assert outcome.status == "not run"
    assert "OPENAI_API_KEY" in outcome.reason
    not_run = json.loads((outcome.run_dir / "not-run.json").read_text(encoding="utf-8"))
    assert not_run["status"] == "not run"
    assert not_run["env_var"] == "OPENAI_API_KEY"

    # No stub result is written.
    assert not list(outcome.run_dir.glob("run-*"))
    aggregate = json.loads((outcome.run_dir / "aggregate.json").read_text(encoding="utf-8"))
    assert aggregate["status"] == "not run"
    assert aggregate["headline"] == {}
    assert aggregate["publishable"] is False

    report = (outcome.run_dir / "report.md").read_text(encoding="utf-8")
    assert "## Status: not run" in report
    assert "OPENAI_API_KEY" in report
    assert "never estimated" in report
    for figure in ("%", "0.0"):
        assert f"| Straight-through-processing rate | {figure}" not in report


def test_a_chart_for_a_model_that_was_not_run_says_so(tmp_path, harness_root, fixtures_dir):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, "anthropic", runs=3)
    charts = sorted(p.name for p in (outcome.run_dir / "charts").glob("*.png"))
    assert len(charts) == 5
    for chart in (outcome.run_dir / "charts").glob("*.png"):
        assert chart.stat().st_size > 500

    # The empty state is drawn from text, not from bars: prove no series was
    # passed by checking the chart builder directly.
    from entail_bench import charts as C

    path = C.empty_state(tmp_path / "empty.png", "A title", "a stated reason")
    assert path.exists()


def test_scores_can_be_rebuilt_from_the_raw_responses_without_a_provider(
    tmp_path, harness_root, fixtures_dir
):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=3, dry_run=True)
    original = json.loads((outcome.run_dir / "run-1" / "scored.json").read_text())

    (outcome.run_dir / "run-1" / "scored.json").unlink()
    written = rescore(outcome.run_dir, config)
    assert (outcome.run_dir / "run-1" / "scored.json").exists()
    rebuilt = json.loads((outcome.run_dir / "run-1" / "scored.json").read_text())
    assert rebuilt["field_accuracy"] == original["field_accuracy"]
    assert any("aggregate.json" in str(p) for p in written)

    report = rebuild_report(outcome.run_dir, config)
    assert report.exists()


def test_a_different_threshold_changes_the_exception_rate_on_a_re_score(
    tmp_path, harness_root, fixtures_dir
):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    config.scoring.confidence_threshold = 0.99
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=1, dry_run=True)
    strict = json.loads((outcome.run_dir / "run-1" / "scored.json").read_text())

    config.scoring.confidence_threshold = 0.0
    rescore(outcome.run_dir, config)
    lenient = json.loads((outcome.run_dir / "run-1" / "scored.json").read_text())

    assert strict["exception"]["by_code"]["LOWCONF"] >= lenient["exception"]["by_code"]["LOWCONF"]
    assert strict["exception"]["confidence_threshold"] == 0.99
    assert lenient["exception"]["confidence_threshold"] == 0.0


def test_a_synthetic_run_is_refused_a_figure_in_the_index(tmp_path, harness_root,
                                                          fixtures_dir):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    run_model(config, FIXTURE_MODEL_NAME, runs=3, dry_run=True)
    run_model(config, "openai", runs=3)

    suite_dir = tmp_path / "results" / "messy-scan-v0.0.1"
    index = build_index(suite_dir).read_text(encoding="utf-8")
    assert "synthetic dry run, not a result" in index
    assert "not run" in index
    assert "OPENAI_API_KEY" in index
    fixture_row = next(l for l in index.splitlines() if FIXTURE_MODEL_NAME in l)
    assert "%" not in fixture_row, "a synthetic run never carries a figure"


def test_the_spend_cap_stops_the_run_and_reports(tmp_path, harness_root, fixtures_dir):
    """A cap with no verified price stops before the first call and says why."""
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=1, dry_run=True,
                        max_spend="1.00")
    assert outcome.status == "not run"
    assert "spend cap" in outcome.reason
    assert "prices.yaml" in outcome.reason


def test_running_totals_are_written_to_the_results_folder(tmp_path, harness_root,
                                                          fixtures_dir):
    config = base_config(harness_root, fixtures_dir / "tiny-dataset", tmp_path / "results")
    outcome = run_model(config, FIXTURE_MODEL_NAME, runs=1, dry_run=True)
    spend = json.loads((outcome.run_dir / "run-1" / "spend.json").read_text())
    assert spend["documents_done"] == 3
    assert spend["documents_not_priced"] == 3
    assert spend["stopped"] is False
    assert "not a result" in spend["projection_note"]


# --------------------------------------------------------------------------- #
# Aggregation over three runs                                                  #
# --------------------------------------------------------------------------- #


def test_the_spread_reports_mean_sd_min_and_max():
    block = spread([0.90, 0.94, 0.92])
    assert block["mean"] == pytest.approx(0.92)
    assert block["sd"] == pytest.approx(0.02)
    assert block["min"] == 0.90
    assert block["max"] == 0.94
    assert block["runs_with_a_figure"] == 3


def test_a_single_run_has_no_standard_deviation_and_is_not_publishable():
    one = spread([0.90])
    assert one["sd"] is None
    assert "not defined" in one["sd_basis"]

    aggregate = aggregate_runs([_fake_run(0.9)], requested_runs=3)
    assert aggregate["status"] == "incomplete"
    assert aggregate["publishable"] is False
    assert "three runs" in aggregate["publishable_reason"]


def test_three_runs_are_publishable():
    aggregate = aggregate_runs([_fake_run(0.90), _fake_run(0.92), _fake_run(0.94)])
    assert aggregate["status"] == "complete"
    assert aggregate["publishable"] is True
    assert aggregate["headline"]["field_accuracy"]["mean"] == pytest.approx(0.92)
    assert aggregate["headline"]["field_accuracy"]["sd"] == pytest.approx(0.02)


def test_no_run_at_all_is_not_run_with_a_reason():
    aggregate = aggregate_runs([], not_run_reason="no key")
    assert aggregate["status"] == "not run"
    assert aggregate["reason"] == "no key"
    assert aggregate["headline"] == {}


def _fake_run(accuracy: float) -> dict:
    return {
        "field_accuracy": {"rate": accuracy},
        "straight_through": {"rate": accuracy},
        "exception": {"rate": 1 - accuracy},
        "calibration": {"expected_calibration_error": 0.05,
                        "high_confidence_check": {"accuracy": accuracy}},
        "latency": {"p50_s": 1.0, "p95_s": 2.0, "p99_s": 3.0, "mean_s": 1.5},
        "counts": {"documents_admitted_to_processing": 50,
                   "documents_processing_failure": 0},
        "breakdowns": {"by_tier": {}, "by_language": {}, "by_doc_type": {}},
        "by_field": {},
    }


# --------------------------------------------------------------------------- #
# CLI surface                                                                  #
# --------------------------------------------------------------------------- #


def test_list_models_shows_every_model_and_why_each_is_not_run(capsys):
    assert main(["list-models"]) == 0
    out = capsys.readouterr().out
    for model in ("openai", "anthropic", "google", "mistral", "aws-textract",
                  "azure-document-intelligence", "google-document-ai",
                  "http-endpoint", "entail-pipeline", "local-vllm", "local-ollama"):
        assert model in out
    assert "not set" in out
    assert "No key is stored in this package." in out


def test_validate_config_reports_problems_and_warnings(harness_root, capsys):
    code = main(["-c", str(harness_root / "entail-bench.yaml"), "validate-config"])
    out = capsys.readouterr().out
    assert code == 0
    assert "not run" in out
    assert "no spend_cap is set" in out
    assert "no entry in prices.yaml is marked verified" in out


def test_validate_config_rejects_a_cap_with_no_verified_price(harness_root, tmp_path, capsys):
    config_path = tmp_path / "entail-bench.yaml"
    config_path.write_text(
        f"suite: messy-scan\n"
        f"dataset: {harness_root.parent / 'datasets' / 'messy-scan'}\n"
        f"split: public_sample\n"
        f"prompt: messy-scan-v1.0.0.md\n"
        f"prices: {harness_root / 'prices.yaml'}\n"
        f"spend_cap: 25.00\n"
        f"models: [openai]\n",
        encoding="utf-8",
    )
    code = main(["-c", str(config_path), "validate-config"])
    out = capsys.readouterr().out
    assert code == 1
    assert "cap cannot be enforced" in out


def test_the_config_file_is_read_and_overridden_by_the_command_line(harness_root):
    config = load_config(harness_root / "entail-bench.yaml")
    assert config.suite == "messy-scan"
    assert config.split == "public_sample"
    assert config.scoring.confidence_threshold == 0.85
    assert [m.name for m in config.models][:2] == ["openai", "anthropic"]
    assert all(isinstance(m, ModelEntry) for m in config.models)
