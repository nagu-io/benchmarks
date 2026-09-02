"""Shared test fixtures.

Every fixture used here is synthetic and is labelled as such in
`tests/fixtures/README.md`. No test calls a network.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from entail_bench.dataset import Document, load_dataset
from entail_bench.scoring import ScoringSettings

FIXTURES = Path(__file__).parent / "fixtures"
TINY = FIXTURES / "tiny-dataset"
HARNESS_ROOT = Path(__file__).resolve().parents[1]

# The tiny dataset's page images are generated, not committed: this repository
# carries no binary files. See tests/fixtures/tiny-dataset/make-pages.py.
_spec = importlib.util.spec_from_file_location(
    "entail_bench_make_pages", TINY / "make-pages.py"
)
_MAKE_PAGES = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_MAKE_PAGES)
_MAKE_PAGES.ensure_pages(TINY)


@pytest.fixture(autouse=True)
def no_provider_keys(monkeypatch):
    """Strip every credential from the environment for the whole suite.

    Tests must never reach a provider, and an adapter must report itself
    unavailable rather than fall back to anything.
    """
    for name in list(os.environ):
        if any(token in name.upper() for token in (
            "OPENAI", "ANTHROPIC", "GOOGLE", "MISTRAL", "AWS", "AZURE",
            "ENTAIL_HTTP", "LOCAL_OPENAI",
        )):
            monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail any test that opens a network connection.

    The suite must pass with no network. Adapters are driven through a recorded
    transport; nothing here may reach a provider.
    """
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError(
            "a test tried to open a network connection. The suite runs offline: "
            "drive the adapter through RecordedTransport instead."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse, raising=False)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse, raising=False)
    monkeypatch.setattr(socket, "create_connection", refuse, raising=False)
    yield


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def harness_root() -> Path:
    return HARNESS_ROOT


@pytest.fixture
def tiny_dataset():
    return load_dataset(TINY, split=None, require_rendered=True)


@pytest.fixture
def tiny_invoice(tiny_dataset):
    return tiny_dataset.by_id("tiny-inv-0001")


@pytest.fixture
def settings() -> ScoringSettings:
    return ScoringSettings(
        confidence_threshold=0.85,
        calibration_bins=10,
        audit_rate=0.0,
        currency_required=True,
        required_fields="all",
        validation=True,
    )


@pytest.fixture
def load_payload():
    def _load(name: str) -> dict:
        with open(FIXTURES / name, encoding="utf-8") as fh:
            return json.load(fh)
    return _load


def make_document(**overrides) -> Document:
    """A minimal document for a unit test of one match rule."""
    base = dict(
        doc_id="unit-0001",
        doc_type="invoice",
        doc_subtype="invoice_tiny",
        tier=1,
        languages=["en"],
        page_count=1,
        split="public_sample",
        schema={},
        fields={},
        display_formats={"date": "%d/%m/%Y", "decimal_separator": "."},
        root=TINY,
    )
    base.update(overrides)
    return Document(**base)
