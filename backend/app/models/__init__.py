"""
SQLAlchemy models for Churchill Application Portal v3.1 schema.
16-table lean architecture with JSONB-first approach.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, Numeric, String, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    """User account roles."""
    STUDENT = "student"
    AGENT = "agent"
    STAFF = "staff"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ApplicationStage(str, enum.Enum):
    """Application workflow stages."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    STAFF_REVIEW = "staff_review"
    AWAITING_DOCUMENTS = "awaiting_documents"
    GS_ASSESSMENT = "gs_assessment"
    OFFER_GENERATED = "offer_generated"
    OFFER_ACCEPTED = "offer_accepted"
    ENROLLED = "enrolled"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DocumentStatus(str, enum.Enum):
    """Document verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OCRStatus(str, enum.Enum):
    """OCR processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TimelineEntryType(str, enum.Enum):
    """Timeline entry categories."""
    APPLICATION_CREATED = "application_created"
    STAGE_CHANGED = "stage_changed"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_VERIFIED = "document_verified"
    COMMENT_ADDED = "comment_added"
    ASSIGNED = "assigned"
    EMAIL_SENT = "email_sent"
    SYSTEM_EVENT = "system_event"


# ============================================================================
# MODELS
# ============================================================================

class RtoProfile(Base):
    """
    RTO (Registered Training Organization) profile for multi-tenancy.
    Stores organization metadata, branding, and business settings.
    """
    __tablename__ = "rto_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    abn = Column(String(20), nullable=True)
    cricos_code = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # JSONB fields
    address = Column(JSONB, nullable=True)  # {street, city, state, postcode, country}
    logo_url = Column(String(500), nullable=True)
    brand_settings = Column(JSONB, nullable=True)  # {primary_color, secondary_color, font_family}
    business_settings = Column(JSONB, nullable=True)  # {default_commission_rate, sla_overrides, features_enabled}
    
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("UserAccount", back_populates="rto_profile")
    
    def __repr__(self):
        return f"<RtoProfile(id={self.id}, name='{self.name}')>"


class UserAccount(Base):
    """
    Unified user account for all roles (student, agent, staff, admin).
    Role determines which profile table (agent_profile, staff_profile, student_profile) to join.
    """
    __tablename__ = "user_account"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    rto_profile_id = Column(UUID(as_uuid=True), ForeignKey("rto_profile.id"), nullable=False, index=True)
    
    # Security
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(String(32), nullable=True)  # Base32 encoded TOTP secret
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    
    # JSONB fields
    notification_preferences = Column(JSONB, nullable=True)  # {email: {enabled, frequency}, sms: {...}, in_app: {...}}
    admin_config = Column(JSONB, nullable=True)  # For staff/admin: workflow_sla, default_templates
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    rto_profile = relationship("RtoProfile", back_populates="users")
    agent_profile = relationship("AgentProfile", back_populates="user_account", uselist=False)
    staff_profile = relationship("StaffProfile", back_populates="user_account", uselist=False)
    student_profile = relationship("StudentProfile", back_populates="user_account", uselist=False)
    
    # Documents uploaded by this user
    uploaded_documents = relationship("Document", foreign_keys="Document.uploaded_by", back_populates="uploader")
    
    # Timeline entries created by this user
    timeline_entries = relationship("TimelineEntry", foreign_keys="TimelineEntry.actor_id", back_populates="actor")
    
    # Audit logs
    audit_logs = relationship("AuditLog", back_populates="actor")
    
    def __repr__(self):
        return f"<UserAccount(id={self.id}, email='{self.email}', role={self.role.value})>"


class AgentProfile(Base):
    """Agent-specific profile information."""
    __tablename__ = "agent_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), unique=True, nullable=False)
    
    agency_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    commission_rate = Column(Numeric(5, 2), nullable=True)  # e.g., 15.00 for 15%
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user_account = relationship("UserAccount", back_populates="agent_profile")
    applications = relationship("Application", back_populates="agent")
    
    def __repr__(self):
        return f"<AgentProfile(id={self.id}, agency='{self.agency_name}')>"


