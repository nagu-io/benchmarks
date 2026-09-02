"""Generic HTTP endpoint adapter.

Any IDP vendor, and our own pipeline, scored by exactly the code that scores a
hosted model. The endpoint receives a POST with a JSON body:

    {
      "doc_id": "msc-inv-in_gst-0001",
      "doc_type": "invoice",
      "doc_subtype": "invoice_in_gst",
      "page_count": 1,
      "schema": {"invoice_number": "string", ...},
      "prompt": "<the rendered suite prompt, identical for every system>",
      "pages": [{"filename": "page-01.jpg", "media_type": "image/jpeg",
                 "content_base64": "..."}]
    }

and replies with:

    {
      "fields": {"invoice_number": "TI/25-26/7822", ...},
      "confidence": {"invoice_number": 0.97, ...},
      "model_version": "our-pipeline@2026-09-02",
      "pages_billed": 1,
      "tokens": {"input": 3120, "output": 480}
    }

`fields` and `confidence` are the only required keys. Anything else is optional
and is recorded when present. The same reply shape is accepted inside a
`result`, `output` or `data` wrapper.
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
    split_answer,
)
from .transport import HttpTransport, Request


class HttpEndpointAdapter(Adapter):
    adapter_name = "http-endpoint"
    provider = "generic"
    required_env = ("ENTAIL_HTTP_ENDPOINT_URL",)
    optional_env = ("ENTAIL_HTTP_ENDPOINT_TOKEN",)
    interface_notes = (
        "The endpoint receives the same rendered prompt and the same page images "
        "as every model, in one JSON POST.",
        "Cost is taken from the per-document or per-page price recorded for this "
        "endpoint in prices.yaml.",
    )

    def _extra_availability(self) -> Availability:
        url = self._env("ENTAIL_HTTP_ENDPOINT_URL")
        if not url.startswith(("http://", "https://")):
            return Availability(
                False,
                "ENTAIL_HTTP_ENDPOINT_URL is set but is not an http or https URL",
                env_var="ENTAIL_HTTP_ENDPOINT_URL",
            )
        return Availability(True, "", env_var="ENTAIL_HTTP_ENDPOINT_URL")

    def _build_request(self, document: Document, rendered_prompt: str) -> Request:
        pages = []
        for page in document_images(document, self.options.get("max_pages")):
            pages.append({
                "filename": page.name,
                "media_type": image_media_type(page),
                "content_base64": encode_b64(page),
            })
        headers = {"Content-Type": "application/json"}
        token = self._env("ENTAIL_HTTP_ENDPOINT_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = {
            "doc_id": document.doc_id,
            "doc_type": document.doc_type,
            "doc_subtype": document.doc_subtype,
            "page_count": document.page_count,
            "schema": document.schema,
            "prompt": rendered_prompt,
            "pages": pages,
        }
        if self.spec.model_id:
            body["model"] = self.spec.model_id
        return Request(
            "POST",
            self._env("ENTAIL_HTTP_ENDPOINT_URL"),
            headers=headers,
            json_body=body,
            timeout=float(self.options.get("timeout_s", 180)),
        )

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        transport = self.transport or HttpTransport()
        return transport.send(self._build_request(document, rendered_prompt))

    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("endpoint payload was not an object")
        body = payload
        for wrapper in ("result", "output", "data"):
            inner = payload.get(wrapper)
            if isinstance(inner, dict) and ("fields" in inner or "confidence" in inner):
                body = inner
                break
        if body.get("error"):
            return Response(
                doc_id=document.doc_id, ok=False, raw_text="",
                error=str(body["error"]), error_kind="call_error",
                model_version=body.get("model_version"),
            )
        fields, confidence, reported = split_answer(body)
        tokens_raw = body.get("tokens") or {}
        return Response(
            doc_id=document.doc_id,
            ok=True,
            fields=fields,
            confidence=confidence,
            raw_text=body.get("raw_text") or "",
            tokens=TokenCounts(
                tokens_raw.get("input"), tokens_raw.get("output"), tokens_raw.get("reasoning")
            ),
            model_version=body.get("model_version") or self.spec.model_id,
            pages_billed=body.get("pages_billed") or document.page_count,
            confidence_reported=reported,
            provider_meta={k: v for k, v in body.items()
                           if k not in {"fields", "confidence", "raw_text", "tokens"}},
        )
