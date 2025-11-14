# Database Schema Migration: v2.0 → v3.1 (Lean JSONB-First Architecture + RTO Profile)

**Date:** November 14, 2025  
**Impact:** MAJOR BREAKING CHANGE - Aggressive table consolidation + organization management for MVP  
**Migration Complexity:** High  

## Summary

Refactored from **28 tables (v2.0) to 16 tables** (-43% reduction from v2.0, **-53% from original 34 tables**) by adopting a lean JSONB-first MVP approach with proper organization/RTO management. This migration consolidates 19 tables into JSONB fields across 4 core entities, drops 3 tables entirely (replaced by external services/config), merges workflow events into timeline, and adds RTO_PROFILE for multi-tenancy.

**Philosophy:** Start lean with JSONB for MVP. Normalize only when actual usage patterns (not anticipated needs) demand it.

---

## Architecture Evolution

| Version | Total Tables | Philosophy | Target Scale |
|---------|-------------|------------|--------------|
| v1.0 | 34 | Fully normalized | 100k+ applications |
| v2.0 | 28 | Hybrid normalized + JSONB | 50k+ applications |
| v3.0 | 15 | Lean JSONB-first | 5k-20k applications (MVP) |
| v3.1 | 16 | **Lean + RTO management** | **5k-20k applications (MVP)** |

---

## New Table Added (v3.1)

### `RTO_PROFILE` - Organization/Multi-Tenancy Management

**Purpose:** Store RTO/organization metadata to enable proper multi-tenancy and future SaaS expansion.

**Schema:**
```sql
CREATE TABLE rto_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,                    -- "Churchill Education"
    abn VARCHAR,                              -- Australian Business Number
    cricos_code VARCHAR,                      -- CRICOS provider code
    contact_email VARCHAR,
    contact_phone VARCHAR,
    address JSONB,                            -- {"street": "...", "city": "...", "state": "...", "postcode": "..."}
    logo_url VARCHAR,                         -- Azure Blob URL for logo
    brand_settings JSONB,                     -- {"primary_color": "#1a73e8", "secondary_color": "#34a853"}
    business_settings JSONB,                  -- {"default_commission_rate": 15, "currency": "AUD", "sla_overrides": {...}}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rename tenant_id to rto_profile_id in USER_ACCOUNT
ALTER TABLE user_account 
RENAME COLUMN tenant_id TO rto_profile_id;

-- Add foreign key constraint
ALTER TABLE user_account 
ADD CONSTRAINT fk_rto_profile 
FOREIGN KEY (rto_profile_id) REFERENCES rto_profile(id);
```

**Migration Strategy:**
```sql
-- Step 1: Create RTO_PROFILE table
CREATE TABLE rto_profile (...);

-- Step 2: Insert Churchill Education record
INSERT INTO rto_profile (id, name, abn, cricos_code, contact_email, is_active)
VALUES (
  gen_random_uuid(),  -- Or use fixed UUID for Churchill
  'Churchill Education',
  '12345678901',      -- Replace with actual ABN
  'CRICOS_CODE',      -- Replace with actual CRICOS code
  'info@churchill.edu.au',
  true
);

-- Step 3: Rename column in USER_ACCOUNT
ALTER TABLE user_account 
RENAME COLUMN tenant_id TO rto_profile_id;

-- Step 4: Add FK constraint
ALTER TABLE user_account 
ADD CONSTRAINT fk_rto_profile 
FOREIGN KEY (rto_profile_id) REFERENCES rto_profile(id);
```

**Rationale:**
- Provides proper organization metadata (RTO name, ABN, CRICOS)
- Enables white-label branding (logo, colors) per RTO
- Supports business settings (commission rates, SLA overrides) per organization
- Future-proofs for multi-RTO SaaS expansion
- JSONB fields keep it flexible (no rigid columns for evolving requirements)

---

## Tables Consolidated into `APPLICATION` (10 JSONB fields)

### 1. `COURSE_ENROLLMENT` → `application.enrollment_data` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE course_enrollment (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    enrollment_status VARCHAR,
    offer_signed_at TIMESTAMP,
    fee_received_at TIMESTAMP,
    coe_uploaded_at TIMESTAMP
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN enrollment_data JSONB;

