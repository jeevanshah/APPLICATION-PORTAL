"""
Staff workflow schemas for dashboard, application review, and document verification.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models import ApplicationStage, DocumentStatus, UserRole


# ============================================================================
# STAFF DASHBOARD SCHEMAS
# ============================================================================

class StaffMetrics(BaseModel):
    """Dashboard metrics for staff workload."""
    total_applications: int
    submitted_pending_review: int
    in_staff_review: int
    awaiting_documents: int
    in_gs_assessment: int
    offers_generated: int
    enrolled: int
    rejected: int
    documents_pending_verification: int


class StudentSummary(BaseModel):
    """Student information summary."""
    id: UUID
    given_name: str
    family_name: str
    email: str
    nationality: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class CourseSummary(BaseModel):
    """Course offering summary."""
    id: UUID
    course_code: str
    course_name: str
    intake: str
    campus: str
    
    model_config = ConfigDict(from_attributes=True)


class AgentSummary(BaseModel):
    """Agent information summary."""
    id: UUID
    agency_name: str
    email: str
    
    model_config = ConfigDict(from_attributes=True)


class DocumentSummaryForStaff(BaseModel):
    """Document summary for staff review."""
    id: UUID
    document_type_code: str
    document_type_name: str
    status: DocumentStatus
    ocr_status: str
    uploaded_at: datetime
    version_count: int
    
    model_config = ConfigDict(from_attributes=True)


class ApplicationListItem(BaseModel):
    """Application item for staff pending queue."""
    id: UUID
    student: StudentSummary
    course: CourseSummary
    agent: Optional[AgentSummary] = None
    current_stage: ApplicationStage
    submitted_at: Optional[datetime] = None
    days_pending: Optional[int] = None  # Calculated field
    document_count: int = 0
    documents_verified: int = 0
    documents_pending: int = 0
    assigned_staff_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PendingApplicationsResponse(BaseModel):
    """Response for GET /staff/applications/pending."""
    total: int
    applications: List[ApplicationListItem]
    skip: int
    limit: int


# ============================================================================
# APPLICATION REVIEW SCHEMAS
# ============================================================================

class SchoolingHistoryDetail(BaseModel):
    """Schooling history for review."""
    id: UUID
    institution: str
    country: str
    start_year: int
    end_year: Optional[int] = None
    qualification_level: str
    result: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class QualificationHistoryDetail(BaseModel):
    """Professional qualification for review."""
    id: UUID
    qualification_name: str
    institution: str
    completion_date: date
    certificate_number: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class EmploymentHistoryDetail(BaseModel):
    """Employment history for review."""
    id: UUID
    employer: str
    role: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool
    responsibilities: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class TimelineEntryDetail(BaseModel):
    """Timeline entry for application history."""
    id: UUID
    entry_type: str
    message: str
    actor_email: Optional[str] = None
    actor_role: Optional[UserRole] = None
    created_at: datetime
    event_payload: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailForReview(BaseModel):
    """Complete application details for staff review."""
    id: UUID
    student: StudentSummary
    course: CourseSummary
    agent: Optional[AgentSummary] = None
    current_stage: ApplicationStage
    submitted_at: Optional[datetime] = None
    decision_at: Optional[datetime] = None
    
    # USI
    usi: Optional[str] = None
    usi_verified: bool = False
    
    # JSONB fields
    enrollment_data: Optional[Dict[str, Any]] = None
    emergency_contacts: Optional[List[Dict[str, Any]]] = None
    health_cover_policy: Optional[Dict[str, Any]] = None
    disability_support: Optional[Dict[str, Any]] = None
    language_cultural_data: Optional[Dict[str, Any]] = None
    survey_responses: Optional[List[Dict[str, Any]]] = None
    additional_services: Optional[List[Dict[str, Any]]] = None
    gs_assessment: Optional[Dict[str, Any]] = None
    form_metadata: Optional[Dict[str, Any]] = None
    
    # Normalized history
    schooling_history: List[SchoolingHistoryDetail] = []
    qualification_history: List[QualificationHistoryDetail] = []
    employment_history: List[EmploymentHistoryDetail] = []
    
    # Documents
    documents: List[DocumentSummaryForStaff] = []
    
    # Timeline
    timeline: List[TimelineEntryDetail] = []
    
    # Staff assignment
    assigned_staff_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# STAFF ACTION SCHEMAS (Requests)
# ============================================================================

class AssignApplicationRequest(BaseModel):
    """Request to assign application to staff."""
    staff_id: UUID


class TransitionStageRequest(BaseModel):
    """Request to transition application stage."""
    to_stage: ApplicationStage
    notes: Optional[str] = None


class VerifyDocumentRequest(BaseModel):
    """Request to verify or reject document."""
    status: DocumentStatus = Field(..., description="VERIFIED or REJECTED")
    notes: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v not in [DocumentStatus.VERIFIED, DocumentStatus.REJECTED]:
            raise ValueError("Status must be VERIFIED or REJECTED")
        return v


class AddStaffCommentRequest(BaseModel):
    """Request to add staff comment."""
    comment: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = False


class RequestAdditionalDocumentsRequest(BaseModel):
    """Request additional documents from student/agent."""
    document_type_codes: List[str] = Field(..., min_items=1)
    message: str = Field(..., min_length=10, max_length=1000)
    due_date: Optional[date] = None


class ApproveApplicationRequest(BaseModel):
    """Request to approve application (move to OFFER_GENERATED)."""
    offer_details: Dict[str, Any] = Field(
        ...,
        description="Offer letter details: course_start_date, fees, conditions, etc."
    )
    notes: Optional[str] = None


class RejectApplicationRequest(BaseModel):
    """Request to reject application."""
    rejection_reason: str = Field(..., min_length=10, max_length=1000)
    is_appealable: bool = False


class GSAssessmentRequest(BaseModel):
    """Request to record GS assessment."""
    interview_date: datetime
    decision: str = Field(..., description="pass, fail, or pending")
    scorecard: Dict[str, Any] = Field(
        ...,
        description="Assessment scorecard with criteria scores"
    )
    notes: Optional[str] = None


# ============================================================================
# OFFER LETTER SCHEMAS
# ============================================================================

class OfferLetterRequest(BaseModel):
    """Request to generate offer letter."""
    course_start_date: date
    tuition_fee: float
    material_fee: Optional[float] = 0.0
    conditions: List[str] = []
    template: str = "standard"  # Could support multiple templates


class OfferLetterResponse(BaseModel):
    """Response after generating offer letter."""
    application_id: UUID
    offer_letter_url: str  # URL to generated PDF
    generated_at: datetime
    expires_at: Optional[datetime] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DocumentVerificationResponse(BaseModel):
    """Response after document verification."""
    document_id: UUID
    status: DocumentStatus
    verified_at: datetime
    message: str


class ApplicationActionResponse(BaseModel):
    """Generic response for application actions."""
    application_id: UUID
    current_stage: ApplicationStage
    message: str
    updated_at: datetime


class StaffCommentResponse(BaseModel):
    """Response after adding comment."""
    timeline_entry_id: UUID
    application_id: UUID
    comment: str
    created_at: datetime
