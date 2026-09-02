"""The `entail-bench` command line.

    entail-bench run --suite messy-scan --model <name> --runs 3
    entail-bench score --run-dir <path>
    entail-bench report --run-dir <path>
    entail-bench list-models
    entail-bench validate-config

`--dataset ./their-folder` points the harness at a partner's own documents.
`--dry-run` exercises the whole path with a recorded fixture and no network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import HARNESS_VERSION
from .adapters import FIXTURE_MODEL_NAME, availability_for, load_registry
from .config import Config, ModelEntry, load_config, validate_config
from .errors import EntailBenchError
from .runner import build_index, rebuild_report, rescore, run_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="entail-bench",
        description=(
            "Evaluation harness for the Entailment Labs benchmark suites. "
            "Metric definitions come from 10-benchmarks/charter/methodology.md."
        ),
    )
    parser.add_argument("--version", action="version", version=f"entail-bench {HARNESS_VERSION}")
    parser.add_argument("-c", "--config", help="path to a config file")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a suite against one or more models")
    run.add_argument("--suite", default=None, help="suite name, for example messy-scan")
    run.add_argument("--model", action="append", default=None,
                     help="model to score; repeat for several")
    run.add_argument("--model-id", default=None,
                     help="the provider's model identifier, for a single --model")
    run.add_argument("--runs", type=int, default=None,
                     help="runs per model; charter 3.1.4 requires three")
    run.add_argument("--dataset", default=None,
                     help="dataset folder; point this at your own documents")
    run.add_argument("--split", default=None,
                     help="public_sample, private_holdout, or all")
    run.add_argument("--limit", type=int, default=None, help="score only the first N documents")
    run.add_argument("--out", default=None, help="results root; default ./results")
    run.add_argument("--prompt", default=None, help="prompt filename in prompts/")
    run.add_argument("--prices", default=None, help="path to prices.yaml")
    run.add_argument("--max-spend", default=None,
                     help="stop the run when the projected cost would exceed this")
    run.add_argument("--threshold", type=float, default=None,
                     help="confidence threshold for the review queue")
    run.add_argument("--bins", type=int, default=None, help="calibration bins; default 10")
    run.add_argument("--audit-rate", type=float, default=None,
                     help="sampled-audit rate; default 0")
    run.add_argument("--dry-run", action="store_true",
                     help="exercise the whole path with a recorded synthetic fixture, "
                          "no network and no key. The output is stamped synthetic "
                          "and is never a result.")
    run.add_argument("--quiet", action="store_true")

    score = sub.add_parser("score", help="re-score raw responses already on disk")
    score.add_argument("--run-dir", required=True, help="a results folder holding run-*/raw")
    score.add_argument("--dataset", default=None)
    score.add_argument("--split", default=None)
    score.add_argument("--threshold", type=float, default=None)
    score.add_argument("--bins", type=int, default=None)
    score.add_argument("--audit-rate", type=float, default=None)
    score.add_argument("--report", action="store_true", help="rebuild the report afterwards")

    report = sub.add_parser("report", help="rebuild a report and its charts")
    report.add_argument("--run-dir", default=None, help="a results folder")
    report.add_argument("--suite-dir", default=None,
                        help="a suite folder; writes index.md across every model")
    report.add_argument("--dataset", default=None)
    report.add_argument("--split", default=None)

    models = sub.add_parser("list-models", help="registered models and their availability")
    models.add_argument("--json", action="store_true")

    check = sub.add_parser("validate-config", help="check a config without running anything")
    check.add_argument("--json", action="store_true")
    check.add_argument("--dataset", default=None)
    check.add_argument("--split", default=None)

    return parser


def _apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    for name in ("suite", "dataset", "split", "prompt", "prices", "out", "limit"):
        value = getattr(args, name, None)
        if value is not None:
            setattr(config, name, value)
    if getattr(args, "runs", None) is not None:
        config.runs = args.runs
    if getattr(args, "threshold", None) is not None:
        config.scoring.confidence_threshold = args.threshold
    if getattr(args, "bins", None) is not None:
        config.scoring.calibration_bins = args.bins
    if getattr(args, "audit_rate", None) is not None:
        config.scoring.audit_rate = args.audit_rate
    if getattr(args, "max_spend", None) is not None:
        config.spend_cap = args.max_spend
    models = getattr(args, "model", None)
    if models:
        config.models = [ModelEntry(name=m, model_id=getattr(args, "model_id", None))
                         for m in models]
    if getattr(args, "dry_run", False):
        config.models = [ModelEntry(name=FIXTURE_MODEL_NAME)]
    return config


# --------------------------------------------------------------------------- #
# Commands                                                                     #
# --------------------------------------------------------------------------- #


def cmd_run(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config(args.config), args)
    say = (lambda _m: None) if args.quiet else (lambda m: print(m, file=sys.stderr))

    if not config.models:
        print(
            "No model named. Use --model <name>, or list models in the config. "
            "Registered models: " + ", ".join(sorted(load_registry())),
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        say(
            "Dry run: no provider is called. The output is a synthetic fixture, "
            "stamped as such, and is not a result."
        )

    outcomes = []
    exit_code = 0
    for entry in config.models:
        try:
            outcome = run_model(
                config, entry.name,
                model_id=entry.model_id or getattr(args, "model_id", None),
                runs=config.runs,
                out_root=Path(args.out) if args.out else None,
                max_spend=args.max_spend,
                dry_run=args.dry_run,
                progress=say,
            )
        except EntailBenchError as exc:
            print(f"{entry.name}: {exc}", file=sys.stderr)
            exit_code = max(exit_code, exc.exit_code)
            continue
        outcomes.append(outcome)
        say(f"{entry.name}: {outcome.status} -> {outcome.run_dir}")
        if outcome.status == "stopped":
            exit_code = max(exit_code, 2)

    for outcome in outcomes:
        print(outcome.run_dir)
    return exit_code


def cmd_score(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config(args.config), args)
    written = rescore(Path(args.run_dir), config,
                      progress=lambda m: print(m, file=sys.stderr))
    for path in written:
        print(path)
    if args.report:
        print(rebuild_report(Path(args.run_dir), config))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config(args.config), args)
    if args.suite_dir:
        print(build_index(Path(args.suite_dir)))
        return 0
    if not args.run_dir:
        print("give --run-dir or --suite-dir", file=sys.stderr)
        return 1
    print(rebuild_report(Path(args.run_dir), config))
    return 0


def cmd_list_models(args: argparse.Namespace) -> int:
    registry = load_registry()
    rows = []
    for name, spec in sorted(registry.items()):
        state = availability_for(name)
        rows.append({
            "model": name,
            "adapter": spec.adapter,
            "provider": spec.provider,
            "kind": spec.kind,
            "model_id": spec.model_id,
            "environment_variables": spec.env_vars,
            "optional_environment_variables": spec.optional_env_vars,
            "price_key": spec.price_key,
            "available": state.available,
            "reason": state.reason,
            "note": spec.note,
        })
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    width = max(len(r["model"]) for r in rows)
    print(f"{'model'.ljust(width)}  {'status'.ljust(12)}  environment variables")
    print(f"{'-' * width}  {'-' * 12}  {'-' * 40}")
    for row in rows:
        status = "available" if row["available"] else "not run"
        env = ", ".join(row["environment_variables"]) or "none"
        print(f"{row['model'].ljust(width)}  {status.ljust(12)}  {env}")
        if not row["available"] and row["reason"]:
            print(f"{' ' * width}  {' ' * 12}  reason: {row['reason']}")
    print()
    print(
        "A model whose environment variable is absent reports itself unavailable. "
        "A run records it as `not run` with that reason and writes no figure for "
        "it. No key is stored in this package."
    )
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    config = _apply_overrides(load_config(args.config), args)
    report = validate_config(config)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0 if report["valid"] else 1

    print(f"Config: {report['config'].get('config_file') or 'defaults, no file found'}")
    print()
    for check in report["checks"]:
        print(f"  [{check['status']}] {check['check']}: {check['detail']}")
    if report.get("dataset"):
        d = report["dataset"]
        print()
        print(f"  dataset {d['dataset']} v{d['dataset_version']}, "
              f"{d['documents']} documents")
        print(f"  tier mix: {d['tier_mix']}")
        print(f"  language mix: {d['language_mix']}")
    if report["models"]:
        print()
        for row in report["models"]:
            status = "available" if row["available"] else "not run"
            print(f"  model {row['model']}: {status}"
                  + (f" — {row['reason']}" if row["reason"] else ""))
    if report["warnings"]:
        print()
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")
    if report["problems"]:
        print()
        print("Problems:")
        for problem in report["problems"]:
            print(f"  - {problem}")
    print()
    print("valid" if report["valid"] else "not valid")
    return 0 if report["valid"] else 1


COMMANDS = {
    "run": cmd_run,
    "score": cmd_score,
    "report": cmd_report,
    "list-models": cmd_list_models,
    "validate-config": cmd_validate_config,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except EntailBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
