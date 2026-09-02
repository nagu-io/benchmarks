"""Adapters that speak the OpenAI chat-completions shape.

OpenAI itself, Mistral, and any OpenAI-compatible local server, which covers
vLLM (`--api-server`) and Ollama (`/v1`). One request builder, one parser, three
registrations, so a local model is scored by exactly the code that scores a
hosted one.
"""

from __future__ import annotations

from typing import Any

from ..dataset import Document
from ..errors import AdapterCallError
from .base import (
    Adapter,
    Availability,
    Response,
    TokenCounts,
    document_images,
    encode_b64,
    image_media_type,
    response_from_text,
)
from .transport import HttpTransport, Request


class OpenAICompatibleAdapter(Adapter):
    """Chat completions with image parts."""

    adapter_name = "openai"
    provider = "OpenAI"
    required_env = ("OPENAI_API_KEY",)
    default_base_url = "https://api.openai.com/v1"
    interface_notes = (
        "The prompt is sent as the single user message; page images are attached "
        "as image_url parts in page order.",
        "JSON object response mode is requested where the interface offers it.",
    )

    def _base_url(self) -> str:
        return (self.options.get("base_url") or self.default_base_url).rstrip("/")

    def _api_key(self) -> str:
        return self._env(self.env_vars[0]) if self.env_vars else ""

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    def _build_request(self, document: Document, rendered_prompt: str) -> Request:
        parts: list[dict] = [{"type": "text", "text": rendered_prompt}]
        for page in document_images(document, self.options.get("max_pages")):
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_media_type(page)};base64,{encode_b64(page)}",
                    "detail": self.options.get("image_detail", "high"),
                },
            })
        body: dict[str, Any] = {
            "model": self.spec.model_id,
            "messages": [{"role": "user", "content": parts}],
            "max_tokens": int(self.options.get("max_output_tokens", 4096)),
            "temperature": float(self.options.get("temperature", 0)),
        }
        if self.options.get("json_mode", True):
            body["response_format"] = {"type": "json_object"}
        return Request(
            "POST",
            f"{self._base_url()}/chat/completions",
            headers=self._headers(),
            json_body=body,
            timeout=float(self.options.get("timeout_s", 180)),
        )

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        transport = self.transport or HttpTransport()
        return transport.send(self._build_request(document, rendered_prompt))

    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("provider payload was not an object")
        choices = payload.get("choices") or []
        if not choices:
            return Response(
                doc_id=document.doc_id, ok=False,
                raw_text="", error="provider returned no choices",
                error_kind="call_error",
                model_version=payload.get("model"),
            )
        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        if isinstance(text, list):
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        usage = payload.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        tokens = TokenCounts(
            input=usage.get("prompt_tokens"),
            output=usage.get("completion_tokens"),
            reasoning=details.get("reasoning_tokens"),
        )
        return response_from_text(
            text, document,
            tokens=tokens,
            model_version=payload.get("model") or self.spec.model_id,
            provider_meta={"id": payload.get("id"), "finish_reason": choices[0].get("finish_reason")},
        )


class MistralAdapter(OpenAICompatibleAdapter):
    adapter_name = "mistral"
    provider = "Mistral"
    required_env = ("MISTRAL_API_KEY",)
    default_base_url = "https://api.mistral.ai/v1"
    interface_notes = (
        "The prompt is sent as the single user message; page images are attached "
        "as image_url parts in page order.",
        "JSON object response mode is requested where the interface offers it.",
    )


class LocalOpenAIAdapter(OpenAICompatibleAdapter):
    """An OpenAI-compatible server the partner runs: vLLM, Ollama, or similar.

    The required environment variable is the base URL, because that is the piece
    without which the adapter cannot run. A key is optional, since a local server
    often has none.
    """

    adapter_name = "local-openai"
    provider = "self-hosted"
    required_env = ("LOCAL_OPENAI_BASE_URL",)
    optional_env = ("LOCAL_OPENAI_API_KEY",)
    interface_notes = (
        "The prompt is sent as the single user message; page images are attached "
        "as image_url parts in page order.",
        "Self-hosted server, so the cost line uses the compute rate in prices.yaml "
        "and the measured occupancy, not a token price.",
    )

    def _base_url(self) -> str:
        return (self._env("LOCAL_OPENAI_BASE_URL") or self.default_base_url).rstrip("/")

    def _api_key(self) -> str:
        return self._env("LOCAL_OPENAI_API_KEY")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _extra_availability(self) -> Availability:
        url = self._env("LOCAL_OPENAI_BASE_URL")
        if not url.startswith(("http://", "https://")):
            return Availability(
                False,
                "LOCAL_OPENAI_BASE_URL is set but is not an http or https URL",
                env_var="LOCAL_OPENAI_BASE_URL",
            )
        return Availability(True, "", env_var="LOCAL_OPENAI_BASE_URL")
