from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class ReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    needs_review = "needs_review"


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    matched_product_id: Optional[str] = None
    matched_product_name: Optional[str] = None
    match_confidence: float = 0.0


class InvoiceData(BaseModel):
    """Structured invoice extracted by the LLM pipeline."""
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_email: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    currency: str = "USD"
    line_items: list[LineItem] = []
    payment_terms: Optional[str] = None
    notes: Optional[str] = None


class ProcessingResult(BaseModel):
    """Full result returned by the pipeline for one document."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    status: str = "processed"
    review_status: ReviewStatus = ReviewStatus.pending

    # Extracted content
    raw_text: str = ""
    invoice_data: InvoiceData = Field(default_factory=InvoiceData)

    # Confidence
    overall_confidence: float = 0.0
    field_confidences: dict[str, float] = {}

    # Metadata
    ocr_engine: str = ""
    llm_model: str = ""
    processing_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Review queue
    review_notes: str = ""
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
