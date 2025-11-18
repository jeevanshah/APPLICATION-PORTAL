"""
Document schemas for upload, OCR, and retrieval.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import DocumentStatus, OCRStatus

# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class DocumentUploadRequest(BaseModel):
    """Metadata for document upload (multipart/form-data)."""
    application_id: UUID
    document_type_id: UUID
    # Note: File itself is uploaded separately in multipart form


class DocumentVerifyRequest(BaseModel):
    """Staff verification of document."""
    status: DocumentStatus
    notes: Optional[str] = None


class OCRProcessRequest(BaseModel):
    """Trigger OCR processing manually."""
    force_reprocess: bool = False


class DocumentMetadataUpdate(BaseModel):
    """Update document metadata."""
    notes: Optional[str] = None
    gs_document_requests: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DocumentVersionResponse(BaseModel):
    """Document version details."""
    id: UUID
    document_id: UUID
    blob_url: str
    checksum: str
    file_size_bytes: int
    version_number: int
    ocr_json: Optional[Dict[str, Any]] = None
    preview_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentTypeResponse(BaseModel):
    """Document type details."""
    id: UUID
    code: str
    name: str
    stage: str
    is_mandatory: bool
    ocr_model_ref: Optional[str] = None
    display_order: int

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Full document details."""
    id: UUID
    application_id: UUID
    document_type_id: UUID
    status: DocumentStatus
    uploaded_by: UUID
    uploaded_at: datetime
    ocr_status: OCRStatus
    ocr_completed_at: Optional[datetime] = None
    gs_document_requests: Optional[List[Dict[str, Any]]] = None

    # Relationships
    document_type: Optional[DocumentTypeResponse] = None
    versions: Optional[List[DocumentVersionResponse]] = []
    latest_version: Optional[DocumentVersionResponse] = None

    # Uploader info (computed)
    uploader_email: Optional[str] = None
    uploader_name: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Lightweight document list item."""
    id: UUID
    application_id: UUID
    document_type_id: UUID
    document_type_name: str
    document_type_code: str
    status: DocumentStatus
    ocr_status: OCRStatus
    uploaded_at: datetime
    uploaded_by: UUID
    uploader_email: Optional[str] = None
    file_size_bytes: Optional[int] = None
    latest_version_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """Response after successful upload."""
    document: DocumentResponse
    message: str = "Document uploaded successfully"
    ocr_queued: bool = False


class OCRResultResponse(BaseModel):
    """OCR extraction results."""
    document_id: UUID
    ocr_status: OCRStatus
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    # Field mappings for auto-fill
    suggested_mappings: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    processing_time_ms: Optional[int] = None


class DocumentStatsResponse(BaseModel):
    """Document statistics for an application."""
    total_documents: int
    by_status: Dict[str, int]
    by_ocr_status: Dict[str, int]
    missing_mandatory: List[str]  # List of missing mandatory document types
    completion_percentage: int


# ============================================================================
# AUTO-FILL SCHEMAS
# ============================================================================

class OCRAutoFillSuggestion(BaseModel):
    """Suggested field value from OCR extraction."""
    field_name: str
    field_path: str  # e.g., "personal_details.given_name"
    extracted_value: Any
    confidence: float  # 0.0 to 1.0
    source_document_id: UUID
    source_text: Optional[str] = None  # Original text snippet


class OCRAutoFillResponse(BaseModel):
    """Auto-fill suggestions for application form."""
    application_id: UUID
    suggestions: List[OCRAutoFillSuggestion]
    total_suggestions: int
    high_confidence_count: int  # confidence > 0.8
    medium_confidence_count: int  # 0.5 < confidence <= 0.8
    low_confidence_count: int  # confidence <= 0.5


# ============================================================================
# DOCUMENT TYPE SCHEMAS
# ============================================================================

class DocumentTypeCreateRequest(BaseModel):
    """Create new document type (admin only)."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    stage: str  # ApplicationStage enum value
    is_mandatory: bool = True
    ocr_model_ref: Optional[str] = None
    display_order: int = 0


class DocumentTypeUpdateRequest(BaseModel):
    """Update document type."""
    name: Optional[str] = None
    is_mandatory: Optional[bool] = None
    ocr_model_ref: Optional[str] = None
    display_order: Optional[int] = None


class DocumentTypeListResponse(BaseModel):
    """List of document types."""
    document_types: List[DocumentTypeResponse]
    total: int
