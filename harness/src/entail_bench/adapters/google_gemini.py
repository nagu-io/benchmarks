"""Google Gemini generative-language adapter."""

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


class GoogleGeminiAdapter(Adapter):
    adapter_name = "google"
    provider = "Google"
    required_env = ("GOOGLE_API_KEY",)
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    interface_notes = (
        "The prompt is sent as one text part; page images are attached as "
        "inline_data parts in page order.",
        "response_mime_type is set to application/json where the interface "
        "offers it.",
    )

    def _base_url(self) -> str:
        return (self.options.get("base_url") or self.default_base_url).rstrip("/")

    def _build_request(self, document: Document, rendered_prompt: str) -> Request:
        parts: list[dict] = [{"text": rendered_prompt}]
        for page in document_images(document, self.options.get("max_pages")):
            parts.append({
                "inline_data": {
                    "mime_type": image_media_type(page),
                    "data": encode_b64(page),
                }
            })
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": float(self.options.get("temperature", 0)),
                "maxOutputTokens": int(self.options.get("max_output_tokens", 4096)),
            },
        }
        if self.options.get("json_mode", True):
            body["generationConfig"]["responseMimeType"] = "application/json"
        url = f"{self._base_url()}/models/{self.spec.model_id}:generateContent"
        return Request(
            "POST",
            url,
            headers={
                "x-goog-api-key": self._env("GOOGLE_API_KEY"),
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
        candidates = payload.get("candidates") or []
        if not candidates:
            return Response(
                doc_id=document.doc_id, ok=False, raw_text="",
                error="provider returned no candidates", error_kind="call_error",
                model_version=payload.get("modelVersion") or self.spec.model_id,
            )
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        usage = payload.get("usageMetadata") or {}
        tokens = TokenCounts(
            input=usage.get("promptTokenCount"),
            output=usage.get("candidatesTokenCount"),
            reasoning=usage.get("thoughtsTokenCount"),
        )
        return response_from_text(
            text, document,
            tokens=tokens,
            model_version=payload.get("modelVersion") or self.spec.model_id,
            provider_meta={"finishReason": candidates[0].get("finishReason")},
        )
