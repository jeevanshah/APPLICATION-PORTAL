"""
Admin panel schemas for system configuration management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ==================== RTO PROFILE SCHEMAS ====================

class RTOProfileCreate(BaseModel):
    """Create/update RTO profile."""
    name: str = Field(..., min_length=1, max_length=255)
    cricos_code: str = Field(..., min_length=1, max_length=10)
    contact_email: EmailStr
    contact_phone: str = Field(..., min_length=1, max_length=20)
    # Address is stored as JSONB with: {street, city, state, postcode, country}
    address: Optional[dict] = Field(None, description="Address details as JSON object")
    abn: Optional[str] = Field(None, max_length=20)


class RTOProfileResponse(BaseModel):
    """RTO profile response."""
    id: UUID
    name: str
    cricos_code: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[dict]
    abn: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== DOCUMENT TYPE SCHEMAS ====================

class DocumentTypeCreate(BaseModel):
    """Create/update document type."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    stage: str = Field(..., description="Application stage (e.g., 'DRAFT', 'SUBMITTED')")
    is_mandatory: bool = Field(default=False)
    ocr_model_ref: Optional[str] = Field(None, description="OCR model reference (e.g., 'passport', 'transcript')")
    display_order: int = Field(default=0)


class DocumentTypeResponse(BaseModel):
    """Document type response."""
    id: UUID
    code: str
    name: str
    stage: str
    is_mandatory: bool
    ocr_model_ref: Optional[str]
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== STAFF SCHEMAS ====================

class StaffCreateRequest(BaseModel):
    """Create staff member."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Min 8 characters")
    department: str = Field(default="General", max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    permissions: Optional[dict] = Field(None, description="Permissions as JSON object")


class StaffResponse(BaseModel):
    """Staff member response."""
    id: UUID
    email: str
    role: str
    status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== COURSE OFFERING SCHEMAS ====================

class CourseOfferingCreate(BaseModel):
    """Create/update course offering."""
    course_code: str = Field(..., min_length=1, max_length=50)
    course_name: str = Field(..., min_length=1, max_length=255)
    intake: str = Field(..., description="e.g., 'Feb 2025'")
    campus: str = Field(..., min_length=1, max_length=100)
    tuition_fee: float = Field(..., gt=0)
    application_deadline: Optional[str] = None


class CourseOfferingResponse(BaseModel):
    """Course offering response."""
    id: UUID
    course_code: str
    course_name: str
    intake: str
    campus: str
    tuition_fee: float
    application_deadline: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== SYSTEM STATUS ====================

class SystemStatus(BaseModel):
    """System configuration status."""
    rto_profiles: int
    document_types: int
    staff_members: int
    courses: int
    configured: bool
