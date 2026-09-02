"""entail-bench — the Entailment Labs benchmark harness.

Metric definitions come from `10-benchmarks/charter/methodology.md`. Where this
code and that document disagree, the document wins and this code is a defect.

Two rules govern every line in this package:

1.  A figure that has not been produced by a run is written `not run` with the
    reason. It is never estimated, extrapolated or replaced with a
    plausible-looking figure, in a results file, a table, a chart or a fixture.
2.  A stub or fixture result is never written into a results file as though a
    model produced it. Fixture output is stamped `synthetic: true` and is
    refused by the leaderboard builder.
"""

__version__ = "1.0.0"
HARNESS_VERSION = __version__

__all__ = ["__version__", "HARNESS_VERSION"]
