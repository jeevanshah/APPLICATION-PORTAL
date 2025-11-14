# Database Schema Migration: v1.1 → v2.0 (Hybrid Architecture)

**Date:** November 14, 2025  
**Impact:** BREAKING CHANGE - Table consolidation  
**Migration Complexity:** Medium  

## Summary

Refactored from **34 tables to 28 tables** (-18% complexity) by adopting a hybrid normalized + JSONB approach. Frequently-queried intake data remains in dedicated tables, while 1:1 simple data and dynamic forms are consolidated into the `APPLICATION` table as JSONB columns.

---

## Tables Removed (Consolidated)

### 1. `LANGUAGE_CULTURAL_PROFILE` → `application.language_cultural_data` (JSONB)

**Before (separate table):**
```sql
CREATE TABLE language_cultural_profile (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    first_language VARCHAR,
    other_languages VARCHAR[],
    indigenous_status VARCHAR,
    country_of_birth VARCHAR,
    citizenship_status VARCHAR
);
```

**After (JSONB column):**
```sql
ALTER TABLE application ADD COLUMN language_cultural_data JSONB;

-- Example data:
{
  "first_language": "Mandarin",
  "other_languages": ["English", "Cantonese"],
  "indigenous_status": null,
  "country_of_birth": "China",
  "citizenship_status": "International Student"
}
```

**Rationale:** Language/cultural data is rarely queried individually. When needed, PostgreSQL GIN indexes on JSONB provide sufficient performance.

---

### 2. `USI_RECORD` → `application.usi` + `application.usi_verified` + `application.usi_verified_at`

**Before (separate table):**
```sql
CREATE TABLE usi_record (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    usi VARCHAR,
    verification_status VARCHAR,
    consent_flag BOOLEAN,
    verified_at TIMESTAMP
);
```

**After (direct columns):**
```sql
ALTER TABLE application 
ADD COLUMN usi VARCHAR,
ADD COLUMN usi_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN usi_verified_at TIMESTAMP;
```

**Rationale:** USI is a simple 1:1 relationship with exactly 3 fields. No benefit to separate table overhead.

---

### 3. `SURVEY_QUESTION` + `SURVEY_RESPONSE` → `application.survey_responses` (JSONB array)

**Before (two tables):**
```sql
CREATE TABLE survey_question (
    id UUID PRIMARY KEY,
    question_text TEXT,
    question_type VARCHAR,
    options JSONB,
    display_order INT
);

CREATE TABLE survey_response (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application(id),
    question_id UUID REFERENCES survey_question(id),
    answer TEXT,
    submitted_at TIMESTAMP
);
```

**After (JSONB array):**
```sql
ALTER TABLE application ADD COLUMN survey_responses JSONB;

-- Example data:
[
  {
    "question_id": "uuid-1",
    "question_text": "How did you hear about us?",
    "answer": "Agent referral",
    "submitted_at": "2025-11-14T10:30:00Z"
  },
  {
    "question_id": "uuid-2",
    "question_text": "Preferred study mode",
    "answer": "On-campus",
    "submitted_at": "2025-11-14T10:30:00Z"
  }
]
```

**Rationale:** Survey questions change frequently and vary by intake. JSONB allows dynamic schema without migrations. Questions are embedded with responses for self-documenting data.

---

## Tables Retained (Normalized)

These tables remain **normalized** because they are frequently queried for filtering and reporting:

✅ **EMERGENCY_CONTACT** - Staff filters: "applications missing emergency contacts"  
✅ **HEALTH_COVER_POLICY** - Compliance queries: coverage expiry dates  
✅ **DISABILITY_SUPPORT** - Reporting: support resource allocation  
✅ **SCHOOLING_HISTORY** - Filters: by institution, country, qualification level  
✅ **QUALIFICATION_HISTORY** - Analytics: qualification type distribution  
✅ **EMPLOYMENT_HISTORY** - Reporting: industry sectors, employment gaps  

---

## Migration Script (PostgreSQL)

```sql
-- Step 1: Add new JSONB columns to application table
ALTER TABLE application 
ADD COLUMN usi VARCHAR,
ADD COLUMN usi_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN usi_verified_at TIMESTAMP,
ADD COLUMN language_cultural_data JSONB,
ADD COLUMN survey_responses JSONB,
ADD COLUMN form_metadata JSONB;

-- Step 2: Migrate USI data
UPDATE application a
SET 
    usi = u.usi,
    usi_verified = (u.verification_status = 'verified'),
    usi_verified_at = u.verified_at
FROM usi_record u
WHERE a.id = u.application_id;

-- Step 3: Migrate language/cultural data
UPDATE application a
SET language_cultural_data = jsonb_build_object(
    'first_language', l.first_language,
    'other_languages', l.other_languages,
    'indigenous_status', l.indigenous_status,
    'country_of_birth', l.country_of_birth,
    'citizenship_status', l.citizenship_status
)
FROM language_cultural_profile l
WHERE a.id = l.application_id;

-- Step 4: Migrate survey responses (aggregate into array)
UPDATE application a
SET survey_responses = (
    SELECT jsonb_agg(
        jsonb_build_object(
            'question_id', sr.question_id,
            'question_text', sq.question_text,
            'answer', sr.answer,
            'submitted_at', sr.submitted_at
        )
    )
    FROM survey_response sr
    JOIN survey_question sq ON sr.question_id = sq.id
    WHERE sr.application_id = a.id
);

-- Step 5: Create GIN indexes for JSONB queries
CREATE INDEX idx_application_language_data 
ON application USING GIN (language_cultural_data);

CREATE INDEX idx_application_survey_responses 
ON application USING GIN (survey_responses);

CREATE INDEX idx_application_usi ON application(usi);

-- Step 6: Drop old tables (after verification)
-- DROP TABLE usi_record;
-- DROP TABLE language_cultural_profile;
-- DROP TABLE survey_response;
-- DROP TABLE survey_question;
```

