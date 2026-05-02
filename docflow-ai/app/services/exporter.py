"""
Exporter Service
================
Pushes structured results to:
  • CSV files (local output dir)
  • Webhook (configurable URL)
  • Both simultaneously
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings
from app.models.invoice import ProcessingResult


class ExporterService:

    # ── CSV Export ────────────────────────────────────────────────────────────

    def to_csv(self, result: ProcessingResult) -> Path:
        """Write invoice + line items to a CSV file. Returns file path."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.job_id[:8]}_{ts}.csv"
        output_path = settings.output_dir / filename

        inv = result.invoice_data
        rows = []

        # One row per line item
        for idx, item in enumerate(inv.line_items or []):
            rows.append({
                "job_id": result.job_id,
                "filename": result.filename,
                "invoice_number": inv.invoice_number or "",
                "vendor_name": inv.vendor_name or "",
                "invoice_date": inv.invoice_date or "",
                "due_date": inv.due_date or "",
                "currency": inv.currency,
                "total_amount": inv.total_amount or "",
                "tax": inv.tax or "",
                "subtotal": inv.subtotal or "",
                "line_item_idx": idx + 1,
                "line_description": item.description,
                "line_qty": item.quantity or "",
                "line_unit_price": item.unit_price or "",
                "line_total": item.total or "",
                "matched_product_id": item.matched_product_id or "",
                "matched_product_name": item.matched_product_name or "",
                "match_confidence": item.match_confidence,
                "overall_confidence": result.overall_confidence,
                "review_status": result.review_status.value,
                "ocr_engine": result.ocr_engine,
                "llm_model": result.llm_model,
                "processing_time_ms": result.processing_time_ms,
            })

        if not rows:
            # No line items — still write one summary row
            rows.append({
                "job_id": result.job_id,
                "filename": result.filename,
                "invoice_number": inv.invoice_number or "",
                "vendor_name": inv.vendor_name or "",
                "invoice_date": inv.invoice_date or "",
                "due_date": inv.due_date or "",
                "currency": inv.currency,
                "total_amount": inv.total_amount or "",
                "tax": inv.tax or "",
                "subtotal": inv.subtotal or "",
                "line_item_idx": "",
                "line_description": "",
                "line_qty": "",
                "line_unit_price": "",
                "line_total": "",
                "matched_product_id": "",
                "matched_product_name": "",
                "match_confidence": "",
                "overall_confidence": result.overall_confidence,
                "review_status": result.review_status.value,
                "ocr_engine": result.ocr_engine,
                "llm_model": result.llm_model,
                "processing_time_ms": result.processing_time_ms,
            })

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV exported: {output_path}")
        return output_path

    # ── Webhook Push ──────────────────────────────────────────────────────────

    async def to_webhook(self, result: ProcessingResult) -> bool:
        """POST structured result JSON to configured webhook URL."""
        if not settings.webhook_enabled or not settings.webhook_url:
            return False

        payload = {
            "event": "invoice.processed",
            "job_id": result.job_id,
            "filename": result.filename,
            "review_status": result.review_status.value,
            "overall_confidence": result.overall_confidence,
            "invoice": result.invoice_data.model_dump(),
            "metadata": {
                "ocr_engine": result.ocr_engine,
                "llm_model": result.llm_model,
                "processing_time_ms": result.processing_time_ms,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    settings.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "X-Source": "docflow-ai"},
                )
                response.raise_for_status()
                logger.info(f"Webhook sent: {settings.webhook_url} → {response.status_code}")
                return True
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return False

    # ── Export Both ───────────────────────────────────────────────────────────

    async def export(self, result: ProcessingResult) -> dict:
        csv_path = self.to_csv(result)
        webhook_ok = await self.to_webhook(result)

        return {
            "csv_file": str(csv_path),
            "webhook_sent": webhook_ok,
        }


exporter = ExporterService()
