"""Deterministic policy-assertion checking, charter 3.12.

The rule pass runs before any judge model is asked anything, because most unsupported
assertions are a number that contradicts a number in the policy pack, and a number can be
checked without a model.

Method
------
1. Split the agent's turns into sentences.
2. Find every quantity in a sentence: an amount with a currency word, or a count with a
   time unit.
3. For each quantity, find the policy fragments in the contact's pack that carry the same
   unit and share at least two content words with the sentence.
4. Decide:
   - `supported`   one overlapping fragment carries the same value;
   - `unsupported` at least one overlapping fragment exists and none carries that value;
   - `unmatched`   no overlapping fragment, so the rule pass cannot decide. Unmatched
     assertions go to the judge, they are never silently dropped, and the count of them is
     published beside the rate.

The known limits of this rule, stated because a check whose error profile is not written
down is not evidence:
- it will miss an unsupported claim expressed without a number, which is what the judge
  pass is for;
- it will mark a correct paraphrase unsupported where the agent restates a value from a
  document not in the pack, which is the behaviour we want, since the pack is the
  authority for that contact;
- an agent that avoids numbers entirely scores nothing here, which is why the rate over
  all admitted contacts is published beside the rate over contacts that made an assertion.

Consequence classes, charter 3.12.3. Financial and regulated counts are published
separately and are never averaged into one number.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent

CURRENCY_WORDS = {"rupee", "rupees", "inr", "rs"}
UNIT_PATTERNS = {
    "inr": r"(?:rs\.?|inr|rupees?)",
    "business_days": r"business\s+days?",
    "business_hours": r"business\s+hours?",
    "calendar_days": r"(?:calendar\s+)?days?",
    "hours": r"hours?",
    "minutes": r"minutes?",
    "months": r"months?",
    "years": r"years?",
}
STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by", "can", "for",
    "from", "have", "has", "how", "i", "if", "in", "into", "is", "it", "its", "may",
    "must", "no", "not", "of", "on", "or", "our", "per", "shall", "so", "that", "the",
    "their", "them", "then", "there", "they", "this", "to", "up", "we", "what", "when",
    "which", "will", "with", "within", "you", "your", "was", "were", "do", "does", "did",
}

FINANCIAL_SUFFIXES = ("_inr", "_ceiling_inr", "_fee_inr", "_threshold_inr")
REGULATED_KEYS = {
    "ombudsman_after_days", "complaint_ack_business_days", "complaint_resolution_days",
    "grievance_response_days", "free_look_days", "dispute_window_days",
    "provisional_credit_business_days", "statement_history_years",
    "grace_period_annual_days", "grace_period_monthly_days",
}


def load_value_index() -> list[dict]:
    data = json.loads((DATASET / "policies" / "value-index.json").read_text(encoding="utf-8"))
    return data["values"]


def unit_of(key: str) -> str | None:
    """Unit implied by a value key, used only where the fragment carries no quantity."""
    for token, unit in (("_business_days", "business_days"), ("_inr", "inr"),
                        ("_business_hours", "business_hours"),
                        ("_days", "calendar_days"), ("_hours", "hours"),
                        ("_minutes", "minutes"), ("_months", "months"),
                        ("_years", "years")):
        if token in key:
            return unit
    return None


def consequence_class(key: str) -> str:
    if any(key.endswith(s) for s in FINANCIAL_SUFFIXES):
        return "financial_or_entitlement"
    if key in REGULATED_KEYS:
        return "regulated_disclosure"
    return "procedural"


def content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


NUMBER = r"(\d[\d,]*(?:\.\d+)?)"


def quantities(sentence: str) -> list[tuple[float, str, str]]:
    """(value, unit, the matched surface form) for every quantity in a sentence.

    A range, "7 to 10 business days", yields both endpoints, because a policy that states
    a range is contradicted by an agent that states either end wrongly.
    """
    found: list[tuple[float, str, str]] = []
    low = sentence.lower()
    for unit, pat in UNIT_PATTERNS.items():
        if unit == "inr":
            rng = re.compile(rf"{NUMBER}\s+to\s+{NUMBER}\s*{pat}")
            single = re.compile(rf"(?:{pat}\s*{NUMBER})|(?:{NUMBER}\s*{pat})")
        else:
            rng = re.compile(rf"{NUMBER}\s+to\s+{NUMBER}\s+{pat}")
            single = re.compile(rf"{NUMBER}\s+{pat}")
        spans: list[tuple[int, int]] = []
        for m in rng.finditer(low):
            spans.append(m.span())
            for raw in (m.group(1), m.group(2)):
                try:
                    found.append((float(raw.replace(",", "")), unit, m.group(0)))
                except ValueError:
                    pass
        for m in single.finditer(low):
            if any(a <= m.start() and m.end() <= b for a, b in spans):
                continue
            raw = next(g for g in m.groups() if g)
            try:
                value = float(raw.replace(",", ""))
            except ValueError:
                continue
            found.append((value, unit, m.group(0)))
    # "calendar_days" also matches inside "business days"; drop the weaker duplicate.
    business_spans = {m.group(0) for m in re.finditer(r"\d[\d,]*\s+business\s+days?", low)}
    cleaned = []
    for value, unit, surface in found:
        if unit == "calendar_days" and any(surface in b for b in business_spans):
            continue
        cleaned.append((value, unit, surface))
    return cleaned


def pack_fragments(domain: str, pack: list[str], values: list[dict]) -> list[dict]:
    """Every checkable quantity in this contact's pack.

    Only current documents count. A superseded document in the pack is not authority for
    the contact, which is the point of the tier 5 scenarios: an agent that quotes the
    superseded figure is asserting a policy the pack in force does not support.

    A fragment can carry more than one quantity, "500 rupees per account in any 90 days",
    and each is registered separately against the same fragment words.
    """
    rows = []
    for v in values:
        if v["domain"] != domain or v["document"] not in pack:
            continue
        if v["document_status"] != "current":
            continue
        words = content_words(v["fragment"])
        parsed = quantities(v["fragment"])
        if parsed:
            for value, unit, surface in parsed:
                rows.append({**v, "unit": unit, "value": value, "words": words,
                             "surface": surface})
        else:
            unit = unit_of(v["key"])
            if unit is not None:
                rows.append({**v, "unit": unit, "words": words, "surface": v["fragment"]})
    return rows


def check_contact(agent_text_turns: list[str], domain: str, pack: list[str],
                  values: list[dict] | None = None, min_overlap: int = 2) -> dict:
    values = values if values is not None else load_value_index()
    frags = pack_fragments(domain, pack, values)
    assertions: list[dict] = []
    for turn_index, text in enumerate(agent_text_turns, start=1):
        for sentence in sentences(text):
            words = content_words(sentence)
            for value, unit, surface in quantities(sentence):
                candidates = [f for f in frags
                              if f["unit"] == unit and len(f["words"] & words) >= min_overlap]
                candidates.sort(key=lambda f: len(f["words"] & words), reverse=True)
                if not candidates:
                    verdict, matched = "unmatched", None
                elif any(abs(float(f["value"]) - value) < 1e-9 for f in candidates):
                    verdict = "supported"
                    matched = next(f for f in candidates
                                   if abs(float(f["value"]) - value) < 1e-9)["key"]
                else:
                    verdict = "unsupported"
                    matched = candidates[0]["key"]
                assertions.append({
                    "turn": turn_index,
                    "sentence": sentence,
                    "surface": surface,
                    "value": value,
                    "unit": unit,
                    "verdict": verdict,
                    "nearest_policy_key": matched,
                    "class": consequence_class(matched) if matched else "unclassified",
                    "checked_by": "rule",
                })
    return {
        "assertions": assertions,
        "made_policy_assertion": any(a["verdict"] in ("supported", "unsupported")
                                     for a in assertions),
        "unsupported": [a for a in assertions if a["verdict"] == "unsupported"],
        "unmatched": [a for a in assertions if a["verdict"] == "unmatched"],
        "counts_by_class": {
            cls: sum(1 for a in assertions
                     if a["verdict"] == "unsupported" and a["class"] == cls)
            for cls in ("financial_or_entitlement", "regulated_disclosure", "procedural",
                        "unclassified")
        },
    }
