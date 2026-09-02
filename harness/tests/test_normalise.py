"""Match rules, charter section 3.3.2."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from entail_bench import normalise as N
from entail_bench.fieldrules import load_field_rules


@pytest.fixture
def rules():
    return load_field_rules()


# --------------------------------------------------------------------------- #
# Dates                                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2026-01-15", dt.date(2026, 1, 15)),
        ("15/01/2026", dt.date(2026, 1, 15)),
        ("15-01-2026", dt.date(2026, 1, 15)),
        ("15.01.2026", dt.date(2026, 1, 15)),
        ("15 January 2026", dt.date(2026, 1, 15)),
        ("15 Jan 2026", dt.date(2026, 1, 15)),
        ("January 15, 2026", dt.date(2026, 1, 15)),
        ("2026-01-15T09:30:00", dt.date(2026, 1, 15)),
        ("  2026-01-15  ", dt.date(2026, 1, 15)),
    ],
)
def test_date_forms_parse_to_the_same_calendar_date(text, expected):
    assert N.parse_date(text, display_format="%d/%m/%Y").value == expected


def test_day_first_and_month_first_are_read_from_the_document_format():
    assert N.parse_date("03/04/2026", display_format="%d/%m/%Y").value == dt.date(2026, 4, 3)
    assert N.parse_date("03/04/2026", display_format="%m/%d/%Y").value == dt.date(2026, 3, 4)


def test_an_ambiguous_numeric_date_is_flagged():
    parsed = N.parse_date("03/04/2026", display_format="%d/%m/%Y")
    assert parsed.ambiguous is True
    unambiguous = N.parse_date("15/04/2026", display_format="%d/%m/%Y")
    assert unambiguous.ambiguous is False


def test_an_impossible_date_in_the_stated_order_falls_back_and_is_flagged():
    parsed = N.parse_date("13/25/2026", display_format="%d/%m/%Y")
    assert parsed.value is None or parsed.ambiguous is True


def test_a_near_match_date_is_not_a_match(rules):
    """One day out is wrong. There is no date tolerance."""
    result = rules.match("date", "2026-01-15", "2026-01-16", present=True,
                         display_format="%d/%m/%Y")
    assert result.correct is False
    assert result.reason == "mismatch"


def test_a_reformatted_date_is_a_match(rules):
    result = rules.match("date", "2026-01-15", "15/01/2026", present=True,
                         display_format="%d/%m/%Y")
    assert result.correct is True
    assert result.exact_strict is False


def test_unparseable_date_is_recorded_as_such(rules):
    result = rules.match("date", "2026-01-15", "sometime in January", present=True)
    assert result.correct is False
    assert result.reason == "unparseable_date"


# --------------------------------------------------------------------------- #
# Amounts                                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text,value",
    [
        ("1250.00", Decimal("1250.00")),
        ("1,250.00", Decimal("1250.00")),
        ("₹1,250.00", Decimal("1250.00")),
        ("Rs. 1,250.00", Decimal("1250.00")),
        ("INR 1250", Decimal("1250")),
        ("1 250,00", Decimal("1250.00")),
        ("4,83,265.00", Decimal("483265.00")),
        ("$1,250.00", Decimal("1250.00")),
        ("(1250.00)", Decimal("-1250.00")),
        ("-1250.00", Decimal("-1250.00")),
        ("1.250,50", Decimal("1250.50")),
    ],
)
def test_currency_formatting_is_normalised(text, value):
    assert N.parse_amount(text).value == value


def test_currency_code_is_taken_from_the_symbol():
    assert N.parse_amount("₹1,250.00").currency == "INR"
    assert N.parse_amount("€1.250,50").currency == "EUR"
    assert N.parse_amount("₱1,250.00").currency == "PHP"


def test_indian_and_western_grouping_agree(rules):
    result = rules.match("amount", "483265.00", "4,83,265.00", present=True,
                         expected_currency="INR", returned_currency="INR")
    assert result.correct is True


def test_a_money_value_with_the_wrong_currency_is_wrong(rules):
    result = rules.match("amount", "1250.00", "USD 1250.00", present=True,
                         expected_currency="INR", returned_currency="INR")
    assert result.correct is False
    assert result.reason == "currency_mismatch"


def test_a_money_value_with_no_currency_anywhere_is_recorded(rules):
    strict = rules.match("amount", "1250.00", "1250.00", present=True,
                         expected_currency="INR", returned_currency=None,
                         currency_required=True)
    assert strict.correct is False
    assert strict.reason == "currency_missing"

    lenient = rules.match("amount", "1250.00", "1250.00", present=True,
                          expected_currency="INR", returned_currency=None,
                          currency_required=False)
    assert lenient.correct is True
    assert lenient.note == "currency_unstated"


def test_a_money_value_off_by_a_paisa_is_wrong(rules):
    result = rules.match("amount", "1250.00", "1250.01", present=True,
                         expected_currency="INR", returned_currency="INR")
    assert result.correct is False
    assert result.reason == "value_mismatch"


# --------------------------------------------------------------------------- #
# Whitespace, Unicode, case                                                    #
# --------------------------------------------------------------------------- #


def test_nfkc_folds_a_fullwidth_identifier(rules):
    fullwidth = "２４ＴＳＴＮＡ１２３４Ａ１Ｚ９"
    result = rules.match("identifier", "24TSTNA1234A1Z9", fullwidth, present=True)
    assert result.correct is True
    assert result.exact_strict is False


def test_a_non_breaking_space_is_normalised_in_a_name(rules):
    # Written as a code point: a no-break space is invisible in a source file,
    # and a test that turns on one is not allowed to depend on it surviving a
    # copy, a paste or a diff.
    nbsp = chr(0x00A0)
    returned = f"Tinnara{nbsp}Fabrication{nbsp}LLP"
    result = rules.match("name", "Tinnara Fabrication LLP", returned, present=True)
    assert result.correct is True


def test_identifier_case_is_not_folded(rules):
    assert rules.match("identifier", "24TSTNA1234A1Z9", "24tstna1234a1z9",
                       present=True).correct is False


def test_identifier_outer_whitespace_is_stripped(rules):
    assert rules.match("identifier", "24TSTNA1234A1Z9", "  24TSTNA1234A1Z9\n",
                       present=True).correct is True


def test_a_name_is_matched_past_case_punctuation_diacritics_and_honorifics(rules):
    for returned in (
        "TINNARA FABRICATION LLP",
        "Tinnara  Fabrication,  LLP",
        "M/s Tinnara Fabrication LLP",
        "Tinnára Fabrication LLP",
    ):
        assert rules.match("name", "Tinnara Fabrication LLP", returned,
                           present=True).correct is True, returned


def test_free_text_tolerance_rule_is_published_and_applied(rules):
    result = rules.match(
        "free_text",
        "Plot 12, Synthetic Estate, Surat, Gujarat 395001, India",
        "plot 12 synthetic estate  surat gujarat 395001 india",
        present=True,
    )
    assert result.correct is True
    assert rules.group_for("free_text") == "free_text"
    assert "NFKC" in N.FREE_TEXT_TOLERANCE_RULE


def test_enum_and_boolean_normalisation(rules):
    assert rules.match("enum", "inter_state", "Inter State", present=True).correct is True
    assert rules.match("boolean", "true", "Yes", present=True).correct is True
    assert rules.match("boolean", "false", "0", present=True).correct is True
    assert rules.match("boolean", "true", "maybe", present=True).reason == "unparseable_boolean"


def test_rate_drops_a_percent_sign(rules):
    assert rules.match("rate", "18.00", "18%", present=True).correct is True
    assert rules.match("rate", "18.00", "18.0", present=True).correct is True
    assert rules.match("rate", "18.00", "0.18", present=True).correct is False


# --------------------------------------------------------------------------- #
# Absent and missing                                                           #
# --------------------------------------------------------------------------- #


def test_a_field_the_ground_truth_marks_absent_needs_an_explicit_null(rules):
    explicit_null = rules.match("free_text", None, None, present=True)
    assert explicit_null.correct is True
    assert explicit_null.reason == "absent_ok"

    empty_string = rules.match("free_text", None, "", present=True)
    assert empty_string.correct is True

    key_omitted = rules.match("free_text", None, None, present=False)
    assert key_omitted.correct is False
    assert key_omitted.reason == "absent_not_stated"

    invented = rules.match("free_text", None, "something", present=True)
    assert invented.correct is False
    assert invented.reason == "value_for_absent_field"


def test_a_missing_field_is_incorrect(rules):
    result = rules.match("identifier", "24TSTNA1234A1Z9", None, present=False)
    assert result.correct is False
    assert result.reason == "missing"


def test_an_empty_value_for_a_present_field_is_incorrect(rules):
    result = rules.match("identifier", "24TSTNA1234A1Z9", "", present=True)
    assert result.correct is False
    assert result.reason == "empty"


# --------------------------------------------------------------------------- #
# Class assignment                                                             #
# --------------------------------------------------------------------------- #


def test_classes_are_assigned_from_the_published_map(rules):
    assert rules.class_for("supplier_gstin", "identifier") == "identifier"
    assert rules.class_for("invoice_date", "date") == "date"
    assert rules.class_for("invoice_total", "money") == "amount"
    assert rules.class_for("supplier_name", "string") == "name"
    assert rules.class_for("invoice_number", "string") == "code"
    assert rules.class_for("currency", "string") == "code"
    assert rules.class_for("supplier_address", "string") == "free_text"
    assert rules.group_for(rules.class_for("supplier_address", "string")) == "free_text"
    assert rules.group_for(rules.class_for("invoice_total", "money")) == "exact_normalised"


def test_internal_line_cells_are_excluded_with_a_reason(rules):
    scored, reason = rules.line_cell_scored("amount_minor", "invoice_in_gst")
    assert scored is False
    assert "minor-unit" in reason
    assert rules.line_cell_scored("amount", "invoice_in_gst")[0] is True


def test_hsn_is_scored_only_where_the_page_prints_it(rules):
    assert rules.line_cell_scored("hsn_sac", "invoice_in_gst")[0] is True
    assert rules.line_cell_scored("hsn_sac", "invoice_eu_vat")[0] is False
    assert rules.line_cell_scored("hsn_sac", "claim_health")[0] is False
