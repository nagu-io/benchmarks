"""Adapter contract tests, driven by the recorded fixtures in tests/fixtures/.

Every fixture is synthetic and labelled as such. No test reaches a network: the
adapters are driven through a recorded transport that replays a payload.

The contract every adapter meets:

* `availability()` is false when its environment variable is absent, with the
  reason, and no stub is produced;
* `extract(document, prompt)` returns a `Response` carrying fields, per-field
  confidence where the system reports it, raw text, token counts and latency;
* a reply that is not valid JSON is a processing failure, not a repaired answer.
"""

from __future__ import annotations

import json

import pytest

from entail_bench.adapters import ADAPTERS, build_adapter, load_registry, registry_names
from entail_bench.adapters.base import Response
from entail_bench.adapters.transport import RecordedTransport
from entail_bench.errors import AdapterUnavailable
from entail_bench.prompts import load_prompt

# model name -> (fixture file, the environment it needs to look available)
CASES = {
    "openai": ("openai-response.json", {"OPENAI_API_KEY": "synthetic-not-a-key"}),
    "anthropic": ("anthropic-response.json", {"ANTHROPIC_API_KEY": "synthetic-not-a-key"}),
    "google": ("google-response.json", {"GOOGLE_API_KEY": "synthetic-not-a-key"}),
    "mistral": ("mistral-response.json", {"MISTRAL_API_KEY": "synthetic-not-a-key"}),
    "local-vllm": ("local-openai-response.json",
                   {"LOCAL_OPENAI_BASE_URL": "http://localhost:8000/v1"}),
    "local-ollama": ("local-openai-response.json",
                     {"LOCAL_OPENAI_BASE_URL": "http://localhost:11434/v1"}),
    "aws-textract": ("aws-textract-response.json",
                     {"AWS_ACCESS_KEY_ID": "synthetic", "AWS_SECRET_ACCESS_KEY": "synthetic",
                      "AWS_REGION": "us-east-1"}),
    "azure-document-intelligence": (
        "azure-di-response.json",
        {"AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "https://synthetic.invalid",
         "AZURE_DOCUMENT_INTELLIGENCE_KEY": "synthetic-not-a-key"}),
    "google-document-ai": (
        "google-docai-response.json",
        {"GOOGLE_APPLICATION_CREDENTIALS": "/dev/null",
         "GOOGLE_DOCAI_PROCESSOR": "projects/p/locations/us/processors/x"}),
    "http-endpoint": ("http-endpoint-response.json",
                      {"ENTAIL_HTTP_ENDPOINT_URL": "https://synthetic.invalid/extract"}),
    "entail-pipeline": ("http-endpoint-response.json",
                        {"ENTAIL_HTTP_ENDPOINT_URL": "https://synthetic.invalid/extract"}),
}


@pytest.fixture
def prompt(harness_root):
    return load_prompt("messy-scan-v1.0.0.md", directory=harness_root / "prompts")


def _adapter(model, payload, monkeypatch, env, model_id="synthetic-model"):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return build_adapter(model, model_id=model_id,
                         transport=RecordedTransport(payload))


# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #


def test_every_registered_model_names_a_registered_adapter():
    for name, spec in load_registry().items():
        assert spec.adapter in ADAPTERS, f"{name} names an unknown adapter"


def test_the_registry_covers_every_system_the_pack_asks_for():
    names = set(registry_names())
    for expected in (
        "openai", "anthropic", "google", "mistral",
        "local-vllm", "local-ollama",
        "aws-textract", "azure-document-intelligence", "google-document-ai",
        "http-endpoint", "entail-pipeline",
    ):
        assert expected in names


