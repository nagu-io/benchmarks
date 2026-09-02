"""Exception types and process exit codes."""

from __future__ import annotations


class EntailBenchError(Exception):
    """Base class for every error this harness raises deliberately."""

    exit_code = 1


class ConfigError(EntailBenchError):
    """The configuration file or the command line is wrong."""

    exit_code = 1


class DatasetError(EntailBenchError):
    """The dataset folder is missing, incomplete or malformed."""

    exit_code = 1


class ReconciliationError(EntailBenchError):
    """Reported counts do not reconcile with the manifest.

    Charter section 3.1.2: the harness fails a run whose reported counts do not
    reconcile. A run that raises this writes its counts and exits non-zero; it
    does not publish a figure.
    """

    exit_code = 3


class SpendCapReached(EntailBenchError):
    """Projected cost would exceed the spend cap, so the run stopped."""

    exit_code = 2


class AdapterUnavailable(EntailBenchError):
    """The adapter cannot run: no key, no endpoint, or no client package.

    Raising this records the model as `not run` with the reason. It never
    causes a fallback to a stub.
    """

    exit_code = 0


class AdapterCallError(EntailBenchError):
    """One provider call failed. Recorded against the document, not the run."""

    exit_code = 1