class StaffProfile(Base):
    """Staff/admin-specific profile information."""
    __tablename__ = "staff_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), unique=True, nullable=False)
    
    department = Column(String(100), nullable=True)
    job_title = Column(String(100), nullable=True)
    
    # JSONB field
    permissions = Column(JSONB, nullable=True)  # {can_approve_applications, can_manage_users, ...}
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user_account = relationship("UserAccount", back_populates="staff_profile")
    assigned_applications = relationship("Application", foreign_keys="Application.assigned_staff_id", back_populates="assigned_staff")
    
    def __repr__(self):
        return f"<StaffProfile(id={self.id}, title='{self.job_title}')>"


class StudentProfile(Base):
    """Student-specific profile information."""
    __tablename__ = "student_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), unique=True, nullable=False)
    
    given_name = Column(String(100), nullable=False)
    family_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    passport_number = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    visa_type = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user_account = relationship("UserAccount", back_populates="student_profile")
    applications = relationship("Application", back_populates="student")
    
    def __repr__(self):
        return f"<StudentProfile(id={self.id}, name='{self.given_name} {self.family_name}')>"


class CourseOffering(Base):
    """Course catalog with intake and pricing information."""
    __tablename__ = "course_offering"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_code = Column(String(50), unique=True, nullable=False, index=True)
    course_name = Column(String(255), nullable=False)
    intake = Column(String(50), nullable=False)  # e.g., "2025 Semester 1"
    campus = Column(String(100), nullable=False)
    tuition_fee = Column(Numeric(10, 2), nullable=False)
    application_deadline = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    applications = relationship("Application", back_populates="course")
    
    def __repr__(self):
        return f"<CourseOffering(code='{self.course_code}', name='{self.course_name}')>"


class Application(Base):
    """
    Central application record with extensive JSONB fields.
    Consolidates enrollment, emergency contacts, health cover, disability, language,
    survey responses, additional services, GS assessment, signatures, and metadata.
    """
    __tablename__ = "application"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_profile_id = Column(UUID(as_uuid=True), ForeignKey("student_profile.id"), nullable=False, index=True)
    agent_profile_id = Column(UUID(as_uuid=True), ForeignKey("agent_profile.id"), nullable=True, index=True)
    course_offering_id = Column(UUID(as_uuid=True), ForeignKey("course_offering.id"), nullable=False, index=True)
    assigned_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profile.id"), nullable=True, index=True)
    
    # Workflow
    current_stage = Column(SQLEnum(ApplicationStage), nullable=False, default=ApplicationStage.DRAFT, index=True)
    submitted_at = Column(DateTime, nullable=True)
    decision_at = Column(DateTime, nullable=True)
    
    # USI (Unique Student Identifier)
    usi = Column(String(20), nullable=True)
    usi_verified = Column(Boolean, nullable=False, default=False)
    usi_verified_at = Column(DateTime, nullable=True)
    
    # JSONB fields (10 total - consolidated from 19 former tables)
    enrollment_data = Column(JSONB, nullable=True)  # {status, offer_signed_at, fee_received_at, coe_uploaded_at}
    emergency_contacts = Column(JSONB, nullable=True)  # [{name, relationship, phone, email, is_primary}]
    health_cover_policy = Column(JSONB, nullable=True)  # {provider, policy_number, start_date, end_date, coverage_type}
    disability_support = Column(JSONB, nullable=True)  # {has_disability, disability_details, support_required, documentation_status}
    language_cultural_data = Column(JSONB, nullable=True)  # {first_language, other_languages, indigenous_status, country_of_birth, citizenship_status}
    survey_responses = Column(JSONB, nullable=True)  # [{question_id, question_text, answer}]
    additional_services = Column(JSONB, nullable=True)  # [{service_id, name, fee, selected_at}]
    gs_assessment = Column(JSONB, nullable=True)  # {interview_date, staff_id, scorecard, decision, notes}
    signature_data = Column(JSONB, nullable=True)  # {envelope_id, provider, status, cost_cents, expires_at, completed_at, parties: [{role, name, email, signed_at}]}
    form_metadata = Column(JSONB, nullable=True)  # {version, ip_address, user_agent, submission_duration_seconds}
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("StudentProfile", back_populates="applications")
    agent = relationship("AgentProfile", back_populates="applications")
    course = relationship("CourseOffering", back_populates="applications")
    assigned_staff = relationship("StaffProfile", back_populates="assigned_applications")
    
    stage_history = relationship("ApplicationStageHistory", back_populates="application")
    schooling_history = relationship("SchoolingHistory", back_populates="application", order_by="SchoolingHistory.display_order")
    qualification_history = relationship("QualificationHistory", back_populates="application", order_by="QualificationHistory.display_order")
    employment_history = relationship("EmploymentHistory", back_populates="application", order_by="EmploymentHistory.display_order")
    documents = relationship("Document", back_populates="application")
    timeline_entries = relationship("TimelineEntry", back_populates="application")
    
    def __repr__(self):
        return f"<Application(id={self.id}, stage={self.current_stage.value})>"


