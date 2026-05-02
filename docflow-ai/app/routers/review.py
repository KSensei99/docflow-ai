"""
Review Router — Human-in-the-Loop
==================================
PATCH /review/{job_id}/approve  — approve extraction
PATCH /review/{job_id}/reject   — reject and flag for reprocessing
PATCH /review/{job_id}/correct  — submit corrected invoice data
GET   /review/stats              — dashboard stats
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.invoice import InvoiceData, ProcessingResult, ReviewStatus
from app.routers.documents import _results  # shared store

router = APIRouter(prefix="/review", tags=["Human Review"])


class ReviewAction(BaseModel):
    reviewed_by: str = "reviewer"
    notes: Optional[str] = None


class CorrectionPayload(BaseModel):
    reviewed_by: str = "reviewer"
    corrected_data: InvoiceData
    notes: Optional[str] = None


@router.patch("/{job_id}/approve", response_model=ProcessingResult)
async def approve(job_id: str, action: ReviewAction):
    """Mark a flagged document as approved after human review."""
    result = _get_or_404(job_id)
    result.review_status = ReviewStatus.approved
    result.reviewed_by = action.reviewed_by
    result.reviewed_at = datetime.utcnow()
    if action.notes:
        result.review_notes = action.notes
    return result


@router.patch("/{job_id}/reject", response_model=ProcessingResult)
async def reject(job_id: str, action: ReviewAction):
    """Reject a document extraction (e.g., unreadable scan)."""
    result = _get_or_404(job_id)
    result.review_status = ReviewStatus.rejected
    result.reviewed_by = action.reviewed_by
    result.reviewed_at = datetime.utcnow()
    result.review_notes = action.notes or "Rejected by reviewer"
    return result


@router.patch("/{job_id}/correct", response_model=ProcessingResult)
async def correct(job_id: str, payload: CorrectionPayload):
    """
    Submit human-corrected invoice data.
    Replaces LLM extraction with verified values — auto-approves.
    """
    result = _get_or_404(job_id)
    result.invoice_data = payload.corrected_data
    result.review_status = ReviewStatus.approved
    result.reviewed_by = payload.reviewed_by
    result.reviewed_at = datetime.utcnow()
    result.review_notes = payload.notes or "Manually corrected and approved"
    result.overall_confidence = 1.0   # human-verified = full confidence
    return result


@router.get("/stats")
async def review_stats():
    """Quick dashboard stats for the review queue."""
    all_results = list(_results.values())
    total = len(all_results)

    status_counts = {}
    for r in all_results:
        k = r.review_status.value
        status_counts[k] = status_counts.get(k, 0) + 1

    avg_confidence = (
        sum(r.overall_confidence for r in all_results) / total
        if total > 0 else 0
    )

    return {
        "total_documents": total,
        "status_breakdown": status_counts,
        "avg_confidence": round(avg_confidence, 3),
        "pending_review": status_counts.get("needs_review", 0),
        "auto_approved": status_counts.get("approved", 0),
    }


def _get_or_404(job_id: str) -> ProcessingResult:
    result = _results.get(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return result
