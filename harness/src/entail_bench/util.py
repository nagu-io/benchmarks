"""Small shared helpers: hashing, redaction, rounding, JSON writing."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

# Anything whose key matches this is removed before a payload is written to
# disk. No key value ever reaches a results folder.
#   Matched against the whole key, with any dotted, hyphenated or underscored
#   prefix allowed, so `x-goog-api-key`, `Ocp-Apim-Subscription-Key` and
#   `AWS_SECRET_ACCESS_KEY` are caught while `prompt_tokens` and
#   `completion_tokens_details` are not.
_SECRET_KEY_RE = re.compile(
    r"^(?:[a-z0-9]+[-_.])*"
    r"(?:api[-_]?key|apikey|authorization|auth|secret|password|passwd|"
    r"credential|credentials|token|subscription[-_]?key|access[-_]?key|"
    r"session[-_]?id)$",
    re.IGNORECASE,
)
_REDACTED = "[redacted]"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def redact(obj: Any) -> Any:
    """Recursively replace anything that looks like a credential.

    Applied to every request and response payload before it is written to a
    results folder. The harness never writes a key.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and _SECRET_KEY_RE.search(k):
                out[k] = _REDACTED
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str) and len(obj) > 20:
        # Bearer tokens pasted into a free string field.
        if obj.lower().startswith("bearer ") or obj.startswith(("sk-", "sk_", "AKIA")):
            return _REDACTED
    return obj


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso_now() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_slug(when: _dt.datetime | None = None) -> str:
    when = when or utc_now()
    return when.strftime("%Y%m%dT%H%M%SZ")


def write_json(path: str | Path, obj: Any, *, sort_keys: bool = True) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=sort_keys, ensure_ascii=False, default=_default)
        fh.write("\n")
    return path


def append_jsonl(path: str | Path, obj: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=_default) + "\n")
    return path


def read_jsonl(path: str | Path) -> list[dict]:
    out: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"not JSON serialisable: {type(obj)!r}")


# --------------------------------------------------------------------------- #
# Rounding, charter section 3.1.5                                              #
# --------------------------------------------------------------------------- #
#   Rates to one decimal place. Money to four significant figures. Times to the
#   precision the source clock supports. Raw values are kept unrounded in the
#   JSON; rounding happens only where a figure is printed.


def fmt_rate(value: float | None, *, unit: str = "%") -> str:
    """A rate as a percentage to one decimal place, or `not run`."""
    if value is None:
        return "not run"
    return f"{value * 100:.1f}{unit}"


def fmt_ratio(value: float | None, places: int = 4) -> str:
    if value is None:
        return "not run"
    return f"{value:.{places}f}"


def fmt_money(value: float | Decimal | None, currency: str = "USD", sigfigs: int = 4) -> str:
    """Money to four significant figures with its currency."""
    if value is None:
        return "not priced"
    v = float(value)
    if v == 0:
        return f"{currency} 0"
    digits = sigfigs - int(math.floor(math.log10(abs(v)))) - 1
    digits = max(digits, 0)
    return f"{currency} {v:.{digits}f}"


def fmt_seconds(value: float | None, places: int | None = None) -> str:
    """Times print at the precision the source clock supports.

    `time.perf_counter` resolves below the microsecond, so a short duration
    keeps its significant digits rather than rounding to `0.000 s`.
    """
    if value is None:
        return "not run"
    if places is None:
        places = 3 if abs(value) >= 0.001 else 6
    return f"{value:.{places}f} s"


def fmt_count(value: int | None) -> str:
    return "not run" if value is None else f"{value:,}"


def percentile_nearest_rank(values: Sequence[float], pct: float) -> float | None:
    """Nearest-rank percentile, charter section 3.8.1.

    Rank = ceil(pct/100 * N) over the ascending sort, 1-indexed.
    """
    xs = sorted(v for v in values if v is not None)
    n = len(xs)
    if n == 0:
        return None
    rank = math.ceil(pct / 100.0 * n)
    rank = min(max(rank, 1), n)
    return xs[rank - 1]


def mean(values: Iterable[float]) -> float | None:
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None


def stdev_sample(values: Iterable[float]) -> float | None:
    """Sample standard deviation, n-1. None for fewer than two observations."""
    xs = [v for v in values if v is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def env_present(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-").lower()
