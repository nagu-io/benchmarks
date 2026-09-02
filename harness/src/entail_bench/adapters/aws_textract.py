"""AWS Textract adapter.

Textract does not take a prompt. The mechanical equivalent, and the only one
that lets the same schema be asked of every system, is the QUERIES feature: one
query per schema field, with the schema field name as the query alias, so the
answers come back under the names the scorer already uses. That is a mechanical
interface difference and it is listed in the report per charter section 5.2.
"""

from __future__ import annotations

from typing import Any

from ..dataset import Document
from ..errors import AdapterCallError
from .base import Adapter, Availability, Response, TokenCounts


class AwsTextractAdapter(Adapter):
    adapter_name = "aws-textract"
    provider = "Amazon Web Services"
    required_env = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    optional_env = ("AWS_REGION", "AWS_SESSION_TOKEN")
    interface_notes = (
        "Textract takes no prompt. One QUERIES entry per schema field is sent, "
        "with the schema field name as the query alias.",
        "Confidence is Textract's own per-answer confidence, rescaled from 0-100 "
        "to 0-1.",
        "Billing is per page, so the cost line uses the per-page price in "
        "prices.yaml rather than a token price.",
    )
    #: Textract limits QUERIES per call.
    max_queries = 30

    def _extra_availability(self) -> Availability:
        if self.transport is not None:
            return Availability(True, "", env_var=self.required_env[0])
        try:
            import boto3  # noqa: F401
        except ImportError:
            return Availability(
                False,
                "boto3 is not installed. Install it with: pip install 'entail-bench[aws]'",
                env_var=self.required_env[0],
            )
        return Availability(True, "", env_var=self.required_env[0])

    # ------------------------------------------------------------------ #
    def _queries(self, document: Document) -> list[dict]:
        queries = []
        for name, type_ in sorted(document.schema.items()):
            if type_ == "line_items":
                continue
            label = name.replace("_", " ")
            queries.append({"Text": f"What is the {label}?", "Alias": name})
        return queries[: self.max_queries]

    def _build_request(self, document: Document, rendered_prompt: str) -> dict:
        page = next((p for p in document.page_paths if p.exists()), None)
        if page is None:
            raise AdapterCallError(f"no rendered page for {document.doc_id}")
        return {
            "page_path": str(page),
            "FeatureTypes": ["QUERIES", "FORMS", "TABLES"],
            "QueriesConfig": {"Queries": self._queries(document)},
        }

    def _call(self, document: Document, rendered_prompt: str) -> Any:
        spec = self._build_request(document, rendered_prompt)
        if self.transport is not None:
            from .transport import Request

            return self.transport.send(
                Request("POST", "textract:AnalyzeDocument", json_body=spec)
            )
        import boto3

        client = boto3.client("textract", region_name=self._env("AWS_REGION", "us-east-1"))
        with open(spec["page_path"], "rb") as fh:
            payload = fh.read()
        return client.analyze_document(
            Document={"Bytes": payload},
            FeatureTypes=spec["FeatureTypes"],
            QueriesConfig=spec["QueriesConfig"],
        )

    # ------------------------------------------------------------------ #
    def _parse_response(self, payload: Any, document: Document) -> Response:
        if not isinstance(payload, dict):
            raise AdapterCallError("Textract payload was not an object")
        blocks = payload.get("Blocks") or []
        by_id = {b.get("Id"): b for b in blocks if isinstance(b, dict)}

        fields: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        for block in blocks:
            if block.get("BlockType") != "QUERY":
                continue
            alias = (block.get("Query") or {}).get("Alias")
            if not alias:
                continue
            best_text, best_conf = None, -1.0
            for rel in block.get("Relationships") or []:
                if rel.get("Type") != "ANSWER":
                    continue
                for answer_id in rel.get("Ids") or []:
                    answer = by_id.get(answer_id) or {}
                    conf = float(answer.get("Confidence") or 0.0)
                    if conf > best_conf:
                        best_conf, best_text = conf, answer.get("Text")
            fields[alias] = best_text
            if best_text is not None:
                confidence[alias] = round(min(max(best_conf / 100.0, 0.0), 1.0), 4)

        pages = payload.get("DocumentMetadata", {}).get("Pages")
        return Response(
            doc_id=document.doc_id,
            ok=True,
            fields=fields,
            confidence=confidence,
            raw_text="",
            tokens=TokenCounts(),
            model_version=self.spec.model_id or "AnalyzeDocument",
            pages_billed=int(pages) if pages else document.page_count,
            confidence_reported=bool(confidence),
            provider_meta={"analyze_document_model_version":
                           payload.get("AnalyzeDocumentModelVersion")},
        )