-- Example data:
{
  "status": "enrolled",
  "offer_signed_at": "2025-11-10T14:30:00Z",
  "fee_received_at": "2025-11-15T09:00:00Z",
  "coe_uploaded_at": "2025-11-20T16:45:00Z"
}
```

**Migration SQL:**
```sql
UPDATE application a
SET enrollment_data = (
  SELECT jsonb_build_object(
    'status', ce.enrollment_status,
    'offer_signed_at', ce.offer_signed_at,
    'fee_received_at', ce.fee_received_at,
    'coe_uploaded_at', ce.coe_uploaded_at
  )
  FROM course_enrollment ce
  WHERE ce.application_id = a.id
);

DROP TABLE course_enrollment;
```

**Rationale:** Each application has exactly 0 or 1 enrollment record. JSONB eliminates JOIN overhead for simple status tracking.

**Promote to table when:** You need to report across 10,000+ enrollments with complex date range filters on enrollment milestones.

---

### 2. `EMERGENCY_CONTACT` → `application.emergency_contacts` (JSONB array)

**Before (separate table):**
```sql
CREATE TABLE emergency_contact (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    name VARCHAR,
    relationship VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    address TEXT,
    is_primary BOOLEAN
);
```

**After (JSONB array):**
```sql
ALTER TABLE application ADD COLUMN emergency_contacts JSONB;

-- Example data:
[
  {
    "name": "John Doe",
    "relationship": "Father",
    "phone": "+61412345678",
    "email": "john@example.com",
    "address": "123 Main St, Sydney NSW 2000",
    "is_primary": true
  },
  {
    "name": "Jane Doe",
    "relationship": "Mother",
    "phone": "+61498765432",
    "email": "jane@example.com",
    "is_primary": false
  }
]
```

**Migration SQL:**
```sql
UPDATE application a
SET emergency_contacts = (
  SELECT jsonb_agg(
    jsonb_build_object(
      'name', ec.name,
      'relationship', ec.relationship,
      'phone', ec.phone,
      'email', ec.email,
      'address', ec.address,
      'is_primary', ec.is_primary
    )
  )
  FROM emergency_contact ec
  WHERE ec.application_id = a.id
);

DROP TABLE emergency_contact;
```

**Rationale:** Emergency contacts are displayed as a list on the application form. No complex JOIN or filtering requirements for MVP.

**Promote to table when:** You need fraud detection ("find all applications with duplicate emergency contact phone numbers") or deduplication analytics.

---

### 3. `HEALTH_COVER_POLICY` → `application.health_cover_policy` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE health_cover_policy (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    provider VARCHAR,
    policy_number VARCHAR,
    start_date DATE,
    end_date DATE,
    coverage_type VARCHAR
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN health_cover_policy JSONB;

-- Example data:
{
  "provider": "Allianz",
  "policy_number": "POL-123456",
  "start_date": "2025-02-01",
  "end_date": "2026-02-01",
  "coverage_type": "Basic"
}
```

**Migration SQL:**
```sql
UPDATE application a
SET health_cover_policy = (
  SELECT jsonb_build_object(
    'provider', hcp.provider,
    'policy_number', hcp.policy_number,
    'start_date', hcp.start_date,
    'end_date', hcp.end_date,
    'coverage_type', hcp.coverage_type
  )
  FROM health_cover_policy hcp
  WHERE hcp.application_id = a.id
);

DROP TABLE health_cover_policy;
```

**Rationale:** Each application has exactly 0 or 1 policy. GIN index supports expiry date filtering: `WHERE (health_cover_policy->>'end_date')::date < CURRENT_DATE + INTERVAL '30 days'`.

**Promote to table when:** You need to build compliance dashboards with complex date range queries across 10,000+ policies, or integrate with insurance provider APIs requiring normalized data.

---

### 4. `DISABILITY_SUPPORT` → `application.disability_support` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE disability_support (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    has_disability BOOLEAN,
    disability_details TEXT,
    support_required TEXT,
    documentation_status VARCHAR
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN disability_support JSONB;

-- Example data:
{
  "has_disability": true,
  "disability_details": "Hearing impairment",
  "support_required": "Sign language interpreter for classes",
  "documentation_status": "verified"
}
```

**Migration SQL:**
```sql
UPDATE application a
SET disability_support = (
  SELECT jsonb_build_object(
    'has_disability', ds.has_disability,
    'disability_details', ds.disability_details,
    'support_required', ds.support_required,
    'documentation_status', ds.documentation_status
  )
  FROM disability_support ds
  WHERE ds.application_id = a.id
);

