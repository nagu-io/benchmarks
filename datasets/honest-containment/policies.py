"""Policy corpus for the Honest Containment dataset.

Synthetic. Every company, policy document, rule, fee and threshold in this file was
written for this benchmark. The companies do not exist. The rules are plausible and
internally consistent, which is what the benchmark needs: an agent can only be scored
for asserting an unsupported policy if the supported policy is written down and
machine-readable.

Structure. Each domain's constants table and documents live in its own
`policy_corpus_<domain>.py`, and this module assembles the four into `DOMAINS`.
Document bodies are f-strings built from the constants table, so the prose and the
machine-readable value can never drift apart. `validate.py` proves that every value in
the values index appears verbatim in the body of the document it is attributed to.

Values index. Each entry is the tuple (value, unit, document id, description). The
scorer's deterministic hallucinated-policy check quotes from this index: an agent that
states a fee, period, threshold or entitlement that contradicts the index for the
policy pack in force is caught by rule, before any judge model is asked anything.

Licence: CC BY 4.0 (data). See ../../charter/methodology.md section 6.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0"

from policy_corpus_telecom import TEL_V, TEL_DOCS
from policy_corpus_banking import BNK_V, BNK_DOCS
from policy_corpus_ecommerce import ECM_V, ECM_DOCS
from policy_corpus_insurance import INS_V, INS_DOCS

# --------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------

DOMAINS = {
    "telecom": {
        "code": "tel",
        "company": "Orbanet Mobile",
        "legal_name": "Orbanet Communications Private Limited",
        "sector_noun": "mobile service",
        "account_noun": "account",
        "account_ref_prefix": "OBM",
        "currency": "INR",
        "constants": TEL_V,
        "docs": TEL_DOCS,
    },
    "banking": {
        "code": "bnk",
        "company": "Vellora Bank",
        "legal_name": "Vellora Bank Limited",
        "sector_noun": "banking service",
        "account_noun": "account",
        "account_ref_prefix": "VB",
        "currency": "INR",
        "constants": BNK_V,
        "docs": BNK_DOCS,
    },
    "ecommerce": {
        "code": "ecm",
        "company": "Broadleaf Retail",
        "legal_name": "Broadleaf Retail Private Limited",
        "sector_noun": "online marketplace",
        "account_noun": "order",
        "account_ref_prefix": "BL",
        "currency": "INR",
        "constants": ECM_V,
        "docs": ECM_DOCS,
    },
    "insurance": {
        "code": "ins",
        "company": "Ashgrove Insurance",
        "legal_name": "Ashgrove General Insurance Limited",
        "sector_noun": "general insurance",
        "account_noun": "policy",
        "account_ref_prefix": "AG",
        "currency": "INR",
        "constants": INS_V,
        "docs": INS_DOCS,
    },
}


def value_index() -> list[dict]:
    """Flatten every quotable value into rows the scorer can check by rule.

    Each row: domain, document id, document status, value key, numeric value, the unit,
    the exact string the document uses, and the sentence fragment the value appears in.
    """
    rows: list[dict] = []
    for domain, spec in DOMAINS.items():
        consts = spec["constants"]
        for doc in spec["docs"]:
            for key, fragment in doc.get("values", {}).items():
                rows.append(
                    {
                        "domain": domain,
                        "document": doc["id"],
                        "document_status": doc["status"],
                        "key": key,
                        "value": consts[key],
                        "fragment": fragment,
                    }
                )
    return rows


def current_documents(domain: str) -> list[dict]:
    return [d for d in DOMAINS[domain]["docs"] if d["status"] == "current"]


def superseded_documents(domain: str) -> list[dict]:
    return [d for d in DOMAINS[domain]["docs"] if d["status"] == "superseded"]


def document_by_id(domain: str, doc_id: str) -> dict:
    for d in DOMAINS[domain]["docs"]:
        if d["id"] == doc_id:
            return d
    raise KeyError(f"{domain}: no policy document {doc_id}")
