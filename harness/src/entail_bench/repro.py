"""Reproducibility block, charter section 5.5.

Every report records the dataset version and content hash, the harness version
and commit hash, the prompt set hash, the model version string as the provider
reported it, the run date and time, the price list date, and the exact command
line. A figure that cannot be reproduced from those is withdrawn, not defended.
"""

from __future__ import annotations

import platform
import shlex
import subprocess
import sys
from pathlib import Path

from . import HARNESS_VERSION
from .util import iso_now


def git_commit(start: Path | None = None) -> dict:
    """The harness commit, and whether the tree was clean when the run started."""
    cwd = Path(start or Path(__file__).resolve().parent)
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
            text=True, timeout=10, check=False,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True,
            text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "clean": None,
                "note": "git is not available in this environment"}
    if commit.returncode != 0:
        return {"commit": None, "clean": None,
                "note": "not a git working tree, so no commit hash was recorded"}
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    return {
        "commit": commit.stdout.strip(),
        "clean": not dirty,
        "uncommitted_paths": len(dirty),
        "note": None if not dirty else (
            "the working tree had uncommitted changes when this run started, so "
            "the commit hash alone does not reproduce it"
        ),
    }


def command_line() -> str:
    return " ".join(shlex.quote(part) for part in sys.argv)


def provenance(
    *,
    suite: str,
    dataset_summary: dict,
    prompt_name: str,
    prompt_sha256: str,
    model: str,
    model_id: str | None,
    model_version: str | None,
    price_list_date: str | None,
    settings: dict,
    field_rules: dict,
    command: str | None = None,
    extra: dict | None = None,
) -> dict:
    return {
        "suite": suite,
        "run_date_utc": iso_now(),
        "harness_version": HARNESS_VERSION,
        "harness_commit": git_commit(),
        "dataset": dataset_summary,
        "prompt": {"file": prompt_name, "sha256": prompt_sha256},
        "model": {
            "name": model,
            "model_id_requested": model_id,
            "model_version_reported": model_version,
            "basis": "the model version string as the provider reported it",
        },
        "price_list_date": price_list_date,
        "scoring_settings": settings,
        "match_rules": field_rules,
        "command": command or command_line(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        **(extra or {}),
    }