DROP TABLE disability_support;
```

**Rationale:** Disability support data is primarily for compliance/documentation. Rarely filtered or aggregated for MVP.

**Promote to table when:** You need resource allocation reporting ("how many students require sign language interpreters per campus?") across 5,000+ applications.

---

### 5. `ADDITIONAL_SERVICE` + `APPLICATION_ADDITIONAL_SERVICE` → `application.additional_services` (JSONB array)

**Before (two tables):**
```sql
CREATE TABLE additional_service (
    id UUID PRIMARY KEY,
    name VARCHAR,
    description TEXT,
    fee DECIMAL
);

CREATE TABLE application_additional_service (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    additional_service_id UUID REFERENCES additional_service(id),
    selected_at TIMESTAMP,
    notes TEXT
);
```

**After (JSONB array):**
```sql
ALTER TABLE application ADD COLUMN additional_services JSONB;

-- Example data:
[
  {
    "service_id": "uuid-1",
    "name": "Airport Pickup",
    "fee": 150.00,
    "selected_at": "2025-11-14T10:00:00Z",
    "notes": "Flight arrives at 6 PM"
  },
  {
    "service_id": "uuid-2",
    "name": "Accommodation Assistance",
    "fee": 200.00,
    "selected_at": "2025-11-14T10:00:00Z",
    "notes": null
  }
]
```

**Migration SQL:**
```sql
UPDATE application a
SET additional_services = (
  SELECT jsonb_agg(
    jsonb_build_object(
      'service_id', aas.additional_service_id,
      'name', addsvc.name,
      'fee', addsvc.fee,
      'selected_at', aas.selected_at,
      'notes', aas.notes
    )
  )
  FROM application_additional_service aas
  JOIN additional_service addsvc ON aas.additional_service_id = addsvc.id
  WHERE aas.application_id = a.id
);

DROP TABLE application_additional_service;
DROP TABLE additional_service;
```

**Rationale:** Additional services catalog is small (< 20 items). Denormalizing into JSONB array avoids junction table complexity.

**Promote to table when:** Service catalog grows to 100+ items, or you need complex pricing rules, or referential integrity validation becomes critical.

---

### 6. `GS_ASSESSMENT` → `application.gs_assessment` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE gs_assessment (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    staff_id UUID,
    interview_date TIMESTAMP,
    scorecard_json JSONB,
    decision VARCHAR,
    notes TEXT
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN gs_assessment JSONB;

-- Example data:
{
  "staff_id": "uuid-staff-123",
  "interview_date": "2025-11-18T10:00:00Z",
  "scorecard": {
    "genuine_intent": 8,
    "english_proficiency": 7,
    "financial_capacity": 9
  },
  "decision": "approved",
  "notes": "Strong candidate with clear study goals"
}
```

**Migration SQL:**
```sql
UPDATE application a
SET gs_assessment = (
  SELECT jsonb_build_object(
    'staff_id', gsa.staff_id,
    'interview_date', gsa.interview_date,
    'scorecard', gsa.scorecard_json,
    'decision', gsa.decision,
    'notes', gsa.notes
  )
  FROM gs_assessment gsa
  WHERE gsa.application_id = a.id
);

DROP TABLE gs_assessment;
```

**Rationale:** Each application has exactly 0 or 1 GS assessment. Scorecard is already JSONB. No need for separate table.

**Promote to table when:** You need GS assessment analytics dashboard with filtering by staff member, date ranges, scorecard trends across 10,000+ assessments.

---

### 7. `SIGNATURE_ENVELOPE` + `SIGNATURE_PARTY` → `application.signature_data` (JSONB)

**Before (two tables):**
```sql
CREATE TABLE signature_envelope (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    provider VARCHAR,
    envelope_id VARCHAR,
    document_bundle JSONB,
    status VARCHAR,
    cost_cents INT,
    expires_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE signature_party (
    id UUID PRIMARY KEY,
    signature_envelope_id UUID REFERENCES signature_envelope(id),
    role VARCHAR,
    name VARCHAR,
    email VARCHAR,
    auth_method VARCHAR,
    signed_at TIMESTAMP,
    ip_address INET
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN signature_data JSONB;

-- Example data:
{
  "envelope_id": "docuseal-123",
  "provider": "DocuSeal",
  "status": "completed",
  "cost_cents": 0,
  "expires_at": "2025-12-01T00:00:00Z",
  "completed_at": "2025-11-14T15:30:00Z",
  "document_bundle": ["offer_letter.pdf", "terms_conditions.pdf"],
  "parties": [
    {
      "role": "student",
      "name": "John Smith",
      "email": "john@example.com",
      "auth_method": "email_otp",
      "signed_at": "2025-11-14T15:30:00Z",
      "ip_address": "203.45.67.89"
    },
    {
      "role": "agent",
      "name": "Agent Name",
      "email": "agent@example.com",
      "signed_at": "2025-11-14T14:00:00Z"
    }
  ]
}
```

