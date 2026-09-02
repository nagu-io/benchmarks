"""Field classes, match rules and the cross-field validation rules.

Loads `data/field-rules.yaml`, which is published with the harness so that a
reader can check which rule scored which field.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from . import normalise as N

_DATA = Path(__file__).parent / "data" / "field-rules.yaml"


@dataclass(frozen=True)
class MatchResult:
    correct: bool
    rule: str
    reason: str
    exact_strict: bool = False
    note: str | None = None


@dataclass
class FieldRules:
    version: str
    classes: dict[str, dict]
    type_to_class: dict[str, str]
    name_overrides: list[dict]
    line_items: dict
    validation_rules: list[dict]
    total_formulas: dict
    date_order_pairs: list[list[str]]
    source_path: Path
    source_sha256: str

    # ------------------------------------------------------------------ #
    def class_for(self, field_name: str, schema_type: str) -> str:
        """The schema type decides first; the name splits the `string` type.

        A field the dataset types as `identifier`, `date`, `money`, `rate`,
        `number`, `bool` or `enum` takes that class whatever it is called. The
        name patterns exist to split the one loose type, `string`, into codes,
        names and free text.
        """
        by_type = self.type_to_class.get(schema_type, "free_text")
        if by_type != "free_text":
            return by_type
        for override in self.name_overrides:
            if re.search(override["pattern"], field_name):
                return override["class"]
        return by_type

    def group_for(self, field_class: str) -> str:
        return self.classes.get(field_class, {}).get("group", "free_text")

    def rule_for(self, field_class: str) -> str:
        return self.classes.get(field_class, {}).get("rule", "free_text")

    def line_cell_scored(self, cell: str, doc_subtype: str) -> tuple[bool, str | None]:
        excluded = self.line_items.get("excluded_cells", {})
        if cell in excluded:
            return False, excluded[cell]
        conditional = self.line_items.get("conditional_cells", {})
        if cell in conditional:
            spec = conditional[cell]
            if doc_subtype not in spec.get("scored_for_subtypes", []):
                return False, spec.get("reason", "not printed for this subtype")
        return True, None

    # ------------------------------------------------------------------ #
    def match(
        self,
        field_class: str,
        expected: Any,
        returned: Any,
        *,
        present: bool,
        display_format: str | None = None,
        decimal_separator: str | None = None,
        expected_currency: str | None = None,
        returned_currency: str | None = None,
        currency_required: bool = True,
        numeric_tolerance: str | None = None,
    ) -> MatchResult:
        """Apply the match rule for a class to one field instance."""
        rule = self.rule_for(field_class)
        expected_absent = N.is_absent(expected)

        if not present:
            # A key the system did not return at all. Charter 3.3.2: a field the
            # ground truth marks absent is correct only if the system returns an
            # explicit null or empty value, so a missing key is never correct.
            reason = "absent_not_stated" if expected_absent else "missing"
            return MatchResult(False, rule, reason)

        returned_absent = N.is_absent(returned)
        if expected_absent:
            return MatchResult(
                returned_absent, rule,
                "absent_ok" if returned_absent else "value_for_absent_field",
            )
        if returned_absent:
            return MatchResult(False, rule, "empty")

        e_text = N.as_text(expected)
        r_text = N.as_text(returned)
        if e_text is None or r_text is None:
            return MatchResult(False, rule, "type")
        strict = e_text == r_text

        if rule == "exact":
            ok = N.norm_exact(e_text) == N.norm_exact(r_text)
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict)

        if rule == "date":
            exp = N.parse_date(e_text, display_format=display_format)
            got = N.parse_date(r_text, display_format=display_format)
            if got.value is None:
                return MatchResult(False, rule, "unparseable_date", strict)
            ok = exp.value == got.value
            note = "ambiguous_day_month" if got.ambiguous else None
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict, note)

        if rule == "amount":
            exp = N.parse_amount(e_text, decimal_separator=decimal_separator)
            got = N.parse_amount(r_text, decimal_separator=decimal_separator)
            if got.value is None:
                return MatchResult(False, rule, "unparseable_amount", strict)
            tol = Decimal(numeric_tolerance) if numeric_tolerance else None
            if not N.decimals_equal(exp.value, got.value, tol):
                return MatchResult(False, rule, "value_mismatch", strict)
            exp_cur = exp.currency or expected_currency
            got_cur = got.currency or returned_currency
            if got_cur is None:
                if currency_required:
                    return MatchResult(False, rule, "currency_missing", strict)
                return MatchResult(True, rule, "match", strict, "currency_unstated")
            if exp_cur is not None and got_cur != exp_cur:
                return MatchResult(False, rule, "currency_mismatch", strict)
            return MatchResult(True, rule, "match", strict)

        if rule == "numeric":
            exp = N.parse_number(e_text, decimal_separator=decimal_separator)
            got = N.parse_number(r_text, decimal_separator=decimal_separator)
            if got is None:
                return MatchResult(False, rule, "unparseable_number", strict)
            tol = Decimal(numeric_tolerance) if numeric_tolerance else None
            ok = N.decimals_equal(exp, got, tol)
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict)

        if rule == "boolean":
            exp = N.norm_boolean(e_text)
            got = N.norm_boolean(r_text)
            if got is None:
                return MatchResult(False, rule, "unparseable_boolean", strict)
            ok = exp == got
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict)

        if rule == "enum":
            ok = N.norm_enum(e_text) == N.norm_enum(r_text)
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict)

        if rule == "name":
            ok = N.norm_name(e_text) == N.norm_name(r_text)
            return MatchResult(ok, rule, "match" if ok else "mismatch", strict)

        ok = N.norm_free_text(e_text) == N.norm_free_text(r_text)
        return MatchResult(ok, "free_text", "match" if ok else "mismatch", strict)


@lru_cache(maxsize=1)
def load_field_rules(path: str | None = None) -> FieldRules:
    from .util import sha256_file

    p = Path(path) if path else _DATA
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return FieldRules(
        version=str(raw.get("version", "0")),
        classes=raw.get("classes", {}),
        type_to_class=raw.get("type_to_class", {}),
        name_overrides=raw.get("name_overrides", []),
        line_items=raw.get("line_items", {}),
        validation_rules=raw.get("validation_rules", []),
        total_formulas=raw.get("total_formulas", {}),
        date_order_pairs=[list(p2) for p2 in raw.get("date_order_pairs", [])],
        source_path=p,
        source_sha256=sha256_file(p),
    )
