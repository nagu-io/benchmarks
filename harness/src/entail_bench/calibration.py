"""Expected calibration error and the reliability diagram, charter section 3.6.

    ECE = sum over bins of (instances in bin / total instances)
              * |accuracy of bin - mean reported confidence of bin|

The unit is one field instance. Ten equal-width bins on the interval zero to one
are the default; any other binning is stated with the figure, because the bin
count changes the number.

Two figures always travel with the expected calibration error: the reliability
diagram, and the high-confidence check, being the accuracy of instances whose
reported confidence is at or above 0.95.

A system that reports no confidence at all is reported as "no confidence
output". It is never reported as an expected calibration error of zero.
"""

from __future__ import annotations

from typing import Iterable

HIGH_CONFIDENCE_FLOOR = 0.95


def calibration_report(
    instances: Iterable,
    *,
    bins: int = 10,
    confidence_reported: bool = True,
) -> dict:
    items = list(instances)
    total_assessed = len(items)
    scored = [i for i in items if i.confidence is not None]
    unscored = total_assessed - len(scored)

    if not confidence_reported or not scored:
        return {
            "status": "no confidence output",
            "expected_calibration_error": None,
            "basis":
                "The system reported no confidence for any assessed field "
                "instance, so calibration cannot be measured. Charter 3.6.4: "
                "this is never reported as an expected calibration error of zero.",
            "bins": bins,
            "binning": f"{bins} equal-width bins on the interval 0 to 1",
            "instances_with_confidence": 0,
            "instances_without_confidence": unscored,
            "share_without_confidence": 1.0 if total_assessed else None,
            "reliability_diagram": [],
            "high_confidence_check": {
                "floor": HIGH_CONFIDENCE_FLOOR,
                "numerator": None,
                "denominator": 0,
                "accuracy": None,
            },
        }

    width = 1.0 / bins
    buckets: list[dict] = []
    for index in range(bins):
        low = index * width
        high = (index + 1) * width
        members = [
            i for i in scored
            if (low <= i.confidence < high) or (index == bins - 1 and i.confidence == 1.0)
        ]
        if members:
            accuracy = sum(1 for m in members if m.correct) / len(members)
            mean_conf = sum(m.confidence for m in members) / len(members)
        else:
            accuracy = None
            mean_conf = None
        buckets.append({
            "bin": f"[{low:.1f}, {high:.1f}{']' if index == bins - 1 else ')'}",
            "lower": low,
            "upper": high,
            "instances": len(members),
            "weight": len(members) / len(scored),
            "accuracy": accuracy,
            "mean_confidence": mean_conf,
            "gap": abs(accuracy - mean_conf) if members else None,
            "contribution": (len(members) / len(scored)) * abs(accuracy - mean_conf)
            if members else 0.0,
        })

    ece = sum(b["contribution"] for b in buckets)
    high = [i for i in scored if i.confidence >= HIGH_CONFIDENCE_FLOOR]
    high_correct = sum(1 for i in high if i.correct)

    return {
        "status": "measured",
        "expected_calibration_error": ece,
        "bins": bins,
        "binning": f"{bins} equal-width bins on the interval 0 to 1",
        "unit": "one field instance",
        "instances_with_confidence": len(scored),
        "instances_without_confidence": unscored,
        "share_without_confidence": (unscored / total_assessed) if total_assessed else None,
        "reliability_diagram": buckets,
        "high_confidence_check": {
            "floor": HIGH_CONFIDENCE_FLOOR,
            "numerator": high_correct,
            "denominator": len(high),
            "accuracy": (high_correct / len(high)) if high else None,
            "basis":
                "The accuracy of instances returned at or above 0.95 confidence, "
                "which is what a review threshold actually depends on",
        },
    }