# GIN indexes for JSONB fields in APPLICATION
Index("idx_application_enrollment", Application.enrollment_data, postgresql_using="gin")
Index("idx_application_emergency", Application.emergency_contacts, postgresql_using="gin")
Index("idx_application_health_cover", Application.health_cover_policy, postgresql_using="gin")
Index("idx_application_disability", Application.disability_support, postgresql_using="gin")
Index("idx_application_language", Application.language_cultural_data, postgresql_using="gin")
Index("idx_application_survey", Application.survey_responses, postgresql_using="gin")
Index("idx_application_services", Application.additional_services, postgresql_using="gin")
Index("idx_application_gs_assessment", Application.gs_assessment, postgresql_using="gin")
Index("idx_application_signatures", Application.signature_data, postgresql_using="gin")


class ApplicationStageHistory(Base):
    """
    Tracks all application workflow transitions.
    Critical for SLA reporting and audit trail.
    """
    __tablename__ = "application_stage_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    from_stage = Column(SQLEnum(ApplicationStage), nullable=True)  # NULL for initial creation
    to_stage = Column(SQLEnum(ApplicationStage), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=True)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    application = relationship("Application", back_populates="stage_history")
    
    def __repr__(self):
        return f"<ApplicationStageHistory(app={self.application_id}, {self.from_stage} → {self.to_stage})>"


class SchoolingHistory(Base):
    """Student's schooling/education background (variable-length list)."""
    __tablename__ = "schooling_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    
    institution = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False, index=True)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=True)  # NULL if currently attending
    qualification_level = Column(String(100), nullable=False)  # e.g., "High School Diploma", "Bachelor's Degree"
    result = Column(String(100), nullable=True)  # e.g., GPA, percentage
    display_order = Column(Integer, nullable=False, default=0)
    
    # Relationships
    application = relationship("Application", back_populates="schooling_history")
    
    def __repr__(self):
        return f"<SchoolingHistory(institution='{self.institution}', {self.start_year}-{self.end_year})>"