---

## Code Changes Required

### 1. SQLAlchemy Models (FastAPI Backend)

**Before:**
```python
class LanguageCulturalProfile(Base):
    __tablename__ = "language_cultural_profile"
    id = Column(UUID, primary_key=True)
    application_id = Column(UUID, ForeignKey("application.id"))
    first_language = Column(String)
    # ... other fields

class USIRecord(Base):
    __tablename__ = "usi_record"
    id = Column(UUID, primary_key=True)
    application_id = Column(UUID, ForeignKey("application.id"))
    usi = Column(String)
    verification_status = Column(String)
```

**After:**
```python
from sqlalchemy.dialects.postgresql import JSONB

class Application(Base):
    __tablename__ = "application"
    id = Column(UUID, primary_key=True)
    # ... existing fields
    
    # New JSONB fields
    usi = Column(String, nullable=True)
    usi_verified = Column(Boolean, default=False)
    usi_verified_at = Column(DateTime, nullable=True)
    language_cultural_data = Column(JSONB, nullable=True)
    survey_responses = Column(JSONB, nullable=True)
    form_metadata = Column(JSONB, nullable=True)
```

---

### 2. Pydantic Schemas (FastAPI)

**Before:**
```python
class LanguageCulturalProfileCreate(BaseModel):
    application_id: UUID
    first_language: str
    other_languages: List[str]
    indigenous_status: Optional[str]
    country_of_birth: str
    citizenship_status: str
```

**After:**
```python
class LanguageCulturalData(BaseModel):
    first_language: str
    other_languages: List[str] = []
    indigenous_status: Optional[str] = None
    country_of_birth: str
    citizenship_status: str

class SurveyResponseItem(BaseModel):
    question_id: str
    question_text: str
    answer: str
    submitted_at: datetime

class ApplicationCreate(BaseModel):
    # ... existing fields
    usi: Optional[str] = None
    language_cultural_data: Optional[LanguageCulturalData] = None
    survey_responses: Optional[List[SurveyResponseItem]] = None
```

---

### 3. Query Examples

**Language filtering (if needed):**
```python
# Before (JOIN)
applications = db.query(Application).join(LanguageCulturalProfile).filter(
    LanguageCulturalProfile.first_language == "Mandarin"
).all()

# After (JSONB query)
applications = db.query(Application).filter(
    Application.language_cultural_data['first_language'].astext == "Mandarin"
).all()
```

**USI lookup:**
```python
# Before (JOIN)
application = db.query(Application).join(USIRecord).filter(
    USIRecord.usi == "ABC123XYZ"
).first()

# After (direct column)
application = db.query(Application).filter(
    Application.usi == "ABC123XYZ"
).first()
```

---

## Rollback Plan

If migration causes issues, rollback is straightforward:

```sql
-- Restore separate tables
CREATE TABLE usi_record AS
SELECT 
    gen_random_uuid() as id,
    id as application_id,
    usi,
    CASE WHEN usi_verified THEN 'verified' ELSE 'pending' END as verification_status,
    usi_verified as consent_flag,
    usi_verified_at as verified_at
FROM application
WHERE usi IS NOT NULL;

-- Similar for language_cultural_profile and survey tables
-- Then DROP COLUMN from application table
```

---

## Benefits Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Total tables | 34 | 28 | -18% |
| JOINs for full application | 12 | 8 | -33% |
| Migration complexity | N/A | Medium | One-time cost |
| Query flexibility | Rigid | High | Dynamic schema |
| Storage fragmentation | Higher | Lower | Fewer small tables |

---

## Testing Checklist

- [ ] Verify all USI data migrated correctly
- [ ] Verify language/cultural data JSON structure
- [ ] Verify survey responses with multiple answers
- [ ] Test JSONB queries with GIN indexes
- [ ] Benchmark query performance vs old schema
- [ ] Update API integration tests
- [ ] Update frontend TypeScript types
- [ ] Run full regression test suite

---

## References

- Main schema diagram: `docs/data-model-diagram.md` (v2.0)
- Architecture doc: `docs/solution-architecture.md` (section 5, v2.0)
- PostgreSQL JSONB docs: https://www.postgresql.org/docs/current/datatype-json.html
- SQLAlchemy JSONB support: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-json-types
