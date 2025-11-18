"""
Pydantic schemas for student profile management and application tracking.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ============================================================================
# STUDENT PROFILE SCHEMAS
# ============================================================================


class StudentProfileCreateRequest(BaseModel):
    """Schema for agents creating a student profile with login credentials."""
    # User account credentials
    email: EmailStr = Field(...,
                            description="Student's email (will be login username)")
    password: str = Field(..., min_length=8,
                          description="Initial password for student login")

    # Student profile information
    given_name: str = Field(..., min_length=1, max_length=100)
    family_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    passport_number: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    visa_type: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123!",
                "given_name": "John",
                "family_name": "Doe",
                "date_of_birth": "1995-03-15",
                "passport_number": "AB1234567",
                "nationality": "Indian",
                "visa_type": "Student Visa (Subclass 500)",
                "phone": "+61 400 123 456",
                "address": "123 Main St, Sydney NSW 2000"
            }
        }


class StudentProfileUpdateRequest(BaseModel):
    """Schema for updating student profile (by student or agent)."""
    given_name: Optional[str] = Field(None, min_length=1, max_length=100)
    family_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    passport_number: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    visa_type: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class StudentProfileResponse(BaseModel):
    """Student profile response with user account details."""
    id: UUID
    user_account_id: UUID
    email: str
    given_name: str
    family_name: str
    date_of_birth: date
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    visa_type: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str  # UserStatus enum value
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# STUDENT DASHBOARD SCHEMAS
# ============================================================================

class ApplicationSummaryForStudent(BaseModel):
    """Lightweight application summary for student dashboard."""
    id: UUID
    course_code: str
    course_name: str
    intake: str
    current_stage: str  # ApplicationStage enum value
    completion_percentage: int = Field(..., ge=0, le=100)
    submitted_at: Optional[datetime] = None
    last_updated: datetime
    # Name of staff member handling application
    assigned_staff_name: Optional[str] = None

    class Config:
        from_attributes = True


class RecentTimelineActivity(BaseModel):
    """Recent timeline entry for dashboard feed."""
    id: UUID
    application_id: UUID
    entry_type: str  # TimelineEntryType enum value
    message: str
    created_at: datetime
    actor_name: Optional[str] = None  # Name of person who performed the action

    class Config:
        from_attributes = True


class StudentDashboardResponse(BaseModel):
    """Complete dashboard view for student portal."""
    student: StudentProfileResponse
    applications: List[ApplicationSummaryForStudent] = []
    recent_activity: List[RecentTimelineActivity] = []
    statistics: dict = Field(
        default_factory=lambda: {
            "total_applications": 0,
            "draft_count": 0,
            "submitted_count": 0,
            "in_review_count": 0,
            "offers_count": 0,
            "enrolled_count": 0
        }
    )


# ============================================================================
# APPLICATION TRACKING SCHEMAS
# ============================================================================

class StageProgressItem(BaseModel):
    """Individual stage in the application workflow."""
    stage: str  # ApplicationStage enum value
    status: str  # "completed", "current", "pending"
    completed_at: Optional[datetime] = None
    duration_days: Optional[int] = None  # Days spent in this stage


class RequiredDocumentItem(BaseModel):
    """Required document with upload status."""
    document_type_code: str
    document_type_name: str
    is_mandatory: bool
    status: Optional[str] = None  # DocumentStatus enum value if uploaded
    uploaded_at: Optional[datetime] = None
    ocr_status: Optional[str] = None  # OCRStatus enum value


class ApplicationTrackingDetailResponse(BaseModel):
    """Detailed tracking view for a specific application."""
    # Application basic info
    id: UUID
    course_code: str
    course_name: str
    intake: str
    campus: str
    tuition_fee: float

    # Current status
    current_stage: str  # ApplicationStage enum value
    completion_percentage: int = Field(..., ge=0, le=100)
    submitted_at: Optional[datetime] = None
    decision_at: Optional[datetime] = None

    # Progress tracking
    stage_progress: List[StageProgressItem] = []
    required_documents: List[RequiredDocumentItem] = []

    # Timeline history
    timeline: List[RecentTimelineActivity] = []

    # Agent information (if applicable)
    agent_name: Optional[str] = None
    agent_agency: Optional[str] = None
    agent_phone: Optional[str] = None

    # Assigned staff (if applicable)
    assigned_staff_name: Optional[str] = None
    assigned_staff_email: Optional[str] = None

    # Next steps
    next_steps: List[str] = Field(
        default_factory=list,
        description="Action items for the student"
    )

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """List of students with basic info (for agents/staff)."""
    students: List[StudentProfileResponse]
    total: int
    page: int
    page_size: int
