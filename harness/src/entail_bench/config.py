"""Configuration: the file, the defaults, and `validate-config`."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .scoring import ScoringSettings

DEFAULT_CONFIG_NAMES = ("entail-bench.yaml", "entail-bench.yml", "config.yaml")


@dataclass
class ModelEntry:
    name: str
    model_id: str | None = None
    options: dict = field(default_factory=dict)


@dataclass
class RejectRule:
    """A pre-processing rule that rejects a document before processing.

    Charter 3.4.3 and 3.4.4: both counts are reported, so the effect of the
    admission rule on the rate is visible. A rule must be named.
    """

    name: str
    field: str
    op: str
    value: Any

    def matches(self, document) -> bool:
        actual = getattr(document, self.field, None)
        if actual is None:
            actual = document.raw.get(self.field)
        try:
            if self.op in {"gt", "gte", "lt", "lte"}:
                left, right = float(actual), float(self.value)
                return {
                    "gt": left > right, "gte": left >= right,
                    "lt": left < right, "lte": left <= right,
                }[self.op]
            if self.op == "eq":
                return str(actual) == str(self.value)
            if self.op == "ne":
                return str(actual) != str(self.value)
            if self.op == "in":
                return str(actual) in [str(v) for v in (self.value or [])]
        except (TypeError, ValueError):
            return False
        raise ConfigError(f"unknown admission operator {self.op!r} in rule {self.name!r}")


@dataclass
class Config:
    suite: str = "messy-scan"
    dataset: str = "../datasets/messy-scan"
    split: str | None = "public_sample"
    prompt: str | None = None
    prompt_dir: str | None = None
    prices: str = "./prices.yaml"
    out: str = "./results"
    runs: int = 3
    limit: int | None = None
    spend_cap: str | None = None
    models: list[ModelEntry] = field(default_factory=list)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)
    adapter_options: dict = field(default_factory=dict)
    reject_rules: list[RejectRule] = field(default_factory=list)
    source_path: Path | None = None

    # ------------------------------------------------------------------ #
    def spend_cap_decimal(self) -> Decimal | None:
        if self.spend_cap in (None, "", "null"):
            return None
        try:
            return Decimal(str(self.spend_cap))
        except InvalidOperation as exc:
            raise ConfigError(f"spend_cap is not a number: {self.spend_cap!r}") from exc

    def prompt_directory(self) -> str | None:
        """Where the prompt files live.

        An explicit `prompt_dir`, else a `prompts/` folder beside the config
        file, else the package's own repository layout or the working
        directory. Named so a wheel install still finds the prompts a partner
        keeps beside their config.
        """
        if self.prompt_dir:
            return self.prompt_dir
        if self.source_path:
            candidate = self.source_path.parent / "prompts"
            if candidate.is_dir():
                return str(candidate)
        return None

    def resolve(self, relative: str | Path) -> Path:
        base = self.source_path.parent if self.source_path else Path.cwd()
        p = Path(relative).expanduser()
        return p if p.is_absolute() else (base / p).resolve()

    def as_dict(self) -> dict:
        return {
            "suite": self.suite,
            "dataset": self.dataset,
            "split": self.split,
            "prompt": self.prompt,
            "prices": self.prices,
            "out": self.out,
            "runs": self.runs,
            "limit": self.limit,
            "spend_cap": self.spend_cap,
            "models": [{"name": m.name, "model_id": m.model_id, "options": m.options}
                       for m in self.models],
            "scoring": self.scoring.as_dict(),
            "adapter_options": self.adapter_options,
            "admission_reject_rules": [
                {"name": r.name, "field": r.field, "op": r.op, "value": r.value}
                for r in self.reject_rules
            ],
            "config_file": str(self.source_path) if self.source_path else None,
        }


def find_config(explicit: str | Path | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            raise ConfigError(f"config file not found: {p}")
        return p.resolve()
    for name in DEFAULT_CONFIG_NAMES:
        candidate = Path.cwd() / name
        if candidate.exists():
            return candidate.resolve()
    return None


def load_config(path: str | Path | None = None) -> Config:
    found = find_config(path)
    if found is None:
        return Config()
    with open(found, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{found} does not hold a YAML mapping")

    scoring_raw = raw.get("scoring") or {}
    unknown = set(scoring_raw) - set(ScoringSettings().as_dict())
    if unknown:
        raise ConfigError(
            f"{found}: unknown scoring key(s) {sorted(unknown)}. Known keys: "
            f"{sorted(ScoringSettings().as_dict())}"
        )

    models = []
    for entry in raw.get("models") or []:
        if isinstance(entry, str):
            models.append(ModelEntry(name=entry))
        elif isinstance(entry, dict):
            if "name" not in entry:
                raise ConfigError(f"{found}: a models entry has no name")
            models.append(ModelEntry(
                name=entry["name"],
                model_id=entry.get("model_id"),
                options=dict(entry.get("options") or {}),
            ))
        else:
            raise ConfigError(f"{found}: a models entry is neither a name nor a mapping")

    rules = []
    for entry in (raw.get("admission") or {}).get("reject_rules") or []:
        missing = [k for k in ("name", "field", "op") if k not in entry]
        if missing:
            raise ConfigError(
                f"{found}: an admission reject rule is missing {missing}. "
                "A rule that rejects documents before processing must be named "
                "(charter 3.4.3)."
            )
        rules.append(RejectRule(entry["name"], entry["field"], entry["op"], entry.get("value")))

    config = Config(
        suite=raw.get("suite", "messy-scan"),
        dataset=raw.get("dataset", "../datasets/messy-scan"),
        split=raw.get("split", "public_sample"),
        prompt=raw.get("prompt"),
        prompt_dir=raw.get("prompt_dir"),
        prices=raw.get("prices", "./prices.yaml"),
        out=raw.get("out", "./results"),
        runs=int(raw.get("runs", 3)),
        limit=raw.get("limit"),
        spend_cap=raw.get("spend_cap"),
        models=models,
        scoring=ScoringSettings(**scoring_raw),
        adapter_options=dict(raw.get("adapter_options") or {}),
        reject_rules=rules,
        source_path=found,
    )
    return config


def validate_config(config: Config) -> dict:
    """Check a config without running anything. Returns a report dictionary."""
    from .adapters import availability_for, get_spec, registry_names
    from .cost import load_prices
    from .dataset import load_dataset
    from .prompts import default_prompt_name, load_prompt

    problems: list[str] = []
    warnings: list[str] = []
    checks: list[dict] = []

    # Dataset
    dataset_summary = None
    try:
        dataset = load_dataset(
            config.resolve(config.dataset), split=config.split,
            limit=config.limit, require_rendered=False,
        )
        dataset_summary = dataset.summary()
        checks.append({"check": "dataset", "status": "pass",
                       "detail": f"{len(dataset)} documents at {dataset.root}"})
        if dataset.unrendered:
            warnings.append(
                f"{len(dataset.unrendered)} document(s) have no rendered pages on "
                f"disk under {dataset.root}. Build the dataset before a run."
            )
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"dataset: {exc}")
        checks.append({"check": "dataset", "status": "fail", "detail": str(exc)})

    # Prompt
    prompt_name = config.prompt or default_prompt_name(config.suite)
    try:
        prompt = load_prompt(prompt_name, directory=config.prompt_directory())
        checks.append({"check": "prompt", "status": "pass",
                       "detail": f"{prompt.name} sha256 {prompt.sha256}"})
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"prompt: {exc}")
        checks.append({"check": "prompt", "status": "fail", "detail": str(exc)})

    # Models
    if not config.models:
        warnings.append(
            "no models are listed in the config. Name one with --model, or add a "
            f"models: list. Registered: {', '.join(registry_names())}"
        )
    model_rows = []
    for entry in config.models:
        try:
            state = availability_for(entry.name, model_id=entry.model_id)
            model_rows.append({
                "model": entry.name, "model_id": entry.model_id,
                "available": state.available, "reason": state.reason,
                "env_var": state.env_var,
            })
            if not state.available:
                warnings.append(
                    f"{entry.name}: {state.reason}. A run will record this model "
                    "`not run` with that reason."
                )
            effective_id = entry.model_id or get_spec(entry.name).model_id
            if effective_id in (None, ""):
                warnings.append(
                    f"{entry.name}: no model_id is set. The model version in scope "
                    "is a decision a person makes before a run; set model_id in the "
                    "config or pass --model-id."
                )
        except Exception as exc:                              # noqa: BLE001
            problems.append(f"model {entry.name}: {exc}")

    # Prices and spend cap
    price_status = {}
    try:
        prices = load_prices(config.resolve(config.prices))
        verified = [k for k, v in prices.providers.items() if v.get("verified") is True]
        unverified = [k for k in prices.providers if k not in verified]
        price_status = {
            "path": str(prices.path),
            "price_list_date": prices.price_list_date,
            "verified_entries": verified,
            "unverified_entries": unverified,
        }
        if not verified:
            warnings.append(
                "no entry in prices.yaml is marked verified, so cost per document "
                "will be reported `not priced`. Fill in the list prices from each "
                "provider's own page and set verified: true."
            )
        if prices.price_list_date is None:
            warnings.append("price_list_date is not set in prices.yaml.")
        checks.append({"check": "prices", "status": "pass", "detail": str(prices.path)})
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"prices: {exc}")
        checks.append({"check": "prices", "status": "fail", "detail": str(exc)})

    cap = None
    try:
        cap = config.spend_cap_decimal()
    except ConfigError as exc:
        problems.append(str(exc))
    if cap is None:
        warnings.append(
            "no spend_cap is set. Set spend_cap in the config or pass --max-spend "
            "before a run that calls a paid interface."
        )
    elif price_status.get("verified_entries") == []:
        problems.append(
            "a spend cap is set but no price in prices.yaml is verified, so the "
            "projected cost cannot be computed and the cap cannot be enforced. "
            "Fill in prices.yaml or remove the cap."
        )

    # Scoring settings
    if not 0.0 <= config.scoring.confidence_threshold <= 1.0:
        problems.append("scoring.confidence_threshold must be between 0 and 1")
    if config.scoring.calibration_bins < 2:
        problems.append("scoring.calibration_bins must be 2 or more")
    if config.scoring.calibration_bins != 10:
        warnings.append(
            f"calibration uses {config.scoring.calibration_bins} bins rather than "
            "the default ten. The bin count changes the number, so it is stated "
            "with every figure."
        )
    if config.runs < 3:
        warnings.append(
            f"runs is {config.runs}. Charter 3.1.4 requires three runs per model "
            "per suite; a row with fewer is marked incomplete and is not "
            "promoted into a headline table."
        )
    if config.scoring.required_fields not in {"all", "none"}:
        problems.append("scoring.required_fields must be `all` or `none`")

    return {
        "config": config.as_dict(),
        "dataset": dataset_summary,
        "models": model_rows,
        "prices": price_status,
        "checks": checks,
        "problems": problems,
        "warnings": warnings,
        "valid": not problems,
    }