def test_no_key_is_hard_coded_anywhere_in_the_package(harness_root):
    import re

    suspicious = re.compile(r"(sk-[A-Za-z0-9]{12,}|AKIA[0-9A-Z]{12,}|"
                            r"api_key\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"'])")
    for path in (harness_root / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not suspicious.search(text), f"{path} looks like it holds a key"


# --------------------------------------------------------------------------- #
# Availability                                                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", sorted(CASES))
def test_a_missing_environment_variable_makes_the_adapter_unavailable(model):
    adapter = build_adapter(model)
    state = adapter.availability()
    assert state.available is False
    assert state.reason
    assert state.env_var in adapter.env_vars


@pytest.mark.parametrize("model", sorted(CASES))
def test_an_unavailable_adapter_refuses_to_extract_rather_than_stub(
    model, tiny_invoice, prompt
):
    adapter = build_adapter(model)
    with pytest.raises(AdapterUnavailable):
        adapter.extract(tiny_invoice, prompt)


def test_a_local_server_needs_a_url_not_a_key(monkeypatch):
    monkeypatch.setenv("LOCAL_OPENAI_BASE_URL", "not-a-url")
    state = build_adapter("local-vllm").availability()
    assert state.available is False
    assert "http" in state.reason

    monkeypatch.setenv("LOCAL_OPENAI_BASE_URL", "http://localhost:8000/v1")
    assert build_adapter("local-vllm").availability().available is True


# --------------------------------------------------------------------------- #
# The extraction contract                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", sorted(CASES))
def test_every_adapter_meets_the_response_contract(
    model, tiny_invoice, prompt, monkeypatch, load_payload
):
    fixture, env = CASES[model]
    adapter = _adapter(model, load_payload(fixture), monkeypatch, env)
    response = adapter.extract(tiny_invoice, prompt)

    assert isinstance(response, Response)
    assert response.doc_id == tiny_invoice.doc_id
    assert response.ok is True
    assert isinstance(response.fields, dict) and response.fields
    assert isinstance(response.confidence, dict)
    assert response.latency_s is not None and response.latency_s >= 0
    assert response.model_version
    assert response.pages_billed == tiny_invoice.page_count
    assert response.requests == 1
    assert response.retries == 0
    assert isinstance(response.interface_notes, list)
    # The response must survive a round trip through the raw responses file, so
    # a disputed figure can be re-scored without re-running the model.
    restored = Response.from_dict(json.loads(json.dumps(response.as_dict())))
    assert restored.fields == response.fields
    assert restored.confidence == response.confidence


@pytest.mark.parametrize("model", sorted(CASES))
def test_every_adapter_reports_a_confidence_or_says_it_does_not(
    model, tiny_invoice, prompt, monkeypatch, load_payload
):
    fixture, env = CASES[model]
    adapter = _adapter(model, load_payload(fixture), monkeypatch, env)
    response = adapter.extract(tiny_invoice, prompt)
    if response.confidence:
        assert response.confidence_reported is True
        for value in response.confidence.values():
            assert 0.0 <= value <= 1.0
    else:
        assert response.confidence_reported is False


@pytest.mark.parametrize("model", ["openai", "anthropic", "google", "mistral", "local-vllm"])
def test_a_model_adapter_records_token_counts(
    model, tiny_invoice, prompt, monkeypatch, load_payload
):
    fixture, env = CASES[model]
    adapter = _adapter(model, load_payload(fixture), monkeypatch, env)
    response = adapter.extract(tiny_invoice, prompt)
    assert response.tokens.input and response.tokens.input > 0
    assert response.tokens.output and response.tokens.output > 0


@pytest.mark.parametrize("model", ["aws-textract", "azure-document-intelligence",
                                   "google-document-ai"])
def test_a_document_service_bills_pages_not_tokens(
    model, tiny_invoice, prompt, monkeypatch, load_payload
):
    fixture, env = CASES[model]
    adapter = _adapter(model, load_payload(fixture), monkeypatch, env)
    response = adapter.extract(tiny_invoice, prompt)
    assert response.tokens.input is None
    assert response.pages_billed == 1


def test_the_prompt_and_the_pages_reach_the_request(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-key")
    transport = RecordedTransport(load_payload("openai-response.json"))
    adapter = build_adapter("openai", model_id="synthetic-model", transport=transport)
    adapter.extract(tiny_invoice, prompt)

    body = transport.requests[0].json_body
    parts = body["messages"][0]["content"]
    text = next(p["text"] for p in parts if p["type"] == "text")
    assert "invoice_number" in text, "the schema is rendered into the prompt"
    assert tiny_invoice.doc_subtype in text
    assert any(p["type"] == "image_url" for p in parts), "the page image is attached"
    assert body["model"] == "synthetic-model"


def test_a_key_never_reaches_the_stored_record(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    from entail_bench.util import redact

    monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-value-that-must-not-be-written")
    transport = RecordedTransport(load_payload("openai-response.json"))
    adapter = build_adapter("openai", model_id="synthetic-model", transport=transport)
    response = adapter.extract(tiny_invoice, prompt)

    stored = json.dumps(redact(response.as_dict()))
    assert "sk-synthetic-value-that-must-not-be-written" not in stored
    headers = redact(dict(transport.requests[0].headers))
    assert headers["Authorization"] == "[redacted]"


def test_a_malformed_reply_is_a_processing_failure_not_a_repair(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-key")
    adapter = build_adapter(
        "openai", model_id="synthetic-model",
        transport=RecordedTransport(load_payload("openai-malformed.json")),
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.ok is False
    assert response.error_kind == "parse_error"
    assert response.fields == {}
    assert response.raw_text, "the raw text is retained for re-scoring"


def test_a_provider_error_is_retried_and_then_recorded(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-key")
    transport = RecordedTransport({"__error__": "synthetic recorded 503"})
    adapter = build_adapter(
        "openai", model_id="synthetic-model", transport=transport,
        options={"max_retries": 2, "retry_backoff_s": 0.0},
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.ok is False
    assert response.error_kind == "call_error"
    assert response.requests == 3
    assert response.retries == 3
    assert "503" in response.error


def test_the_generic_endpoint_accepts_a_wrapped_reply(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    monkeypatch.setenv("ENTAIL_HTTP_ENDPOINT_URL", "https://synthetic.invalid/extract")
    adapter = build_adapter(
        "http-endpoint", transport=RecordedTransport(load_payload("http-endpoint-wrapped.json"))
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.ok is True
    assert response.fields["invoice_number"] == "TST/26-27/0001"
    assert response.model_version == "synthetic-pipeline@2026-01-01"


def test_the_generic_endpoint_sends_the_same_prompt_and_pages(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    monkeypatch.setenv("ENTAIL_HTTP_ENDPOINT_URL", "https://synthetic.invalid/extract")
    transport = RecordedTransport(load_payload("http-endpoint-response.json"))
    adapter = build_adapter("http-endpoint", transport=transport)
    adapter.extract(tiny_invoice, prompt)
    body = transport.requests[0].json_body
    assert body["doc_id"] == tiny_invoice.doc_id
    assert body["schema"] == tiny_invoice.schema
    assert body["prompt"].startswith("You are reading a business document")
    assert body["pages"][0]["media_type"] == "image/png"


def test_textract_asks_one_query_per_schema_field(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    for name, value in CASES["aws-textract"][1].items():
        monkeypatch.setenv(name, value)
    transport = RecordedTransport(load_payload("aws-textract-response.json"))
    adapter = build_adapter("aws-textract", transport=transport)
    adapter.extract(tiny_invoice, prompt)
    queries = transport.requests[0].json_body["QueriesConfig"]["Queries"]
    aliases = {q["Alias"] for q in queries}
    assert "invoice_number" in aliases
    assert "line_items" not in aliases, "a list is not asked for as one query"


def test_textract_confidence_is_rescaled_from_a_percentage(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    for name, value in CASES["aws-textract"][1].items():
        monkeypatch.setenv(name, value)
    adapter = build_adapter(
        "aws-textract",
        transport=RecordedTransport(load_payload("aws-textract-response.json")),
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.confidence["invoice_number"] == pytest.approx(0.965)
    assert response.fields["invoice_total"] is None, "a query with no answer returns null"


def test_azure_flattens_typed_values(tiny_invoice, prompt, monkeypatch, load_payload):
    for name, value in CASES["azure-document-intelligence"][1].items():
        monkeypatch.setenv(name, value)
    adapter = build_adapter(
        "azure-document-intelligence", model_id="prebuilt-invoice",
        transport=RecordedTransport(load_payload("azure-di-response.json")),
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.fields["InvoiceId"] == "TST/26-27/0001"
    assert response.fields["InvoiceDate"] == "2026-01-15"
    assert response.fields["InvoiceTotal"] == "1250.0 INR"
    assert isinstance(response.fields["Items"], list)
    assert response.confidence["InvoiceId"] == pytest.approx(0.955)


def test_document_ai_reads_entities_and_their_properties(
    tiny_invoice, prompt, monkeypatch, load_payload
):
    for name, value in CASES["google-document-ai"][1].items():
        monkeypatch.setenv(name, value)
    adapter = build_adapter(
        "google-document-ai",
        transport=RecordedTransport(load_payload("google-docai-response.json")),
    )
    response = adapter.extract(tiny_invoice, prompt)
    assert response.fields["invoice_id"] == "TST/26-27/0001"
    assert response.fields["invoice_date"] == "2026-01-15"
    assert response.fields["line_item"] == [
        {"description": "Widget, synthetic", "amount": "1000.00"}
    ]
    assert response.confidence["supplier_name"] == pytest.approx(0.86)


def test_a_document_service_answer_is_mapped_onto_the_schema_by_the_shared_table(
    tiny_invoice, prompt, monkeypatch, load_payload, settings
):
    """The alias table is shared, so a service is scored under the schema names."""
    from entail_bench.scoring import score_document

    for name, value in CASES["azure-document-intelligence"][1].items():
        monkeypatch.setenv(name, value)
    adapter = build_adapter(
        "azure-document-intelligence", model_id="prebuilt-invoice",
        transport=RecordedTransport(load_payload("azure-di-response.json")),
    )
    response = adapter.extract(tiny_invoice, prompt)
    score = score_document(tiny_invoice, response, settings)
    by_path = {i.path: i for i in score.instances}
    assert by_path["invoice_number"].correct is True
    assert by_path["invoice_date"].correct is True
    assert score.aliased_keys, "the shared alias table moved at least one key"


def test_the_dry_run_fixture_adapter_is_available_without_any_key(tiny_invoice, prompt):
    adapter = build_adapter("dry-run-fixture")
    assert adapter.availability().available is True
    response = adapter.extract(tiny_invoice, prompt)
    assert response.provider_meta["synthetic"] is True
    assert "not a result" in response.provider_meta["warning"].lower()


def test_the_dry_run_fixture_is_deterministic_within_a_run(tiny_dataset, prompt):
    adapter = build_adapter("dry-run-fixture")
    adapter.begin_run(1)
    first = [adapter.extract(d, prompt).fields for d in tiny_dataset]
    adapter.begin_run(2)
    second = [adapter.extract(d, prompt).fields for d in tiny_dataset]
    assert first == second
