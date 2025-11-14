"""
Pydantic schemas for JSONB fields in Application Portal.
These nested models provide type safety and validation for flexible JSONB data.
"""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID


# ============================================================================
# JSONB NESTED SCHEMAS (for APPLICATION table)
# ============================================================================

class EmergencyContactSchema(BaseModel):
    """Emergency contact information (stored in APPLICATION.emergency_contacts array)."""
    name: str = Field(..., min_length=1, max_length=255)
    relationship: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    is_primary: bool = False


class HealthCoverPolicySchema(BaseModel):
    """Health insurance policy (stored in APPLICATION.health_cover_policy)."""
    provider: str = Field(..., min_length=1, max_length=255)
    policy_number: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    coverage_type: str = Field(..., min_length=1, max_length=100)  # e.g., "Basic", "Comprehensive"


class DisabilitySupportSchema(BaseModel):
    """Disability support requirements (stored in APPLICATION.disability_support)."""
    has_disability: bool
    disability_details: Optional[str] = None
    support_required: Optional[str] = None
    documentation_status: Optional[str] = Field(None, max_length=50)  # e.g., "verified", "pending"


class LanguageCulturalDataSchema(BaseModel):
    """Language and cultural background (stored in APPLICATION.language_cultural_data)."""
    first_language: str = Field(..., min_length=1, max_length=100)
    other_languages: List[str] = Field(default_factory=list)
    indigenous_status: Optional[str] = Field(None, max_length=100)
    country_of_birth: str = Field(..., min_length=1, max_length=100)
    citizenship_status: str = Field(..., min_length=1, max_length=100)  # e.g., "International Student", "PR", "Citizen"


class SurveyResponseSchema(BaseModel):
    """Survey question and answer (stored in APPLICATION.survey_responses array)."""
    question_id: UUID
    question_text: str = Field(..., min_length=1)
    answer: str


class AdditionalServiceSchema(BaseModel):
    """Optional service selection (stored in APPLICATION.additional_services array)."""
    service_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    fee: Decimal = Field(..., ge=0)
    selected_at: datetime


class GsScorecardSchema(BaseModel):
    """Genuine Student assessment scorecard."""
    genuine_intent: int = Field(..., ge=0, le=10)
    english_proficiency: int = Field(..., ge=0, le=10)
    financial_capacity: int = Field(..., ge=0, le=10)
    academic_background: Optional[int] = Field(None, ge=0, le=10)
    interview_performance: Optional[int] = Field(None, ge=0, le=10)


class GsAssessmentSchema(BaseModel):
    """GS assessment results (stored in APPLICATION.gs_assessment)."""
    interview_date: datetime
    staff_id: UUID
    scorecard: GsScorecardSchema
    decision: str = Field(..., pattern="^(approved|rejected|further_review)$")
    notes: Optional[str] = None


class SignaturePartySchema(BaseModel):
    """Signature party information for e-signature envelope."""
    role: str = Field(..., max_length=50)  # e.g., "student", "agent", "guardian"
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    signed_at: Optional[datetime] = None


class SignatureDataSchema(BaseModel):
    """E-signature envelope data (stored in APPLICATION.signature_data)."""
    envelope_id: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., max_length=50)  # e.g., "DocuSeal", "DocuSign"
    status: str = Field(..., pattern="^(draft|sent|completed|declined|voided)$")
    cost_cents: int = Field(..., ge=0)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parties: List[SignaturePartySchema]


class EnrollmentDataSchema(BaseModel):
    """Course enrollment status (stored in APPLICATION.enrollment_data)."""
    status: str = Field(..., pattern="^(enrolled|deferred|withdrawn)$")
    offer_signed_at: Optional[datetime] = None
    fee_received_at: Optional[datetime] = None
    coe_uploaded_at: Optional[datetime] = None
    coe_number: Optional[str] = Field(None, max_length=100)


