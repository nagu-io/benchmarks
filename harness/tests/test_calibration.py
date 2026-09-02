"""Expected calibration error and the reliability diagram, charter section 3.6."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from entail_bench.calibration import calibration_report


@dataclass
class Fake:
    """The one shape the calibration code reads: correct plus a confidence."""

    correct: bool
    confidence: float | None


def instances(spec: list[tuple[int, float, float]]) -> list[Fake]:
    """(count, confidence, accuracy) -> instances with that confidence."""
    out: list[Fake] = []
    for count, confidence, accuracy in spec:
        correct = round(count * accuracy)
        out += [Fake(True, confidence)] * correct
        out += [Fake(False, confidence)] * (count - correct)
    return out


def test_the_worked_arithmetic_of_the_charter_reproduces():
    """Charter 3.6.6 sets out the arithmetic on invented numbers.

    Those numbers are an arithmetic example, not a result. This test uses them
    to prove the formula is implemented as written:

        bin 0.5-0.6: 100 instances, mean 0.55, accuracy 0.50 -> 0.005
        bin 0.8-0.9: 300 instances, mean 0.85, accuracy 0.79 -> 0.018
        bin 0.9-1.0: 600 instances, mean 0.97, accuracy 0.91 -> 0.036
        expected calibration error = 0.059
    """
    items = instances([(100, 0.55, 0.50), (300, 0.85, 0.79), (600, 0.97, 0.91)])
    report = calibration_report(items, bins=10)
    assert report["instances_with_confidence"] == 1000
    assert report["expected_calibration_error"] == pytest.approx(0.059, abs=1e-9)

    occupied = {b["bin"]: b for b in report["reliability_diagram"] if b["instances"]}
    assert len(occupied) == 3
    assert occupied["[0.5, 0.6)"]["contribution"] == pytest.approx(0.005)
    assert occupied["[0.8, 0.9)"]["contribution"] == pytest.approx(0.018)
    assert occupied["[0.9, 1.0]"]["contribution"] == pytest.approx(0.036)


def test_a_perfectly_calibrated_system_scores_zero():
    items = instances([(100, 0.5, 0.5), (100, 0.9, 0.9)])
    report = calibration_report(items, bins=10)
    assert report["expected_calibration_error"] == pytest.approx(0.0)


def test_weights_sum_to_one_over_occupied_bins():
    items = instances([(100, 0.55, 0.5), (300, 0.85, 0.8), (600, 0.95, 0.9)])
    report = calibration_report(items, bins=10)
    assert sum(b["weight"] for b in report["reliability_diagram"]) == pytest.approx(1.0)


def test_a_confidence_of_exactly_one_lands_in_the_last_bin():
    report = calibration_report([Fake(True, 1.0), Fake(False, 1.0)], bins=10)
    last = report["reliability_diagram"][-1]
    assert last["instances"] == 2
    assert report["instances_with_confidence"] == 2


def test_the_bin_count_is_stated_because_it_changes_the_number():
    # Two groups that sit in different bins at ten and in one bin at five. Their
    # gaps have opposite signs, so merging them cancels most of the error.
    items = instances([(100, 0.45, 0.90), (100, 0.55, 0.20)])
    ten = calibration_report(items, bins=10)
    five = calibration_report(items, bins=5)
    assert ten["binning"] == "10 equal-width bins on the interval 0 to 1"
    assert five["binning"] == "5 equal-width bins on the interval 0 to 1"
    assert ten["expected_calibration_error"] == pytest.approx(0.40)
    assert five["expected_calibration_error"] == pytest.approx(0.05)


def test_no_confidence_output_is_never_an_error_of_zero():
    report = calibration_report([Fake(True, None), Fake(False, None)], bins=10)
    assert report["status"] == "no confidence output"
    assert report["expected_calibration_error"] is None
    assert "never reported as an expected calibration error of zero" in report["basis"]
    assert report["share_without_confidence"] == 1.0


def test_a_system_that_reports_no_confidence_at_all_is_flagged_by_the_caller():
    items = instances([(10, 0.9, 1.0)])
    report = calibration_report(items, bins=10, confidence_reported=False)
    assert report["status"] == "no confidence output"
    assert report["expected_calibration_error"] is None


def test_instances_without_a_confidence_are_counted_and_reported():
    items = instances([(80, 0.9, 0.9)]) + [Fake(True, None)] * 20
    report = calibration_report(items, bins=10)
    assert report["instances_with_confidence"] == 80
    assert report["instances_without_confidence"] == 20
    assert report["share_without_confidence"] == pytest.approx(0.2)


def test_the_high_confidence_check_travels_with_the_error():
    items = instances([(100, 0.96, 0.80), (100, 0.50, 0.50)])
    report = calibration_report(items, bins=10)
    high = report["high_confidence_check"]
    assert high["floor"] == 0.95
    assert high["denominator"] == 100
    assert high["numerator"] == 80
    assert high["accuracy"] == pytest.approx(0.80)


def test_an_empty_population_reports_no_confidence_output():
    report = calibration_report([], bins=10)
    assert report["status"] == "no confidence output"
    assert report["expected_calibration_error"] is None