**Migration SQL:**
```sql
UPDATE application a
SET signature_data = (
  SELECT jsonb_build_object(
    'envelope_id', se.envelope_id,
    'provider', se.provider,
    'status', se.status,
    'cost_cents', se.cost_cents,
    'expires_at', se.expires_at,
    'completed_at', se.completed_at,
    'document_bundle', se.document_bundle,
    'parties', (
      SELECT jsonb_agg(
        jsonb_build_object(
          'role', sp.role,
          'name', sp.name,
          'email', sp.email,
          'auth_method', sp.auth_method,
          'signed_at', sp.signed_at,
          'ip_address', sp.ip_address
        )
      )
      FROM signature_party sp
      WHERE sp.signature_envelope_id = se.id
    )
  )
  FROM signature_envelope se
  WHERE se.application_id = a.id
);

DROP TABLE signature_party;
DROP TABLE signature_envelope;
```

**Rationale:** Each application has exactly 0 or 1 signature envelope. Parties array is small (1-3 signers). No complex JOIN requirements for MVP.

**Promote to table when:** You build e-signature analytics ("average signing time by role", "abandonment rate by provider") across 10,000+ envelopes.

---

## Tables Consolidated into `USER_ACCOUNT` (2 JSONB fields)

### 8. `NOTIFICATION_PREFERENCE` → `user_account.notification_preferences` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE notification_preference (
    id UUID PRIMARY KEY,
    user_account_id UUID REFERENCES user_account(id),
    channel VARCHAR,
    frequency VARCHAR,
    mute_until TIMESTAMP,
    created_at TIMESTAMP
);
```

**After (JSONB column):**
```sql
ALTER TABLE user_account ADD COLUMN notification_preferences JSONB;

-- Example data:
{
  "email": {
    "enabled": true,
    "frequency": "instant",
    "mute_until": null
  },
  "sms": {
    "enabled": false
  },
  "in_app": {
    "enabled": true,
    "frequency": "instant"
  }
}
```

**Migration SQL:**
```sql
UPDATE user_account ua
SET notification_preferences = (
  SELECT jsonb_object_agg(
    np.channel,
    jsonb_build_object(
      'enabled', true,
      'frequency', np.frequency,
      'mute_until', np.mute_until
    )
  )
  FROM notification_preference np
  WHERE np.user_account_id = ua.id
);

DROP TABLE notification_preference;
```

**Rationale:** Each user has 2-3 channel preferences. JSONB provides flexible nested structure without table overhead.

**Promote to table when:** Never (notification preferences are inherently user-specific configuration data).

---

### 9. `STAFF_ADMIN_CONFIG` → `user_account.admin_config` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE staff_admin_config (
    id UUID PRIMARY KEY,
    user_account_id UUID REFERENCES user_account(id),
    config_key VARCHAR,
    config_value JSONB
);
```

**After (JSONB column):**
```sql
ALTER TABLE user_account ADD COLUMN admin_config JSONB;

-- Example data:
{
  "workflow_sla": {
    "submitted": {
      "target_hours": 24,
      "escalation_hours": 48
    },
    "staff_review": {
      "target_hours": 72,
      "escalation_hours": 120
    }
  },
  "default_templates": {
    "offer_letter": "templates/offer_letter_v2.docx",
    "coe": "templates/coe_v1.docx"
  }
}
```

**Migration SQL:**
```sql
UPDATE user_account ua
SET admin_config = (
  SELECT jsonb_object_agg(sac.config_key, sac.config_value)
  FROM staff_admin_config sac
  WHERE sac.user_account_id = ua.id
);

DROP TABLE staff_admin_config;
```

**Rationale:** Admin configuration is per-user, unstructured, and rarely queried globally.

**Promote to table when:** You build admin configuration auditing or need to query across all staff configurations frequently.

---

## Tables Consolidated into `DOCUMENT` (1 JSONB field)

### 10. `GS_DOCUMENT_REQUEST` → `document.gs_document_requests` (JSONB array)

**Before (separate table):**
```sql
CREATE TABLE gs_document_request (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    document_type_id UUID,
    requested_by UUID,
    requested_at TIMESTAMP,
    due_at TIMESTAMP,
    status VARCHAR
);
```

