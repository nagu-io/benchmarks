"""PNG charts in the brand marks.

Paper #E4E8EA, ink #1C2329, extraction yellow #F5E9A0 for the automated share,
review red #B8321A for the human-reviewed share, rule grey #B7BEC3 hairlines.
IBM Plex Sans where it is installed. One baseline, no other gridlines, no
shadows, no gradients, no icons.

A chart for a model that was not run renders an explicit empty state reading
"not run" with the reason. It never renders sample bars. Charter section 10.4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

PAPER = "#E4E8EA"
INK = "#1C2329"
YELLOW = "#F5E9A0"
RED = "#B8321A"
RULE = "#B7BEC3"
ANNOTATION = "#585E63"

_FONT_DIRS = ("/home/claude/fonts", "/usr/share/fonts", str(Path.home() / ".fonts"))
_FONT_STATE: dict[str, object] = {}


def _setup():
    """Import matplotlib, register IBM Plex if it is on the machine."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    if not _FONT_STATE:
        family = "DejaVu Sans"
        found = False
        for directory in _FONT_DIRS:
            d = Path(directory)
            if not d.is_dir():
                continue
            for path in d.rglob("IBMPlexSans*.ttf"):
                try:
                    font_manager.fontManager.addfont(str(path))
                    found = True
                except Exception:                              # noqa: BLE001
                    pass
        available = {f.name for f in font_manager.fontManager.ttflist}
        if found and "IBM Plex Sans" in available:
            family = "IBM Plex Sans"
        _FONT_STATE["family"] = family
        _FONT_STATE["ibm_plex"] = family == "IBM Plex Sans"

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [str(_FONT_STATE["family"]), "DejaVu Sans"],
        "font.size": 9,
        "axes.facecolor": PAPER,
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.edgecolor": INK,
        "axes.linewidth": 1.0,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "figure.dpi": 160,
    })
    return plt


def font_note() -> str:
    if not _FONT_STATE:
        return "chart typeface not yet resolved"
    return (
        "IBM Plex Sans"
        if _FONT_STATE.get("ibm_plex")
        else "IBM Plex Sans is not installed on this machine; charts fall back to "
             "DejaVu Sans"
    )


