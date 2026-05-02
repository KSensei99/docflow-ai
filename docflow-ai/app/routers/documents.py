"""
Documents Router
================
POST /documents/upload  — upload + process a document
GET  /documents/{job_id} — get result by ID
GET  /documents/         — list all results
GET  /documents/{job_id}/download/csv — download CSV export
"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings
from app.models.invoice import ProcessingResult, ReviewStatus
from app.services.extractor import extractor
from app.services.exporter import exporter

router = APIRouter(prefix="/documents", tags=["Documents"])

# In-memory store (swap for Redis/Postgres in production)
_results: dict[str, ProcessingResult] = {}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".docx", ".doc"}


@router.post("/upload", response_model=ProcessingResult)
async def upload_and_process(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload a document (PDF, image, Word) and run the full AI pipeline.
    Returns structured invoice data with confidence scores.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Validate size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max: {settings.max_file_size_mb} MB"
        )

    # Save to disk
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = settings.upload_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"Uploaded: {file.filename} ({size_mb:.2f} MB) → {file_path}")

    # Run pipeline
    result = await extractor.process(file_path)

    # Export (CSV + optional webhook)
    export_info = await exporter.export(result)
    logger.info(f"Exported: {export_info}")

    # Store result
    _results[result.job_id] = result
    return result


@router.get("/", response_model=list[ProcessingResult])
async def list_results(
    status: Optional[str] = None,
    limit: int = 50,
):
    """List all processed documents, optionally filtered by review_status."""
    results = list(_results.values())

    if status:
        results = [r for r in results if r.review_status.value == status]

    results.sort(key=lambda r: r.created_at, reverse=True)
    return results[:limit]


@router.get("/review-queue", response_model=list[ProcessingResult])
async def get_review_queue():
    """Get all documents flagged for human review (low confidence)."""
    return [
        r for r in _results.values()
        if r.review_status == ReviewStatus.needs_review
    ]


@router.get("/{job_id}", response_model=ProcessingResult)
async def get_result(job_id: str):
    result = _results.get(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return result


@router.get("/{job_id}/download/csv")
async def download_csv(job_id: str):
    """Download the CSV export for a processed document."""
    result = _results.get(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    # Re-export if needed
    csv_path = exporter.to_csv(result)
    return FileResponse(
        path=csv_path,
        filename=f"invoice_{job_id[:8]}.csv",
        media_type="text/csv",
    )