**After (JSONB array on DOCUMENT table):**
```sql
ALTER TABLE document ADD COLUMN gs_document_requests JSONB;

-- Example data:
[
  {
    "document_type_id": "uuid-passport",
    "requested_by": "uuid-staff-123",
    "requested_at": "2025-11-15T10:00:00Z",
    "due_at": "2025-11-22T10:00:00Z",
    "status": "pending"
  },
  {
    "document_type_id": "uuid-bank-statement",
    "requested_by": "uuid-staff-123",
    "requested_at": "2025-11-16T14:00:00Z",
    "due_at": "2025-11-23T14:00:00Z",
    "status": "fulfilled"
  }
]
```

**Migration SQL:**
```sql
-- This migration is complex because GS_DOCUMENT_REQUEST referenced application_id, not document_id
-- We'll need to match requests to documents via document_type_id

UPDATE document d
SET gs_document_requests = (
  SELECT jsonb_agg(
    jsonb_build_object(
      'document_type_id', gdr.document_type_id,
      'requested_by', gdr.requested_by,
      'requested_at', gdr.requested_at,
      'due_at', gdr.due_at,
      'status', gdr.status
    )
  )
  FROM gs_document_request gdr
  WHERE gdr.application_id = d.application_id
    AND gdr.document_type_id = d.document_type_id
);

DROP TABLE gs_document_request;
```

**Rationale:** GS document requests are tightly coupled to specific documents. JSONB array tracks request history per document.

**Promote to table when:** You need GS compliance reporting ("average response time to document requests") across 10,000+ requests.

---

## Tables Consolidated into `TIMELINE_ENTRY` (2 fields)

### 11. `WORKFLOW_EVENT` → `timeline_entry.event_payload` + `correlation_id`

**Before (separate table):**
```sql
CREATE TABLE workflow_event (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    event_type VARCHAR,
    payload_json JSONB,
    emitted_at TIMESTAMP,
    correlation_id VARCHAR
);
```

**After (JSONB column + correlation_id column):**
```sql
ALTER TABLE timeline_entry 
ADD COLUMN event_payload JSONB,
ADD COLUMN correlation_id VARCHAR;

-- Example data (event_payload):
{
  "event_type": "offer_generated",
  "metadata": {
    "template_used": "offer_letter_v2.docx",
    "generated_by": "staff-uuid-123"
  },
  "triggered_by": "system"
}
```

**Migration SQL:**
```sql
-- Insert workflow events as timeline entries
INSERT INTO timeline_entry (
  id, application_id, entry_type, actor_id, actor_role, message, stage, 
  created_at, event_payload, correlation_id
)
SELECT 
  gen_random_uuid(),
  we.application_id,
  'system_event',
  NULL,
  'system',
  we.event_type,
  (SELECT current_stage FROM application WHERE id = we.application_id),
  we.emitted_at,
  we.payload_json,
  we.correlation_id
FROM workflow_event we;

DROP TABLE workflow_event;
```

**Rationale:** TIMELINE_ENTRY is already the unified activity log. Adding `event_payload` and `correlation_id` eliminates redundant WORKFLOW_EVENT table.

**Promote to table when:** You build complex event sourcing patterns or need to query workflow events independently from timeline (unlikely for this domain).

---

## Tables Dropped Entirely (Replaced by External Services/Config)

### 12. `NOTIFICATION` → Use Celery Task Results + In-App Toasts

**Before (separate table):**
```sql
CREATE TABLE notification (
    id UUID PRIMARY KEY,
    timeline_entry_id UUID,
    recipient_user_id UUID,
    channel VARCHAR,
    status VARCHAR,
    sent_at TIMESTAMP,
    read_at TIMESTAMP
);
```

**After:** Remove table entirely. Use Celery task results for delivery tracking + in-app toasts for real-time notifications.

**Migration Strategy:**
- **Email notifications**: Celery task logs stored in Redis (or PostgreSQL via `django-celery-results` if needed later)
- **In-app notifications**: WebSocket toasts (no persistence required for MVP)
- **Notification inbox feature**: If needed later, create `NOTIFICATION` table from Celery task history

**Rationale:** Persistent notification table is over-engineering for MVP. Most notifications are transient. If notification inbox is required, easy to add later.

**Add table back when:** Users request "notification inbox" feature with read/unread tracking, or compliance requires notification delivery audit trail.

---

### 13. `DOCUMENT_TEMPLATE` → Use Azure Blob Filename Conventions

