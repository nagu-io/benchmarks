"""Azure AI Document Intelligence adapter.

A prebuilt or custom model is named in the config (`prebuilt-invoice`,
`prebuilt-document`, or a custom model id). The service returns its own field
names; the shared alias table in `data/field-aliases.yaml` maps them onto the
schema, and that table is applied to every system's output, not to this one only.
"""

from __future__ import annotations

import time
from typing import Any

from ..dataset import Document
from ..errors import AdapterCallError
from .base import Adapter, Availability, Response, TokenCounts
from .transport import Request


class AzureDocumentIntelligenceAdapter(Adapter):
    adapter_name = "azure-document-intelligence"
    provider = "Microsoft Azure"
    required_env = (
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    )
    api_version = "2024-11-30"
    interface_notes = (
        "Document Intelligence takes no prompt. The prebuilt or custom model "
        "named in the config is called on the same page images.",
        "Confidence is the service's own per-field confidence.",
        "Billing is per page, so the cost line uses the per-page price in "
        "prices.yaml rather than a token price.",
    )

    def _extra_availability(self) -> Availability:
        endpoint = self._env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        if not endpoint.startswith(("http://", "https://")):
            return Availability(
                False,
                "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT is set but is not an http or "
                "https URL",
                env_var="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            )
        return Availability(True, "", env_var=self.required_env[0])

    def _build_request(self, document: Document, rendered_prompt: str) -> Request:
        page = next((p for p in document.page_paths if p.exists()), None)
        if page is None and document.pdf_path and document.pdf_path.exists():
            page = document.pdf_path
        if page is None:
            raise AdapterCallError(f"no rendered page for {document.doc_id}")
        endpoint = self._env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT").rstrip("/")
        model = self.spec.model_id or "prebuilt-document"
        url = (
            f"{endpoint}/documentintelligence/documentModels/{model}:analyze"
            f"?api-version={self.options.get('api_version', self.api_version)}"
        )
        from .base import image_media_type

        with open(page, "rb") as fh:
            body = fh.read()
        return Request(
            "POST",
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self._env("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
                "Content-Type": image_media_type(page),
            },
            data=body,
            timeout=float(self.options.get("timeout_s", 180)),
        )

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        request = self._build_request(document, rendered_prompt)
        if self.transport is not None:
            return self.transport.send(request)
        return self._call_and_poll(request)

    def _call_and_poll(self, request: Request) -> Any:
        try:
            import httpx
        except ImportError as exc:                            # pragma: no cover
            raise AdapterCallError("httpx is not installed") from exc
        poll_interval = float(self.options.get("poll_interval_s", 2.0))
        poll_limit = int(self.options.get("poll_attempts", 60))
        with httpx.Client(timeout=request.timeout) as client:
            started = client.post(request.url, headers=request.headers, content=request.data)
            if started.status_code >= 400:
                raise AdapterCallError(f"HTTP {started.status_code}: {started.text[:400]}")
            location = started.headers.get("operation-location")
            if not location:
                raise AdapterCallError("no operation-location header on the analyze response")
            key_header = {
                "Ocp-Apim-Subscription-Key": self._env("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            }
            for _ in range(poll_limit):
                time.sleep(poll_interval)
                polled = client.get(location, headers=key_header)
                if polled.status_code >= 400:
                    raise AdapterCallError(f"HTTP {polled.status_code}: {polled.text[:400]}")
                body = polled.json()
                status = body.get("status")
                if status == "succeeded":
                    return body
                if status == "failed":
                    raise AdapterCallError(f"analysis failed: {body.get('error')}")
            raise AdapterCallError("analysis did not finish within the poll limit")

    # ------------------------------------------------------------------ #
    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("Document Intelligence payload was not an object")
        result = payload.get("analyzeResult") or payload
        documents = result.get("documents") or []
        fields: dict[str, Any] = {}
        confidence: dict[str, float] = {}

        if documents:
            for name, spec in (documents[0].get("fields") or {}).items():
                value, conf = _flatten_field(spec)
                fields[name] = value
                if conf is not None:
                    confidence[name] = conf
        else:
            for pair in result.get("keyValuePairs") or []:
                key = ((pair.get("key") or {}).get("content") or "").strip()
                if not key:
                    continue
                fields[key] = (pair.get("value") or {}).get("content")
                if pair.get("confidence") is not None:
                    confidence[key] = float(pair["confidence"])

        pages = len(result.get("pages") or []) or document.page_count
        return Response(
            doc_id=document.doc_id,
            ok=True,
            fields=fields,
            confidence=confidence,
            raw_text=result.get("content") or "",
            tokens=TokenCounts(),
            model_version=result.get("modelId") or self.spec.model_id,
            pages_billed=pages,
            confidence_reported=bool(confidence),
            provider_meta={"apiVersion": result.get("apiVersion")},
        )


def _flatten_field(spec: Any) -> tuple[Any, float | None]:
    """One Document Intelligence field to a plain value plus its confidence."""
    if not isinstance(spec, dict):
        return spec, None
    conf = spec.get("confidence")
    conf = float(conf) if isinstance(conf, (int, float)) else None
    kind = spec.get("type")
    if kind == "array":
        rows = []
        for item in spec.get("valueArray") or []:
            row, _ = _flatten_field(item)
            rows.append(row)
        return rows, conf
    if kind == "object":
        obj = {}
        for k, v in (spec.get("valueObject") or {}).items():
            obj[k], _ = _flatten_field(v)
        return obj, conf
    for key in (
        "valueString", "valueDate", "valueNumber", "valueInteger",
        "valueCurrency", "valueBoolean", "valuePhoneNumber", "valueAddress",
        "valueSelectionMark", "valueCountryRegion", "valueTime",
    ):
        if key in spec:
            value = spec[key]
            if key == "valueCurrency" and isinstance(value, dict):
                amount = value.get("amount")
                code = value.get("currencyCode") or value.get("currencySymbol") or ""
                return (f"{amount} {code}".strip() if amount is not None else None), conf
            if isinstance(value, dict):
                return value.get("content") or spec.get("content"), conf
            return value, conf
    return spec.get("content"), conf