def _finish(fig, ax, path: Path, title: str, subtitle: str | None = None):
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=24 if subtitle else 10)
    if subtitle:
        ax.annotate(
            subtitle, xy=(0, 1), xycoords="axes fraction",
            xytext=(0, 6), textcoords="offset points",
            fontsize=8, color=ANNOTATION, ha="left", va="bottom",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


def empty_state(
    path: str | Path,
    title: str,
    reason: str,
    *,
    subtitle: str | None = None,
    headline: str = "not run",
) -> Path:
    """The chart for a measure with no figure. No bars, no axis values.

    `headline` is "not run" for a model that was not run. It says something
    else only where the run happened and one measure has no figure, such as
    "not priced" or "no confidence output". It is never a number.
    """
    plt = _setup()
    path = Path(path)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.text(0.5, 0.58, headline, ha="center", va="center", fontsize=22, color=INK)
    ax.text(0.5, 0.34, reason, ha="center", va="center", fontsize=9,
            color=ANNOTATION, wrap=True)
    return _finish(fig, ax, path, title, subtitle)


def _hairline(ax):
    ax.spines["bottom"].set_color(RULE)


def _spread_whisker(ax, x: float, low, high):
    """A thin ink line from the minimum to the maximum across runs."""
    if low is None or high is None or low == high:
        return
    ax.plot([x, x], [low, high], color=INK, linewidth=1.0, solid_capstyle="butt", zorder=5)


def stacked_share_chart(
    path: str | Path,
    labels: list[str],
    automated: list[float | None],
    title: str,
    subtitle: str | None = None,
    *,
    automated_label: str = "automated",
    reviewed_label: str = "human-reviewed",
    counts: list[int] | None = None,
    spreads: list[tuple[float | None, float | None]] | None = None,
    axis_label: str = "per cent of documents",
) -> Path:
    """Yellow for the automated share, red for the human-reviewed share."""
    plt = _setup()
    path = Path(path)
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    xs = list(range(len(labels)))
    auto = [(v if v is not None else 0.0) * 100 for v in automated]
    rest = [100 - a for a in auto]
    ax.bar(xs, auto, color=YELLOW, edgecolor=INK, linewidth=0.6, width=0.62,
           label=automated_label, zorder=3)
    ax.bar(xs, rest, bottom=auto, color=RED, edgecolor=INK, linewidth=0.6, width=0.62,
           label=reviewed_label, zorder=3)
    if spreads:
        for x, (low, high) in zip(xs, spreads):
            _spread_whisker(ax, x, None if low is None else low * 100,
                            None if high is None else high * 100)
    ax.set_xticks(xs)
    ax.set_xticklabels(
        [f"{l}\nn={c}" if counts else l for l, c in zip(labels, counts or labels)],
        fontsize=8.5,
    )
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel(axis_label)
    _hairline(ax)
    ax.legend(loc="lower right", fontsize=8, ncol=2, bbox_to_anchor=(1.0, -0.32))
    for x, value in zip(xs, automated):
        if value is None:
            continue
        share = value * 100
        if share >= 10:
            # Inside the yellow, where ink reads.
            ax.text(x, share - 4.5, f"{share:.1f}", ha="center", va="center",
                    fontsize=8, color=INK, zorder=6)
        else:
            # The yellow is too short to hold the label, so it sits on the red.
            ax.text(x, share + 4.5, f"{share:.1f}", ha="center", va="center",
                    fontsize=8, color=PAPER, zorder=6)
    return _finish(fig, ax, path, title, subtitle)


def reliability_diagram(
    path: str | Path,
    bins: list[dict],
    title: str,
    subtitle: str | None = None,
) -> Path:
    plt = _setup()
    path = Path(path)
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    centres = [(b["lower"] + b["upper"]) / 2 for b in bins]
    width = (bins[0]["upper"] - bins[0]["lower"]) * 0.86 if bins else 0.09
    heights = [(b["accuracy"] if b["accuracy"] is not None else 0.0) for b in bins]
    ax.bar(centres, heights, width=width, color=YELLOW, edgecolor=INK,
           linewidth=0.6, zorder=3, label="accuracy in bin")
    ax.plot([0, 1], [0, 1], color=RULE, linewidth=1.0, zorder=2,
            label="perfect calibration")
    for b, centre in zip(bins, centres):
        if b["mean_confidence"] is not None:
            ax.plot([centre], [b["mean_confidence"]], marker="_", markersize=11,
                    color=RED, markeredgewidth=1.6, zorder=5)
    ax.plot([], [], marker="_", markersize=11, color=RED, linestyle="none",
            markeredgewidth=1.6, label="mean reported confidence")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("reported confidence")
    ax.set_ylabel("accuracy")
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    _hairline(ax)
    ax.legend(loc="upper left", fontsize=8)
    for b, centre in zip(bins, centres):
        if b["instances"]:
            ax.text(centre, 0.02, str(b["instances"]), ha="center", fontsize=7,
                    color=ANNOTATION, zorder=6)
    return _finish(fig, ax, path, title, subtitle)


def latency_chart(
    path: str | Path,
    percentiles: dict,
    title: str,
    subtitle: str | None = None,
) -> Path:
    plt = _setup()
    path = Path(path)
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    labels = ["p50", "p95", "p99"]
    values = [percentiles.get("p50_s"), percentiles.get("p95_s"), percentiles.get("p99_s")]
    xs = list(range(len(labels)))
    ax.bar(xs, [v or 0.0 for v in values], color=YELLOW, edgecolor=INK,
           linewidth=0.6, width=0.5, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.set_ylabel("seconds")
    _hairline(ax)
    for x, value in zip(xs, values):
        if value is not None:
            ax.text(x, value, f"{value:.3f}", ha="center", va="bottom",
                    fontsize=8, color=INK)
    return _finish(fig, ax, path, title, subtitle)


def single_value_chart(
    path: str | Path,
    label: str,
    value: float,
    title: str,
    subtitle: str | None = None,
    *,
    value_text: str | None = None,
    axis_label: str = "",
) -> Path:
    """One measured value, drawn as one bar. No comparison invented."""
    plt = _setup()
    path = Path(path)
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.bar([0], [value], color=YELLOW, edgecolor=INK, linewidth=0.6, width=0.4, zorder=3)
    ax.set_xticks([0])
    ax.set_xticklabels([label])
    ax.set_xlim(-0.6, 0.6)
    ax.set_ylabel(axis_label)
    _hairline(ax)
    ax.text(0, value, value_text or f"{value:g}", ha="center", va="bottom",
            fontsize=9, color=INK)
    return _finish(fig, ax, path, title, subtitle)


def accuracy_by_group_chart(
    path: str | Path,
    labels: list[str],
    accuracy: list[float | None],
    title: str,
    subtitle: str | None = None,
    counts: list[int] | None = None,
    spreads: list[tuple[float | None, float | None]] | None = None,
) -> Path:
    """Yellow for the share read correctly, red for the share a person corrects."""
    return stacked_share_chart(
        path, labels, accuracy, title, subtitle,
        automated_label="matched the label",
        reviewed_label="did not match",
        counts=counts,
        spreads=spreads,
        axis_label="per cent of field instances",
    )
