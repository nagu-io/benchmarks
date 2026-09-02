"""Three-run aggregation, charter sections 3.1.4 and 5.4.

Every published figure is the mean of three runs, with the standard deviation
and the minimum and maximum beside it. A single-run figure is never published,
so an aggregate over fewer than three runs is marked `incomplete` and the report
says how many ran and why.

The standard deviation is the sample standard deviation over runs, n-1. It is
undefined for a single run and is reported as such.
"""

from __future__ import annotations

from typing import Any, Callable

from .util import mean, stdev_sample

REQUIRED_RUNS = 3


def spread(values: list[float | None]) -> dict:
    present = [v for v in values if v is not None]
    return {
        "runs": len(values),
        "runs_with_a_figure": len(present),
        "mean": mean(present),
        "sd": stdev_sample(present),
        "sd_basis": "sample standard deviation over runs, n-1"
        if len(present) > 1 else "not defined for fewer than two runs",
        "min": min(present) if present else None,
        "max": max(present) if present else None,
        "values": present,
    }


def _pluck(runs: list[dict], path: list[str]) -> list[float | None]:
    out: list[float | None] = []
    for run in runs:
        node: Any = run
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        out.append(node if isinstance(node, (int, float)) else None)
    return out


HEADLINE_PATHS: dict[str, list[str]] = {
    "straight_through_rate": ["straight_through", "rate"],
    "exception_rate": ["exception", "rate"],
    "field_accuracy": ["field_accuracy", "rate"],
    "field_accuracy_exact_strict": ["field_accuracy", "exact_strict_rate"],
    "free_text_accuracy": ["free_text_accuracy", "rate"],
    "expected_calibration_error": ["calibration", "expected_calibration_error"],
    "high_confidence_accuracy": ["calibration", "high_confidence_check", "accuracy"],
    "latency_p50_s": ["latency", "p50_s"],
    "latency_p95_s": ["latency", "p95_s"],
    "latency_p99_s": ["latency", "p99_s"],
    "latency_mean_s": ["latency", "mean_s"],
    "processing_failures": ["counts", "documents_processing_failure"],
    "documents_admitted": ["counts", "documents_admitted_to_processing"],
}


def aggregate_runs(runs: list[dict], *, requested_runs: int = REQUIRED_RUNS,
                   not_run_reason: str | None = None) -> dict:
    """Mean, standard deviation, minimum and maximum across runs."""
    if not runs:
        return {
            "status": "not run",
            "reason": not_run_reason or "no run produced a scored result",
            "runs_completed": 0,
            "runs_requested": requested_runs,
            "publishable": False,
            "publishable_reason":
                "charter 3.1.8: a figure that has not been produced by a run is "
                "written `not run` with the reason",
            "headline": {},
        }

    headline = {name: spread(_pluck(runs, path)) for name, path in HEADLINE_PATHS.items()}
    complete = len(runs) >= REQUIRED_RUNS

    return {
        "status": "complete" if complete else "incomplete",
        "runs_completed": len(runs),
        "runs_requested": requested_runs,
        "publishable": complete,
        "publishable_reason": None if complete else (
            f"charter 3.1.4 and 5.4: every published figure is the mean of three "
            f"runs at identical settings. {len(runs)} of {requested_runs} ran, so "
            f"this row is incomplete and is not promoted into a headline table."
        ),
        "headline": headline,
        "by_tier": _aggregate_breakdown(runs, "by_tier"),
        "by_language": _aggregate_breakdown(runs, "by_language"),
        "by_doc_type": _aggregate_breakdown(runs, "by_doc_type"),
        "by_field": _aggregate_by_field(runs),
        "difference_rule":
            "A difference smaller than the reported spread is not a difference, "
            "and is not written about as one (charter 3.1.4 and 9.7).",
    }


def _aggregate_breakdown(runs: list[dict], key: str) -> dict:
    names: list[str] = []
    for run in runs:
        for name in (run.get("breakdowns") or {}).get(key, {}):
            if name not in names:
                names.append(name)
    out: dict[str, dict] = {}
    for name in sorted(names):
        out[name] = {
            "documents": _first(runs, ["breakdowns", key, name, "documents"]),
            "field_accuracy": spread(
                _pluck(runs, ["breakdowns", key, name, "field_accuracy", "rate"])),
            "straight_through_rate": spread(
                _pluck(runs, ["breakdowns", key, name, "straight_through", "rate"])),
            "exception_rate": spread(
                _pluck(runs, ["breakdowns", key, name, "exception", "rate"])),
            "latency_p95_s": spread(
                _pluck(runs, ["breakdowns", key, name, "latency_p95_s"])),
            "processing_failures": spread(
                _pluck(runs, ["breakdowns", key, name, "processing_failures"])),
        }
    return out


def _aggregate_by_field(runs: list[dict]) -> dict:
    names: list[str] = []
    for run in runs:
        for name in run.get("by_field", {}):
            if name not in names:
                names.append(name)
    out: dict[str, dict] = {}
    for name in sorted(names):
        out[name] = {
            "class": _first(runs, ["by_field", name, "class"]),
            "rule": _first(runs, ["by_field", name, "rule"]),
            "assessed": _first(runs, ["by_field", name, "denominator_assessed"]),
            "accuracy": spread(_pluck(runs, ["by_field", name, "rate"])),
        }
    return out


def _first(runs: list[dict], path: list[str]) -> Any:
    for run in runs:
        node: Any = run
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if node is not None:
            return node
    return None
