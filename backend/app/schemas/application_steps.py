"""
Schemas for the 12-step application form.
Each step has its own request/response schema.
"""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# STEP 1: PERSONAL DETAILS
# ============================================================================

class PersonalDetailsRequest(BaseModel):
    """Step 1: Personal details update."""
    given_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    family_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(..., description="Male, Female, Other, Prefer not to say")
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)
    
    # Address
    street_address: str
    suburb: str
    state: str
    postcode: str
    country: str = "Australia"
    
    # Identity
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    nationality: str
    country_of_birth: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "given_name": "John",
                "middle_name": "Michael",
                "family_name": "Doe",
                "date_of_birth": "2000-03-15",
                "gender": "Male",
                "email": "john.doe@example.com",
                "phone": "+61 400 123 456",
                "street_address": "123 Main Street",
                "suburb": "Sydney",
                "state": "NSW",
                "postcode": "2000",
                "country": "Australia",
                "passport_number": "AB1234567",
                "passport_expiry": "2030-12-31",
                "nationality": "Indian",
                "country_of_birth": "India"
            }
        }


# ============================================================================
# STEP 2: EMERGENCY CONTACT
# ============================================================================

class EmergencyContactItem(BaseModel):
    """Single emergency contact."""
    name: str = Field(..., min_length=1, max_length=100)
    relationship: str
    phone: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    is_primary: bool = False


class EmergencyContactRequest(BaseModel):
    """Step 2: Emergency contacts (must have at least one)."""
    contacts: List[EmergencyContactItem] = Field(..., min_items=1, max_items=5)
    
    @field_validator('contacts')
    @classmethod
    def validate_primary_contact(cls, contacts):
        """Ensure at least one primary contact."""
        if not any(c.is_primary for c in contacts):
            contacts[0].is_primary = True
        return contacts


# ============================================================================
# STEP 3: HEALTH COVER (OSHC)
# ============================================================================

class HealthCoverRequest(BaseModel):
    """Step 3: Overseas Student Health Cover."""
    provider: str = Field(..., description="OSHC provider name (e.g., Bupa, Medibank)")
    policy_number: str
    start_date: date
    end_date: date
    coverage_type: str = Field(..., description="Single, Family, Couple")
    cost: Optional[float] = Field(None, ge=0)
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, end_date, info):
        """Ensure end date is after start date."""
        if 'start_date' in info.data and end_date <= info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return end_date


# ============================================================================
# STEP 4: LANGUAGE & CULTURAL
# ============================================================================

class LanguageCulturalRequest(BaseModel):
    """Step 4: Language and cultural background."""
    first_language: str
    english_proficiency: str = Field(..., description="Native, Advanced, Intermediate, Basic")
    other_languages: Optional[List[str]] = None
    
    # Cultural background
    indigenous_status: Optional[str] = Field(None, description="Aboriginal, Torres Strait Islander, Both, Neither")
    country_of_birth: str
    citizenship_status: str = Field(..., description="Citizen, Permanent Resident, Temporary Visa")
    visa_type: Optional[str] = None
    visa_expiry: Optional[date] = None
    
    # English test (if applicable)
    english_test_type: Optional[str] = Field(None, description="IELTS, TOEFL, PTE, None")
    english_test_score: Optional[str] = None
    english_test_date: Optional[date] = None


# ============================================================================
# STEP 5: DISABILITY SUPPORT
# ============================================================================

class DisabilitySupportRequest(BaseModel):
    """Step 5: Disability and support needs."""
    has_disability: bool
    disability_type: Optional[str] = None
    disability_details: Optional[str] = None
    support_required: Optional[str] = None
    has_documentation: bool = False
    documentation_status: Optional[str] = Field(None, description="Pending upload, Uploaded, Verified")
    adjustments_needed: Optional[List[str]] = None


# ============================================================================
# STEP 6: SCHOOLING HISTORY
# ============================================================================

