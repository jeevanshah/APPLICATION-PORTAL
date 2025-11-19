"""
Application schemas with JSONB field validation and draft/resume support.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import ApplicationStage

# ============================================================================
# JSONB SUB-SCHEMAS (for nested data validation)
# ============================================================================


class EmergencyContact(BaseModel):
    """Emergency contact person."""
    name: str
    relationship: str
    phone: str
    email: Optional[str] = None
    is_primary: bool = False


class HealthCoverPolicy(BaseModel):
    """Overseas student health cover details."""
    provider: str
    policy_number: str
    start_date: date
    end_date: date
    coverage_type: str  # e.g., "Single", "Family"


class DisabilitySupport(BaseModel):
    """Disability and support requirements."""
    has_disability: bool
    disability_details: Optional[str] = None
    support_required: Optional[str] = None
    documentation_status: Optional[str] = None


class LanguageCulturalData(BaseModel):
    """Language and cultural background."""
    first_language: str
    other_languages: Optional[List[str]] = None
    indigenous_status: Optional[str] = None
    country_of_birth: str
    citizenship_status: str


class SurveyResponse(BaseModel):
    """Survey question response."""
    question_id: str
    question_text: str
    answer: str


class AdditionalService(BaseModel):
    """Optional service selection."""
    service_id: str
    name: str
    fee: float
    selected_at: datetime


class EnrollmentData(BaseModel):
    """Enrollment and offer acceptance data."""
    status: Optional[str] = None  # "offer_sent", "offer_accepted", "enrolled"
    offer_signed_at: Optional[datetime] = None
    fee_received_at: Optional[datetime] = None
    coe_uploaded_at: Optional[datetime] = None


class GSAssessment(BaseModel):
    """Genuine Student assessment record."""
    interview_date: Optional[datetime] = None
    staff_id: Optional[UUID] = None
    scorecard: Optional[dict] = None
    decision: Optional[str] = None  # "pass", "fail", "pending"
    notes: Optional[str] = None


class SignatureParty(BaseModel):
    """Individual signature party in e-signature process."""
    role: str  # "student", "parent", "guardian"
    name: str
    email: str
    signed_at: Optional[datetime] = None


class SignatureData(BaseModel):
    """E-signature envelope tracking."""
    envelope_id: str
    provider: str  # "docuseal", "docusign", etc.
    status: str  # "pending", "completed", "expired"
    cost_cents: Optional[int] = None
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parties: List[SignatureParty]


class FormMetadata(BaseModel):
    """Application form metadata for draft/resume."""
    version: str = "1.0"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    submission_duration_seconds: Optional[int] = None
    last_edited_section: Optional[str] = None
    completed_sections: List[str] = Field(default_factory=list)
    last_saved_at: Optional[datetime] = None
    auto_save_count: int = 0


# ============================================================================
# APPLICATION REQUEST/RESPONSE SCHEMAS
# ============================================================================

class ApplicationCreateRequest(BaseModel):
    """Create new application (draft)."""
    course_offering_id: UUID
    agent_profile_id: Optional[UUID] = None

    # Optional: pre-fill with student profile data if available
    student_profile_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "course_offering_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "agent_profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                # student_profile_id is optional - typically null for new applications
            }
        }


class ApplicationUpdateRequest(BaseModel):
    """Update application (auto-save or manual save)."""
    # All fields optional for partial updates
    usi: Optional[str] = None

    # JSONB fields (partial updates supported)
    enrollment_data: Optional[EnrollmentData] = None
    emergency_contacts: Optional[List[EmergencyContact]] = None
    health_cover_policy: Optional[HealthCoverPolicy] = None
    disability_support: Optional[DisabilitySupport] = None
    language_cultural_data: Optional[LanguageCulturalData] = None
    survey_responses: Optional[List[SurveyResponse]] = None
    additional_services: Optional[List[AdditionalService]] = None
    gs_assessment: Optional[GSAssessment] = None
    signature_data: Optional[SignatureData] = None
    form_metadata: Optional[FormMetadata] = None


class ApplicationSubmitRequest(BaseModel):
    """Submit application for review (validates all required fields)."""
    # Require critical fields before submission
    confirm_accuracy: bool = Field(...,
                                   description="User confirms all information is accurate")


class ApplicationAssignRequest(BaseModel):
    """Assign application to staff member."""
    staff_id: UUID
    notes: Optional[str] = None


class ApplicationStageChangeRequest(BaseModel):
    """Transition application to new stage."""
    to_stage: ApplicationStage
    notes: Optional[str] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ApplicationSummary(BaseModel):
    """Lightweight application list item."""
    id: UUID
    student_profile_id: Optional[UUID] = None  # Nullable - created when application enrolled
    course_offering_id: UUID
    current_stage: ApplicationStage
    submitted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    student_name: Optional[str] = None  # From joined student_profile
    course_name: Optional[str] = None  # From joined course_offering
    agent_name: Optional[str] = None  # From joined agent_profile
    assigned_staff_name: Optional[str] = None

    # Progress indicator
    completion_percentage: Optional[int] = None

    class Config:
        from_attributes = True


class ApplicationDetail(BaseModel):
    """Full application details."""
    id: UUID
    student_profile_id: Optional[UUID] = None  # Nullable - created when application enrolled
    agent_profile_id: Optional[UUID]
    course_offering_id: UUID
    assigned_staff_id: Optional[UUID]

    # Workflow
    current_stage: ApplicationStage
    submitted_at: Optional[datetime]
    decision_at: Optional[datetime]

    # USI
    usi: Optional[str]
    usi_verified: bool
    usi_verified_at: Optional[datetime]

    # JSONB fields - Form Steps
    personal_details: Optional[Dict[str, Any]]  # Step 1
    emergency_contacts: Optional[List[EmergencyContact]]  # Step 2
    health_cover_policy: Optional[HealthCoverPolicy]  # Step 3
    language_cultural_data: Optional[LanguageCulturalData]  # Step 4
    disability_support: Optional[DisabilitySupport]  # Step 5
    schooling_history: Optional[List[Dict[str, Any]]]  # Step 6
    qualifications: Optional[List[Dict[str, Any]]]  # Step 7
    employment_history: Optional[List[Dict[str, Any]]]  # Step 8
    additional_services: Optional[List[AdditionalService]]  # Step 10
    survey_responses: Optional[List[SurveyResponse]]  # Step 11
    
    # JSONB fields - Business Data
    enrollment_data: Optional[EnrollmentData]
    gs_assessment: Optional[GSAssessment]
    signature_data: Optional[SignatureData]
    form_metadata: Optional[FormMetadata]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    """Standard application response with message."""
    application: ApplicationDetail
    message: str = "Application updated successfully"
