"""
Confidence Scorer
=================
Computes an overall confidence score for a processed invoice.
Uses a weighted combination of:
  • LLM self-reported field scores
  • Structural validation (required fields present)
  • Numeric consistency (line items sum to total)
  • Catalog match rates
"""

from app.models.invoice import ProcessingResult, ReviewStatus
from app.config import settings
from loguru import logger


# Fields required for a "complete" invoice — weight them
REQUIRED_FIELD_WEIGHTS = {
    "vendor_name": 0.20,
    "invoice_number": 0.15,
    "invoice_date": 0.15,
    "total_amount": 0.20,
    "line_items": 0.15,
    "due_date": 0.05,
    "subtotal": 0.05,
    "vendor_address": 0.05,
}


class ConfidenceScorer:
    """Multi-factor confidence scoring for invoice extractions."""

    def score(
        self,
        result: ProcessingResult,
        llm_scores: dict[str, float],
    ) -> ProcessingResult:
        """
        Mutates result in-place: sets overall_confidence, field_confidences,
        and review_status.
        """
        scores = {}

        # ── 1. LLM self-reported scores ────────────────────────────────────
        for field, weight in REQUIRED_FIELD_WEIGHTS.items():
            llm_s = llm_scores.get(field, 0.5)  # default 0.5 if not reported
            scores[field] = llm_s

        # ── 2. Structural validation ───────────────────────────────────────
        structural_score = self._structural_check(result)
        scores["structural"] = structural_score

        # ── 3. Numeric consistency ─────────────────────────────────────────
        numeric_score = self._numeric_check(result)
        scores["numeric_consistency"] = numeric_score

        # ── 4. Catalog match rate ──────────────────────────────────────────
        match_score = self._catalog_match_score(result)
        scores["catalog_match_rate"] = match_score

        # ── Weighted overall ───────────────────────────────────────────────
        llm_overall = llm_scores.get("overall", 0.5)
        overall = (
            llm_overall * 0.40
            + structural_score * 0.25
            + numeric_score * 0.20
            + match_score * 0.15
        )
        overall = round(max(0.0, min(1.0, overall)), 4)

        result.field_confidences = scores
        result.overall_confidence = overall

        # ── Review routing ─────────────────────────────────────────────────
        if overall >= settings.confidence_threshold:
            result.review_status = ReviewStatus.approved
            logger.info(f"Auto-approved: {result.job_id} (score={overall:.2f})")
        else:
            result.review_status = ReviewStatus.needs_review
            low_fields = [
                f for f, s in scores.items()
                if isinstance(s, float) and s < 0.6
            ]
            result.review_notes = (
                f"Low confidence ({overall:.2f} < {settings.confidence_threshold}). "
                f"Check fields: {', '.join(low_fields)}"
            )
            logger.warning(
                f"Flagged for review: {result.job_id} "
                f"(score={overall:.2f}, low: {low_fields})"
            )

        return result

    def _structural_check(self, result: ProcessingResult) -> float:
        """Score based on which required fields are present."""
        inv = result.invoice_data
        present = 0
        total = len(REQUIRED_FIELD_WEIGHTS)

        checks = {
            "vendor_name": bool(inv.vendor_name),
            "invoice_number": bool(inv.invoice_number),
            "invoice_date": bool(inv.invoice_date),
            "total_amount": inv.total_amount is not None,
            "line_items": len(inv.line_items) > 0,
            "due_date": bool(inv.due_date),
            "subtotal": inv.subtotal is not None,
            "vendor_address": bool(inv.vendor_address),
        }

        for field, ok in checks.items():
            if ok:
                present += 1

        return round(present / total, 3)

    def _numeric_check(self, result: ProcessingResult) -> float:
        """Check if line items sum ≈ subtotal, and subtotal + tax ≈ total."""
        inv = result.invoice_data
        score = 1.0

        # Line items sum check
        if inv.line_items and inv.subtotal is not None:
            items_total = sum(
                item.total or 0.0 for item in inv.line_items
            )
            if items_total > 0:
                diff_pct = abs(items_total - inv.subtotal) / max(abs(inv.subtotal), 0.01)
                if diff_pct > 0.05:   # >5% discrepancy
                    score -= 0.3
                    logger.debug(f"Line items sum mismatch: {items_total:.2f} vs subtotal {inv.subtotal:.2f}")

        # Subtotal + tax ≈ total
        if inv.subtotal is not None and inv.total_amount is not None:
            tax = inv.tax or 0.0
            expected = inv.subtotal + tax
            diff_pct = abs(expected - inv.total_amount) / max(abs(inv.total_amount), 0.01)
            if diff_pct > 0.05:
                score -= 0.3
                logger.debug(f"Total mismatch: {expected:.2f} vs {inv.total_amount:.2f}")

        return round(max(0.0, score), 3)

    def _catalog_match_score(self, result: ProcessingResult) -> float:
        """Ratio of line items that matched a catalog product."""
        items = result.invoice_data.line_items
        if not items:
            return 0.5   # neutral — no items to judge

        matched = sum(1 for item in items if item.match_confidence >= 0.65)
        return round(matched / len(items), 3)


scorer = ConfidenceScorer()