class SchoolingHistoryItem(BaseModel):
    """Single schooling/education entry."""
    institution: str
    country: str
    qualification_level: str = Field(..., description="High School, Diploma, Bachelor, Master, etc.")
    start_year: int = Field(..., ge=1950, le=2030)
    end_year: Optional[int] = Field(None, ge=1950, le=2030)
    currently_attending: bool = False
    result: Optional[str] = None
    field_of_study: Optional[str] = None


class SchoolingHistoryRequest(BaseModel):
    """Step 6: Educational background (at least one entry required)."""
    entries: List[SchoolingHistoryItem] = Field(..., min_items=1, max_items=10)


# ============================================================================
# STEP 7: PREVIOUS QUALIFICATIONS
# ============================================================================

class QualificationItem(BaseModel):
    """Single qualification/certification."""
    qualification_name: str
    institution: str
    completion_date: date
    certificate_number: Optional[str] = None
    field_of_study: Optional[str] = None
    grade: Optional[str] = None


class PreviousQualificationsRequest(BaseModel):
    """Step 7: Professional qualifications and certifications."""
    qualifications: List[QualificationItem] = Field(default_factory=list, max_items=10)


# ============================================================================
# STEP 8: EMPLOYMENT HISTORY
# ============================================================================

class EmploymentHistoryItem(BaseModel):
    """Single employment entry."""
    employer: str
    role: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    responsibilities: Optional[str] = None
    industry: Optional[str] = None


class EmploymentHistoryRequest(BaseModel):
    """Step 8: Work experience."""
    entries: List[EmploymentHistoryItem] = Field(default_factory=list, max_items=15)


# ============================================================================
# STEP 9: USI (Unique Student Identifier)
# ============================================================================

class USIRequest(BaseModel):
    """Step 9: USI details."""
    usi: str = Field(..., min_length=10, max_length=10, pattern=r'^[A-Z0-9]{10}$')
    consent_to_verify: bool = Field(..., description="Student consents to USI verification")
    
    class Config:
        json_schema_extra = {
            "example": {
                "usi": "ABC1234567",
                "consent_to_verify": True
            }
        }


# ============================================================================
# STEP 10: ADDITIONAL SERVICES
# ============================================================================

class AdditionalServiceItem(BaseModel):
    """Single optional service."""
    service_id: str
    name: str
    description: Optional[str] = None
    fee: float = Field(..., ge=0)
    selected: bool = False


class AdditionalServicesRequest(BaseModel):
    """Step 10: Optional services selection."""
    services: List[AdditionalServiceItem] = Field(default_factory=list)
    total_additional_fees: float = Field(default=0.0, ge=0)


# ============================================================================
# STEP 11: SURVEY
# ============================================================================

class SurveyQuestionResponse(BaseModel):
    """Single survey question response."""
    question_id: str
    question_text: str
    answer: str
    answer_type: str = Field(..., description="text, single_choice, multiple_choice, rating")


class SurveyRequest(BaseModel):
    """Step 11: Pre-enrollment survey."""
    responses: List[SurveyQuestionResponse] = Field(default_factory=list)
    how_did_you_hear: Optional[str] = None
    referral_source: Optional[str] = None


# ============================================================================
# STEP 12: DOCUMENT UPLOAD TRACKING
# ============================================================================

class DocumentUploadInfo(BaseModel):
    """Document upload status for step 12."""
    document_type_code: str
    document_type_name: str
    is_mandatory: bool
    uploaded: bool = False
    uploaded_at: Optional[datetime] = None
    status: Optional[str] = None
    ocr_status: Optional[str] = None


class DocumentStepResponse(BaseModel):
    """Step 12: Document upload status."""
    required_documents: List[DocumentUploadInfo]
    total_required: int
    total_uploaded: int
    all_mandatory_uploaded: bool


# ============================================================================
# COMMON RESPONSE
# ============================================================================

class StepUpdateResponse(BaseModel):
    """Common response for step updates."""
    success: bool = True
    message: str
    step_number: int
    step_name: str
    completion_percentage: int = Field(..., ge=0, le=100)
    next_step: Optional[str] = None
    can_submit: bool = False
