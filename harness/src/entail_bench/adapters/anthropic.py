"""Anthropic messages adapter."""

from __future__ import annotations

from typing import Any

from ..dataset import Document
from ..errors import AdapterCallError
from .base import (
    Adapter,
    Response,
    TokenCounts,
    document_images,
    encode_b64,
    image_media_type,
    response_from_text,
)
from .transport import HttpTransport, Request


class AnthropicAdapter(Adapter):
    adapter_name = "anthropic"
    provider = "Anthropic"
    required_env = ("ANTHROPIC_API_KEY",)
    default_base_url = "https://api.anthropic.com/v1"
    api_version = "2023-06-01"
    interface_notes = (
        "The prompt is sent as the single user message; page images are attached "
        "as base64 image blocks in page order.",
        "No structured-output mode is requested; the prompt's JSON instruction is "
        "the only constraint, as it is for every model.",
    )

    def _base_url(self) -> str:
        return (self.options.get("base_url") or self.default_base_url).rstrip("/")

    def _build_request(self, document: Document, rendered_prompt: str) -> Request:
        content: list[dict] = []
        for page in document_images(document, self.options.get("max_pages")):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type(page),
                    "data": encode_b64(page),
                },
            })
        content.append({"type": "text", "text": rendered_prompt})
        body: dict[str, Any] = {
            "model": self.spec.model_id,
            "max_tokens": int(self.options.get("max_output_tokens", 4096)),
            "temperature": float(self.options.get("temperature", 0)),
            "messages": [{"role": "user", "content": content}],
        }
        return Request(
            "POST",
            f"{self._base_url()}/messages",
            headers={
                "x-api-key": self._env("ANTHROPIC_API_KEY"),
                "anthropic-version": self.api_version,
                "Content-Type": "application/json",
            },
            json_body=body,
            timeout=float(self.options.get("timeout_s", 180)),
        )

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        transport = self.transport or HttpTransport()
        return transport.send(self._build_request(document, rendered_prompt))

    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("provider payload was not an object")
        blocks = payload.get("content") or []
        text = "".join(
            b.get("text", "") for b in blocks
            if isinstance(b, dict) and b.get("type") == "text"
        )
        usage = payload.get("usage") or {}
        tokens = TokenCounts(
            input=usage.get("input_tokens"),
            output=usage.get("output_tokens"),
            reasoning=usage.get("thinking_tokens"),
        )
        return response_from_text(
            text, document,
            tokens=tokens,
            model_version=payload.get("model") or self.spec.model_id,
            provider_meta={"id": payload.get("id"), "stop_reason": payload.get("stop_reason")},
        )