**Before (separate table):**
```sql
CREATE TABLE document_template (
    id UUID PRIMARY KEY,
    name VARCHAR,
    template_type VARCHAR,
    blob_url VARCHAR,
    version INT,
    active BOOLEAN
);
```

**After:** Remove table entirely. Use Azure Blob Storage with structured folder/filename conventions:
```
templates/
  offer_letter_v2.docx
  coe_v1.docx
  enrollment_form_v3.pdf
```

**Migration Strategy:**
- Migrate existing template records to Azure Blob with version suffix
- Reference templates in code via filename constants or environment variables
- Template versioning handled by filename convention

**Rationale:** Template catalog is small (< 20 templates), managed by admins via Azure Storage Explorer. No need for database table.

**Add table back when:** You need template metadata (created_by, approval workflow, variables schema) or dynamic template selection logic.

---

### 14. `WORKFLOW_STAGE_SLA` → Use YAML Config File or `user_account.admin_config`

**Before (separate table):**
```sql
CREATE TABLE workflow_stage_sla (
    id UUID PRIMARY KEY,
    stage VARCHAR,
    target_hours INT,
    escalation_hours INT,
    notification_template VARCHAR
);
```

**After:** Remove table entirely. Use YAML configuration file:
```yaml
# config/sla.yml
workflow_sla:
  submitted:
    target_hours: 24
    escalation_hours: 48
  staff_review:
    target_hours: 72
    escalation_hours: 120
  genuine_student_assessment:
    target_hours: 96
    escalation_hours: 168
```

Or store in `user_account.admin_config` JSONB for per-tenant customization.

**Migration Strategy:**
- Export existing SLA records to YAML file
- Load SLA config at application startup via FastAPI settings
- Override via `user_account.admin_config` JSONB for tenant-specific SLA rules

**Rationale:** SLA thresholds change infrequently, managed by admins. YAML provides version control and simpler deployment than database table.

**Add table back when:** You need per-course, per-campus, or per-agent SLA customization with complex business rules.

---

## SQLAlchemy Model Changes

**New Model (v3.1): RTO_PROFILE**
```python
class RtoProfile(Base):
    __tablename__ = "rto_profile"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    abn: Mapped[str] = mapped_column(String, nullable=True)
    cricos_code: Mapped[str] = mapped_column(String, nullable=True)
    contact_email: Mapped[str] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str] = mapped_column(String, nullable=True)
    
    # JSONB fields for flexible metadata
    address: Mapped[dict] = mapped_column(JSONB, nullable=True)
    brand_settings: Mapped[dict] = mapped_column(JSONB, nullable=True)
    business_settings: Mapped[dict] = mapped_column(JSONB, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users: Mapped[List["UserAccount"]] = relationship(back_populates="rto_profile")
```

**Updated Model (v3.1): USER_ACCOUNT**
```python
class UserAccount(Base):
    __tablename__ = "user_account"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # Enum: agent, staff, student, admin
    
    # v3.1 - renamed tenant_id to rto_profile_id
    rto_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rto_profile.id"), nullable=False)
    
    # v3.0 JSONB fields
    notification_preferences: Mapped[dict] = mapped_column(JSONB, nullable=True)
    admin_config: Mapped[dict] = mapped_column(JSONB, nullable=True)
    
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rto_profile: Mapped["RtoProfile"] = relationship(back_populates="users")
    agent_profile: Mapped["AgentProfile"] = relationship(back_populates="user_account", uselist=False)
    staff_profile: Mapped["StaffProfile"] = relationship(back_populates="user_account", uselist=False)
    student_profile: Mapped["StudentProfile"] = relationship(back_populates="user_account", uselist=False)
```

**Before (v2.0 APPLICATION model):**
```python
class Application(Base):
    __tablename__ = "application"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_profile.id"))
    current_stage: Mapped[str] = mapped_column(String)
    
    # v2.0 JSONB fields
    language_cultural_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    survey_responses: Mapped[list] = mapped_column(JSONB, nullable=True)
    form_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship(back_populates="application")
    enrollment: Mapped["CourseEnrollment"] = relationship(back_populates="application")
    # ... more relationships
```