class FormMetadataSchema(BaseModel):
    """Form submission metadata (stored in APPLICATION.form_metadata)."""
    version: str = Field(..., max_length=20)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    submission_duration_seconds: Optional[int] = Field(None, ge=0)


# ============================================================================
# JSONB NESTED SCHEMAS (for USER_ACCOUNT table)
# ============================================================================

class EmailNotificationPrefsSchema(BaseModel):
    """Email notification preferences."""
    enabled: bool = True
    frequency: str = Field("instant", pattern="^(instant|daily|weekly|never)$")
    mute_until: Optional[datetime] = None


class SmsNotificationPrefsSchema(BaseModel):
    """SMS notification preferences."""
    enabled: bool = False
    phone_number: Optional[str] = Field(None, max_length=50)


class InAppNotificationPrefsSchema(BaseModel):
    """In-app notification preferences."""
    enabled: bool = True
    frequency: str = Field("instant", pattern="^(instant|never)$")


class NotificationPreferencesSchema(BaseModel):
    """User notification preferences (stored in USER_ACCOUNT.notification_preferences)."""
    email: EmailNotificationPrefsSchema = Field(default_factory=EmailNotificationPrefsSchema)
    sms: SmsNotificationPrefsSchema = Field(default_factory=SmsNotificationPrefsSchema)
    in_app: InAppNotificationPrefsSchema = Field(default_factory=InAppNotificationPrefsSchema)


class WorkflowSlaConfigSchema(BaseModel):
    """SLA configuration for workflow stage."""
    target_hours: int = Field(..., ge=1)
    escalation_hours: int = Field(..., ge=1)


class AdminConfigSchema(BaseModel):
    """Staff admin configuration (stored in USER_ACCOUNT.admin_config)."""
    workflow_sla: Optional[dict[str, WorkflowSlaConfigSchema]] = None  # Key: stage name
    default_templates: Optional[dict[str, str]] = None  # Key: template type, Value: blob URL
    auto_assign_enabled: bool = False
    signature_authority: bool = False


# ============================================================================
# JSONB NESTED SCHEMAS (for DOCUMENT table)
# ============================================================================

class GsDocumentRequestSchema(BaseModel):
    """GS document request (stored in DOCUMENT.gs_document_requests array)."""
    requested_by: UUID
    requested_at: datetime
    due_at: datetime
    status: str = Field(..., pattern="^(pending|fulfilled|overdue)$")
    notes: Optional[str] = None


# ============================================================================
# JSONB NESTED SCHEMAS (for TIMELINE_ENTRY table)
# ============================================================================

class WorkflowEventPayloadSchema(BaseModel):
    """Workflow event payload (stored in TIMELINE_ENTRY.event_payload)."""
    event_type: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[dict] = Field(default_factory=dict)
    triggered_by: str = Field(..., pattern="^(user|system|scheduled)$")


# ============================================================================
# JSONB NESTED SCHEMAS (for RTO_PROFILE table)
# ============================================================================

class AddressSchema(BaseModel):
    """Physical address (stored in RTO_PROFILE.address)."""
    street: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    postcode: str = Field(..., min_length=1, max_length=10)
    country: str = Field(..., min_length=1)


class BrandSettingsSchema(BaseModel):
    """Branding configuration (stored in RTO_PROFILE.brand_settings)."""
    primary_color: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$")  # Hex color
    secondary_color: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$")
    font_family: Optional[str] = Field(None, max_length=100)
    theme: str = Field("light", pattern="^(light|dark)$")


class BusinessSettingsSchema(BaseModel):
    """Business configuration (stored in RTO_PROFILE.business_settings)."""
    default_commission_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    sla_overrides: Optional[dict[str, WorkflowSlaConfigSchema]] = None
    features_enabled: Optional[dict[str, bool]] = Field(default_factory=dict)
    time_zone: str = Field("Australia/Sydney", max_length=50)
    business_hours: Optional[dict] = None  # {monday: {open: "09:00", close: "17:00"}, ...}
