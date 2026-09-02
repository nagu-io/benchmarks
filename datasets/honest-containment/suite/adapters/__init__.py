"""Adapter registry. Add a system by adding a module here and a block to the run config."""

from __future__ import annotations

from model_client import ModelClient, ModelSpec, NotConfigured


def build(name: str, config: dict):
    kind = config.get("adapter")
    if kind == "general_llm":
        from adapters.general_llm import GeneralLLMAdapter
        return GeneralLLMAdapter(name, ModelClient(ModelSpec.from_dict("agent", config["model"])))
    if kind == "entailment_agent":
        from adapters.entailment_agent import EntailmentAgentAdapter
        return EntailmentAgentAdapter(name,
                                      ModelClient(ModelSpec.from_dict("agent", config["model"])))
    if kind == "voice_platform":
        from adapters.voice_platform import VoicePlatformAdapter
        return VoicePlatformAdapter(name, config)
    if kind == "replay":
        from adapters.replay import ReplayAdapter
        return ReplayAdapter(name, config)
    raise NotConfigured(f"unknown adapter {kind!r} for system {name!r}")