**After (v3.0 APPLICATION model - FAT MODEL):**
```python
class Application(Base):
    __tablename__ = "application"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("student_profile.id"))
    current_stage: Mapped[str] = mapped_column(String)
    
    # v3.0 - 10 JSONB fields
    enrollment_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    emergency_contacts: Mapped[list] = mapped_column(JSONB, nullable=True)
    health_cover_policy: Mapped[dict] = mapped_column(JSONB, nullable=True)
    disability_support: Mapped[dict] = mapped_column(JSONB, nullable=True)
    language_cultural_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    survey_responses: Mapped[list] = mapped_column(JSONB, nullable=True)
    additional_services: Mapped[list] = mapped_column(JSONB, nullable=True)
    gs_assessment: Mapped[dict] = mapped_column(JSONB, nullable=True)
    signature_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    form_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    
    # Relationships - only history tables remain normalized
    schooling_history: Mapped[List["SchoolingHistory"]] = relationship(back_populates="application")
    qualification_history: Mapped[List["QualificationHistory"]] = relationship(back_populates="application")
    employment_history: Mapped[List["EmploymentHistory"]] = relationship(back_populates="application")
    documents: Mapped[List["Document"]] = relationship(back_populates="application")
    timeline_entries: Mapped[List["TimelineEntry"]] = relationship(back_populates="application")
```

---

## Pydantic Schema Changes

**Example: Emergency Contacts**

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Nested schema for JSONB structure
class EmergencyContactSchema(BaseModel):
    name: str
    relationship: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    is_primary: bool = False

# Application schema with JSONB fields
class ApplicationCreate(BaseModel):
    student_profile_id: uuid.UUID
    course_offering_id: uuid.UUID
    
    # JSONB fields with nested schemas
    emergency_contacts: Optional[List[EmergencyContactSchema]] = None
    health_cover_policy: Optional[dict] = None
    disability_support: Optional[dict] = None
    language_cultural_data: Optional[dict] = None
    survey_responses: Optional[List[dict]] = None
    additional_services: Optional[List[dict]] = None
    # ... other JSONB fields

class ApplicationResponse(ApplicationCreate):
    id: uuid.UUID
    current_stage: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

---

## Query Pattern Changes

### Before (v2.0): Join-based queries

```python
# Find applications with emergency contacts in Sydney
db.query(Application).join(EmergencyContact).filter(
    EmergencyContact.address.like('%Sydney%')
).all()
```

### After (v3.0): JSONB queries

```python
# Same query with JSONB containment
db.query(Application).filter(
    Application.emergency_contacts.op('@>')(
        '[{"address": "Sydney"}]'
    )
).all()

# Or using JSONB path operator
db.query(Application).filter(
    func.jsonb_path_exists(
        Application.emergency_contacts,
        '$[*] ? (@.address like_regex "Sydney")'
    )
).all()
```

### JSONB Index Creation

```sql
-- GIN indexes for all JSONB fields
CREATE INDEX idx_application_enrollment ON application USING GIN (enrollment_data);
CREATE INDEX idx_application_emergency ON application USING GIN (emergency_contacts);
CREATE INDEX idx_application_health_cover ON application USING GIN (health_cover_policy);
CREATE INDEX idx_application_disability ON application USING GIN (disability_support);
CREATE INDEX idx_application_language ON application USING GIN (language_cultural_data);
CREATE INDEX idx_application_survey ON application USING GIN (survey_responses);
CREATE INDEX idx_application_services ON application USING GIN (additional_services);
CREATE INDEX idx_application_gs_assessment ON application USING GIN (gs_assessment);
CREATE INDEX idx_application_signatures ON application USING GIN (signature_data);
CREATE INDEX idx_application_metadata ON application USING GIN (form_metadata);

CREATE INDEX idx_user_notification_prefs ON user_account USING GIN (notification_preferences);
CREATE INDEX idx_user_admin_config ON user_account USING GIN (admin_config);

CREATE INDEX idx_document_gs_requests ON document USING GIN (gs_document_requests);

CREATE INDEX idx_timeline_event_payload ON timeline_entry USING GIN (event_payload);
CREATE INDEX idx_timeline_correlation ON timeline_entry(correlation_id) WHERE correlation_id IS NOT NULL;
```

---

## Migration Triggers: When to Promote JSONB Back to Tables

### 1. **Complex JOIN Requirements**
- **Trigger**: Need to join emergency contacts with other entities frequently
- **Example**: "Find all agents whose emergency contacts share duplicate phone numbers" (fraud detection)
- **Action**: Promote `application.emergency_contacts` → `emergency_contact` table

### 2. **High-Volume Filtering/Sorting**
- **Trigger**: Filtering on specific JSONB fields becomes hot query path (e.g., health cover expiry sorting across 10,000+ apps)
- **Example**: Daily compliance report of expiring health cover policies
- **Action**: Promote `application.health_cover_policy` → `health_cover_policy` table with B-tree indexes

