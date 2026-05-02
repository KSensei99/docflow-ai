"""
Extractor Service — Pipeline Orchestrator
==========================================
Coordinates: OCR → LLM extraction → semantic matching → confidence scoring

Entry point: extractor.process(file_path)
"""

import time
from pathlib import Path

from loguru import logger

from app.models.invoice import InvoiceData, LineItem, ProcessingResult
from app.services.ocr import ocr_service
from app.services.llm import llm_service
from app.services.matcher import matcher
from app.services.scorer import scorer
from app.config import settings


class ExtractorService:
    """Runs the full document intelligence pipeline for one file."""

    async def process(self, file_path: Path) -> ProcessingResult:
        start_ms = int(time.time() * 1000)
        filename = file_path.name

        result = ProcessingResult(
            filename=filename,
            file_type=file_path.suffix.lower().lstrip("."),
            llm_model=settings.ollama_model,
        )

        try:
            # ── Step 1: OCR ────────────────────────────────────────────────
            logger.info(f"[{filename}] Step 1/4: OCR extraction")
            raw_text, ocr_engine = ocr_service.extract(file_path)
            result.raw_text = raw_text
            result.ocr_engine = ocr_engine
            logger.info(f"[{filename}] OCR: {len(raw_text)} chars via {ocr_engine}")

            if not raw_text.strip():
                result.status = "error"
                result.review_notes = "OCR returned empty text"
                return result

            # ── Step 2: LLM Extraction ─────────────────────────────────────
            logger.info(f"[{filename}] Step 2/4: LLM structured extraction")
            extracted_dict = await llm_service.extract_invoice(raw_text)

            if not extracted_dict:
                result.status = "error"
                result.review_notes = "LLM returned empty extraction"
                return result

            result.invoice_data = self._dict_to_invoice_data(extracted_dict)

            # ── Step 3: Semantic Matching ──────────────────────────────────
            logger.info(f"[{filename}] Step 3/4: Semantic catalog matching")
            result.invoice_data = await self._match_line_items(result.invoice_data)

            # ── Step 4: Confidence Scoring ─────────────────────────────────
            logger.info(f"[{filename}] Step 4/4: Confidence scoring")
            llm_scores = await llm_service.score_confidence(raw_text, extracted_dict)
            result = scorer.score(result, llm_scores)

        except Exception as e:
            logger.exception(f"[{filename}] Pipeline error: {e}")
            result.status = "error"
            result.review_notes = f"Pipeline error: {str(e)}"

        finally:
            result.processing_time_ms = int(time.time() * 1000) - start_ms
            logger.info(
                f"[{filename}] Done in {result.processing_time_ms}ms "
                f"| confidence={result.overall_confidence:.2f} "
                f"| status={result.review_status}"
            )

        return result

    def _dict_to_invoice_data(self, data: dict) -> InvoiceData:
        """Safely convert LLM output dict → validated InvoiceData."""
        line_items_raw = data.pop("line_items", []) or []
        line_items = []

        for item in line_items_raw:
            if not isinstance(item, dict):
                continue
            line_items.append(
                LineItem(
                    description=str(item.get("description", "")),
                    quantity=self._safe_float(item.get("quantity")),
                    unit_price=self._safe_float(item.get("unit_price")),
                    total=self._safe_float(item.get("total")),
                )
            )

        return InvoiceData(
            invoice_number=data.get("invoice_number"),
            vendor_name=data.get("vendor_name"),
            vendor_address=data.get("vendor_address"),
            vendor_email=data.get("vendor_email"),
            invoice_date=data.get("invoice_date"),
            due_date=data.get("due_date"),
            subtotal=self._safe_float(data.get("subtotal")),
            tax=self._safe_float(data.get("tax")),
            total_amount=self._safe_float(data.get("total_amount")),
            currency=data.get("currency", "USD"),
            payment_terms=data.get("payment_terms"),
            notes=data.get("notes"),
            line_items=line_items,
        )

    async def _match_line_items(self, invoice: InvoiceData) -> InvoiceData:
        """Run semantic matching on every line item."""
        if not invoice.line_items:
            return invoice

        for item in invoice.line_items:
            if not item.description:
                continue

            match = matcher.match(item.description)
            if match:
                item.match_confidence = match.similarity_score
                if match.is_match:
                    item.matched_product_id = match.catalog_item.id
                    item.matched_product_name = match.catalog_item.name

        return invoice

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            return None


extractor = ExtractorService()
