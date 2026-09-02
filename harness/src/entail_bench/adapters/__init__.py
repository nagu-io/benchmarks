"""Adapter registry.

Every system under test is reached through one interface,
`Adapter.extract(document, prompt) -> Response`, so a hosted model, a document
service, a self-hosted model and a partner's own pipeline are scored by the same
code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ..errors import ConfigError
from .anthropic import AnthropicAdapter
from .aws_textract import AwsTextractAdapter
from .azure_di import AzureDocumentIntelligenceAdapter
from .base import Adapter, AdapterSpec, Availability, Response, TokenCounts
from .fixture import FIXTURE_MODEL_NAME, DryRunFixtureAdapter
from .google_docai import GoogleDocumentAIAdapter
from .google_gemini import GoogleGeminiAdapter
from .http_endpoint import HttpEndpointAdapter
from .openai_family import LocalOpenAIAdapter, MistralAdapter, OpenAICompatibleAdapter

_REGISTRY_FILE = Path(__file__).parents[1] / "data" / "models.yaml"

ADAPTERS: dict[str, type[Adapter]] = {
    "openai": OpenAICompatibleAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleGeminiAdapter,
    "mistral": MistralAdapter,
    "local-openai": LocalOpenAIAdapter,
    "aws-textract": AwsTextractAdapter,
    "azure-document-intelligence": AzureDocumentIntelligenceAdapter,
    "google-document-ai": GoogleDocumentAIAdapter,
    "http-endpoint": HttpEndpointAdapter,
    "dry-run-fixture": DryRunFixtureAdapter,
}


@lru_cache(maxsize=1)
def load_registry(path: str | None = None) -> dict[str, AdapterSpec]:
    p = Path(path) if path else _REGISTRY_FILE
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    specs: dict[str, AdapterSpec] = {}
    for row in raw.get("models") or []:
        spec = AdapterSpec(
            name=row["name"],
            adapter=row["adapter"],
            provider=row.get("provider", "unknown"),
            model_id=row.get("model_id"),
            kind=row.get("kind", "model"),
            env_vars=list(row.get("env_vars") or []),
            optional_env_vars=list(row.get("optional_env_vars") or []),
            price_key=row.get("price_key"),
            options=dict(row.get("options") or {}),
            note=str(row.get("note", "")).strip(),
        )
        specs[spec.name] = spec
    return specs


def registry_names() -> list[str]:
    return sorted(load_registry())


def get_spec(name: str) -> AdapterSpec:
    registry = load_registry()
    if name in registry:
        return registry[name]
    raise ConfigError(
        f"unknown model {name!r}. Known models: {', '.join(registry_names())}. "
        "Add a row to src/entail_bench/data/models.yaml to register another."
    )


def build_adapter(
    name: str,
    *,
    model_id: str | None = None,
    options: dict | None = None,
    transport=None,
) -> Adapter:
    spec = get_spec(name)
    if model_id:
        spec = AdapterSpec(**{**spec.__dict__, "model_id": model_id})
    cls = ADAPTERS.get(spec.adapter)
    if cls is None:
        raise ConfigError(
            f"model {name!r} names adapter {spec.adapter!r}, which is not registered"
        )
    return cls(spec, options=options, transport=transport)


def availability_for(name: str, *, model_id: str | None = None) -> Availability:
    return build_adapter(name, model_id=model_id).availability()


def is_synthetic(name: str) -> bool:
    return name == FIXTURE_MODEL_NAME


__all__ = [
    "ADAPTERS",
    "Adapter",
    "AdapterSpec",
    "Availability",
    "FIXTURE_MODEL_NAME",
    "Response",
    "TokenCounts",
    "availability_for",
    "build_adapter",
    "get_spec",
    "is_synthetic",
    "load_registry",
    "registry_names",
]