### 3. **Referential Integrity Enforcement**
- **Trigger**: Additional services catalog grows to 100+ items, consistency validation needed
- **Example**: Service pricing changes require cascading updates
- **Action**: Promote `application.additional_services` → `additional_service` + `application_additional_service` junction tables

### 4. **Third-Party Tool Integration**
- **Trigger**: BI tools (Power BI, Tableau) struggle with JSONB queries
- **Example**: Executive dashboard requires complex cross-table analytics
- **Action**: Create materialized views or promote to normalized tables

### 5. **Scale Thresholds**
- **< 5,000 applications**: JSONB with GIN indexes handles easily
- **5,000-20,000 applications**: Monitor query performance, selective normalization
- **20,000+ applications**: Likely need to normalize high-frequency JSONB queries

---

## Rollback Plan (v3.0 → v2.0)

If JSONB-first approach proves insufficient, easy rollback:

```sql
-- Example: Restore EMERGENCY_CONTACT table from JSONB
CREATE TABLE emergency_contact AS
SELECT
  gen_random_uuid() AS id,
  a.id AS application_id,
  (contact->>'name')::varchar AS name,
  (contact->>'relationship')::varchar AS relationship,
  (contact->>'phone')::varchar AS phone,
  (contact->>'email')::varchar AS email,
  (contact->>'address')::text AS address,
  (contact->>'is_primary')::boolean AS is_primary,
  a.created_at AS created_at
FROM application a,
LATERAL jsonb_array_elements(a.emergency_contacts) AS contact;

-- Add constraints
ALTER TABLE emergency_contact ADD CONSTRAINT fk_application 
  FOREIGN KEY (application_id) REFERENCES application(application_id);
  
CREATE INDEX idx_emergency_contact_application ON emergency_contact(application_id);
```

---

## Performance Benchmarks (Target)

| Operation | v2.0 (Normalized) | v3.0 (JSONB) | Acceptable? |
|-----------|------------------|--------------|-------------|
| Load application detail | 5-8 JOINs, 50ms | 1 query, 10ms | ✅ Faster |
| Filter by health cover expiry | B-tree index, 20ms | GIN index, 40ms | ✅ Acceptable |
| Insert new application | 8 tables, 150ms | 1 table, 40ms | ✅ Much faster |
| Emergency contact fraud detection | EXISTS subquery, 30ms | JSONB containment, 80ms | ⚠️ Monitor |
| GS assessment reporting | JOIN + GROUP BY, 100ms | JSONB aggregation, 200ms | ⚠️ Promote if critical |

**Recommendation:** Monitor query performance for 3-6 months. Normalize only when data (not assumptions) proves it's needed.

---

## Testing Checklist

- [ ] **Migration SQL scripts tested** on staging database with production data sample
- [ ] **JSONB indexes created** on all new JSONB columns before migration
- [ ] **Pydantic schemas updated** with nested models for JSONB structures
- [ ] **SQLAlchemy models updated** and Alembic migration generated
- [ ] **Unit tests updated** for new JSONB query patterns
- [ ] **Integration tests** for application creation/update flows
- [ ] **Performance tests** comparing query times against v2.0 benchmarks
- [ ] **Rollback script tested** to restore normalized tables from JSONB
- [ ] **Documentation updated** for all JSONB field structures and query examples
- [ ] **Monitoring alerts configured** for slow JSONB queries (> 200ms)

---

## Conclusion

v3.1 lean JSONB-first architecture with RTO management reduces schema complexity by **53%** (34 → 16 tables) to enable rapid MVP iteration while supporting proper multi-tenancy. PostgreSQL JSONB with GIN indexes provides sufficient query performance for 5,000-20,000 applications. Clear migration triggers ensure easy promotion to normalized tables when actual usage patterns demand it.

**Key Additions in v3.1:**
- RTO_PROFILE table enables organization metadata management
- Supports white-label branding and per-RTO business settings
- Future-proofs for multi-RTO SaaS expansion
- Maintains lean philosophy with JSONB for flexible configuration

**Next Steps:**
1. Generate Alembic migration script for v3.1 schema changes (RTO_PROFILE + all JSONB consolidations)
2. Create initial RTO_PROFILE record for Churchill Education
3. Update FastAPI routes and Pydantic schemas (add RTO models)
4. Test migration on staging environment
5. Deploy to production with monitoring for JSONB query performance
6. Document JSONB field structures and RTO_PROFILE JSONB schemas in API documentation
