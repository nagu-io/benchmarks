"""Google Document AI adapter.

A processor is named by `GOOGLE_DOCAI_PROCESSOR`, in the full resource form
`projects/<project>/locations/<location>/processors/<id>` or as a bare processor
id with `GOOGLE_DOCAI_PROJECT` and `GOOGLE_DOCAI_LOCATION` set. The service
returns entities under its own type names; the shared alias table maps them onto
the schema, and that table is applied to every system.
"""

from __future__ import annotations

from typing import Any

from ..dataset import Document
from ..errors import AdapterCallError
from .base import Adapter, Availability, Response, TokenCounts, image_media_type


class GoogleDocumentAIAdapter(Adapter):
    adapter_name = "google-document-ai"
    provider = "Google Cloud"
    required_env = ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_DOCAI_PROCESSOR")
    optional_env = ("GOOGLE_DOCAI_PROJECT", "GOOGLE_DOCAI_LOCATION")
    interface_notes = (
        "Document AI takes no prompt. The processor named in "
        "GOOGLE_DOCAI_PROCESSOR is called on the same page images.",
        "Confidence is the processor's own per-entity confidence.",
        "Billing is per page, so the cost line uses the per-page price in "
        "prices.yaml rather than a token price.",
    )

    def _extra_availability(self) -> Availability:
        if self.transport is not None:
            return Availability(True, "", env_var=self.required_env[0])
        try:
            from google.cloud import documentai  # noqa: F401
        except ImportError:
            return Availability(
                False,
                "google-cloud-documentai is not installed. Install it with: "
                "pip install 'entail-bench[gcp]'",
                env_var=self.required_env[0],
            )
        return Availability(True, "", env_var=self.required_env[0])

    def _processor_name(self) -> str:
        processor = self._env("GOOGLE_DOCAI_PROCESSOR")
        if processor.startswith("projects/"):
            return processor
        project = self._env("GOOGLE_DOCAI_PROJECT")
        location = self._env("GOOGLE_DOCAI_LOCATION", "us")
        if not project:
            raise AdapterCallError(
                "GOOGLE_DOCAI_PROCESSOR is a bare id, so GOOGLE_DOCAI_PROJECT must be set"
            )
        return f"projects/{project}/locations/{location}/processors/{processor}"

    def _build_request(self, document: Document, rendered_prompt: str) -> dict:
        page = next((p for p in document.page_paths if p.exists()), None)
        if page is None and document.pdf_path and document.pdf_path.exists():
            page = document.pdf_path
        if page is None:
            raise AdapterCallError(f"no rendered page for {document.doc_id}")
        return {
            "name": self._processor_name(),
            "page_path": str(page),
            "mime_type": image_media_type(page),
        }

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        spec = self._build_request(document, rendered_prompt)
        if self.transport is not None:
            from .transport import Request

            return self.transport.send(
                Request("POST", "documentai:process", json_body=spec)
            )
        from google.api_core.client_options import ClientOptions
        from google.cloud import documentai

        location = spec["name"].split("/locations/")[1].split("/")[0]
        client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        )
        with open(spec["page_path"], "rb") as fh:
            content = fh.read()
        request = documentai.ProcessRequest(
            name=spec["name"],
            raw_document=documentai.RawDocument(content=content, mime_type=spec["mime_type"]),
        )
        result = client.process_document(request=request)
        return type(result).to_dict(result)

    # ------------------------------------------------------------------ #
    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("Document AI payload was not an object")
        doc = payload.get("document") or payload
        fields: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        for entity in doc.get("entities") or []:
            name = entity.get("type_") or entity.get("type")
            if not name:
                continue
            value = (
                entity.get("normalized_value", {}).get("text")
                if isinstance(entity.get("normalized_value"), dict) else None
            ) or entity.get("mention_text")
            properties = entity.get("properties") or []
            if properties:
                row: dict[str, Any] = {}
                for prop in properties:
                    pname = prop.get("type_") or prop.get("type")
                    if pname:
                        row[pname.split("/")[-1]] = prop.get("mention_text")
                existing = fields.get(name)
                if isinstance(existing, list):
                    existing.append(row)
                else:
                    fields[name] = [row]
            else:
                fields[name] = value
            conf = entity.get("confidence")
            if isinstance(conf, (int, float)):
                confidence[name] = float(conf)

        pages = len(doc.get("pages") or []) or document.page_count
        return Response(
            doc_id=document.doc_id,
            ok=True,
            fields=fields,
            confidence=confidence,
            raw_text=doc.get("text") or "",
            tokens=TokenCounts(),
            model_version=self.spec.model_id or self._env("GOOGLE_DOCAI_PROCESSOR", "processor"),
            pages_billed=pages,
            confidence_reported=bool(confidence),
            provider_meta={"mime_type": doc.get("mime_type")},
        )