class QualificationHistory(Base):
    """Professional qualifications and certifications."""
    __tablename__ = "qualification_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    
    qualification_name = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=False)
    completion_date = Column(Date, nullable=False)
    certificate_number = Column(String(100), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    
    # Relationships
    application = relationship("Application", back_populates="qualification_history")
    
    def __repr__(self):
        return f"<QualificationHistory(qual='{self.qualification_name}')>"


class EmploymentHistory(Base):
    """Work experience records."""
    __tablename__ = "employment_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    
    employer = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL if currently employed
    responsibilities = Column(Text, nullable=True)
    is_current = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    
    # Relationships
    application = relationship("Application", back_populates="employment_history")
    
    def __repr__(self):
        return f"<EmploymentHistory(employer='{self.employer}', role='{self.role}')>"


class DocumentType(Base):
    """
    Document category catalog (e.g., Passport, Academic Transcripts, COE).
    Defines mandatory documents per stage and OCR model references.
    """
    __tablename__ = "document_type"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    stage = Column(SQLEnum(ApplicationStage), nullable=False)  # Which stage requires this document
    is_mandatory = Column(Boolean, nullable=False, default=True)
    ocr_model_ref = Column(String(100), nullable=True)  # Azure Form Recognizer model ID
    display_order = Column(Integer, nullable=False, default=0)
    
    # Relationships
    documents = relationship("Document", back_populates="document_type")
    
    def __repr__(self):
        return f"<DocumentType(code='{self.code}', name='{self.name}')>"


class Document(Base):
    """
    Document record linked to application.
    Each document can have multiple versions (immutable history).
    """
    __tablename__ = "document"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    document_type_id = Column(UUID(as_uuid=True), ForeignKey("document_type.id"), nullable=False, index=True)
    
    status = Column(SQLEnum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # OCR processing
    ocr_status = Column(SQLEnum(OCRStatus), nullable=False, default=OCRStatus.PENDING)
    ocr_completed_at = Column(DateTime, nullable=True)
    
    # JSONB field
    gs_document_requests = Column(JSONB, nullable=True)  # [{requested_by, requested_at, due_at, status}]
    
    # Relationships
    application = relationship("Application", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    uploader = relationship("UserAccount", foreign_keys=[uploaded_by], back_populates="uploaded_documents")
    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number")
    timeline_entries = relationship("TimelineEntry", back_populates="linked_document")
    
    def __repr__(self):
        return f"<Document(id={self.id}, type={self.document_type.code if self.document_type else 'N/A'})>"


# GIN index for JSONB field in DOCUMENT
Index("idx_document_gs_requests", Document.gs_document_requests, postgresql_using="gin")


class DocumentVersion(Base):
    """
    Immutable document version history.
    Each upload creates a new version (never update blob_url).
    """
    __tablename__ = "document_version"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id"), nullable=False, index=True)
    
    blob_url = Column(String(1000), nullable=False)  # Azure Blob Storage URL
    checksum = Column(String(64), nullable=False)  # SHA256 for integrity
    file_size_bytes = Column(Integer, nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # OCR results
    ocr_json = Column(JSONB, nullable=True)  # Raw Azure Form Recognizer output
    preview_url = Column(String(1000), nullable=True)  # Thumbnail or preview image
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="versions")
    
    def __repr__(self):
        return f"<DocumentVersion(doc={self.document_id}, v{self.version_number})>"


class TimelineEntry(Base):
    """
    Application activity timeline (user-facing feed).
    Consolidates workflow events with event_payload JSONB.
    """
    __tablename__ = "timeline_entry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False, index=True)
    
    entry_type = Column(SQLEnum(TimelineEntryType), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=True)
    actor_role = Column(SQLEnum(UserRole), nullable=True)
    message = Column(Text, nullable=False)
    
    # Optional references
    stage = Column(SQLEnum(ApplicationStage), nullable=True)
    linked_document_id = Column(UUID(as_uuid=True), ForeignKey("document.id"), nullable=True)
    
    # JSONB field (replaces WORKFLOW_EVENT table)
    event_payload = Column(JSONB, nullable=True)  # {event_type, metadata, triggered_by}
    correlation_id = Column(String(100), nullable=True, index=True)  # For grouping related events
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    is_pinned = Column(Boolean, nullable=False, default=False)  # Pin important entries to top
    
    # Relationships
    application = relationship("Application", back_populates="timeline_entries")
    actor = relationship("UserAccount", foreign_keys=[actor_id], back_populates="timeline_entries")
    linked_document = relationship("Document", back_populates="timeline_entries")
    
    def __repr__(self):
        return f"<TimelineEntry(app={self.application_id}, type={self.entry_type.value})>"


# GIN index for JSONB field in TIMELINE_ENTRY
Index("idx_timeline_event_payload", TimelineEntry.event_payload, postgresql_using="gin")


class AuditLog(Base):
    """
    Comprehensive immutable audit trail for compliance.
    Superset of timeline (includes system actions, data changes, security events).
    """
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    entity_type = Column(String(50), nullable=False, index=True)  # e.g., "application", "document", "user_account"
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # e.g., "create", "update", "delete", "login", "permission_change"
    
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_account.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    
    payload_json = Column(JSONB, nullable=True)  # Full snapshot of changed data
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    actor = relationship("UserAccount", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(entity={self.entity_type}:{self.entity_id}, action={self.action})>"


# GIN index for JSONB field in AUDIT_LOG
Index("idx_audit_payload", AuditLog.payload_json, postgresql_using="gin")
