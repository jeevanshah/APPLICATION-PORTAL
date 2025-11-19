# Application Data Architecture

## Current Structure (As-Is)

### Application Table JSONB Columns

The `application` table has **10 JSONB columns** plus regular columns. Here's what each stores:

```
application
├── Regular Columns
│   ├── id (UUID)
│   ├── student_profile_id (UUID, nullable)
│   ├── agent_profile_id (UUID)
│   ├── course_offering_id (UUID)
│   ├── assigned_staff_id (UUID, nullable)
│   ├── current_stage (enum)
│   ├── usi (VARCHAR)
│   ├── usi_verified (BOOLEAN)
│   └── timestamps
│
└── JSONB Columns (10 total)
    ├── form_metadata          ← Form submission tracking + Step 1 data (INCONSISTENT)
    ├── emergency_contacts     ← Step 2 data
    ├── health_cover_policy    ← Step 3 data
    ├── language_cultural_data ← Step 4 data
    ├── disability_support     ← Step 5 data
    ├── survey_responses       ← Step 11 data
    ├── additional_services    ← Step 10 data
    ├── enrollment_data        ← Post-enrollment business data
    ├── gs_assessment          ← Staff assessment data
    └── signature_data         ← DocuSign/signature workflow data
```

---

## Current Inconsistency

### 🔴 Problem: Personal Details Storage

**Step 1 (Personal Details)** is stored DIFFERENTLY from all other steps:

```json
// Step 1 - NESTED in form_metadata
{
  "form_metadata": {
    "personal_details": {        // ← Step 1 data buried here
      "given_name": "John",
      "family_name": "Doe",
      ...
    },
    "version": "1.0",
    "completed_sections": [...],
    "last_saved_at": "..."
  }
}

// Steps 2-11 - TOP-LEVEL JSONB columns
{
  "emergency_contacts": [...],    // ← Step 2 data at top level
  "health_cover_policy": {...},   // ← Step 3 data at top level
  "language_cultural_data": {...} // ← Step 4 data at top level
}
```

---

## Design Intent (Original Plan)

Looking at the column names and structure, the **original design intent** seems to be:

### Purpose of Each Column:

| Column | Purpose | Step # | Notes |
|--------|---------|--------|-------|
| `form_metadata` | Form submission metadata | N/A | Version, IP, timestamps, progress tracking |
| `emergency_contacts` | Emergency contact data | 2 | Frequently queried for safety |
| `health_cover_policy` | OSHC insurance data | 3 | Business logic, expiry tracking |
| `language_cultural_data` | Language/visa data | 4 | Compliance reporting |
| `disability_support` | Disability support needs | 5 | Service planning |
| `survey_responses` | Pre-enrollment survey | 11 | Analytics, reporting |
| `additional_services` | Optional services | 10 | Billing, service provisioning |
| `enrollment_data` | Post-enrollment info | N/A | COE, fee receipts (after ENROLLED) |
| `gs_assessment` | Staff assessment | N/A | Internal workflow (staff only) |
| `signature_data` | DocuSign workflow | N/A | Legal compliance |

### What's Missing:
- ❌ **Step 1** (Personal Details) - No dedicated column
- ❌ **Step 6** (Schooling History) - No dedicated column
- ❌ **Step 7** (Qualifications) - No dedicated column
- ❌ **Step 8** (Employment History) - No dedicated column
- ❌ **Step 9** (USI) - Has `usi` VARCHAR column (not JSONB)

---

## Recommended Fix: Unified Approach

### ✅ **Recommendation: Store ALL form steps in `form_metadata`**

```json
{
  "form_metadata": {
    // === FORM DATA (Steps 1-12) ===
    "personal_details": {...},           // Step 1
    "emergency_contacts": [...],         // Step 2
    "health_cover": {...},               // Step 3
    "language_cultural": {...},          // Step 4
    "disability_support": {...},         // Step 5
    "schooling_history": [...],          // Step 6
    "qualifications": [...],             // Step 7
    "employment_history": [...],         // Step 8
    "usi": {...},                        // Step 9
    "additional_services": [...],        // Step 10
    "survey": {...},                     // Step 11
    "documents": {...},                  // Step 12 (status)
    
    // === FORM METADATA (Tracking) ===
    "version": "1.0",
    "completed_sections": ["personal_details", "emergency_contacts"],
    "last_saved_at": "2025-11-19T01:47:07",
    "last_edited_section": "personal_details",
    "auto_save_count": 5,
    "ip_address": "203.0.113.1",
    "user_agent": "Mozilla/5.0...",
    "submission_duration_seconds": 1234
  }
}
```

### ✅ **Keep Separate Columns for Business Logic**

```json
// These columns serve BUSINESS purposes (not just form storage)
{
  "emergency_contacts": [...],     // ← Duplicate for quick emergency lookup
  "health_cover_policy": {...},    // ← Duplicate for expiry alerts
  "enrollment_data": {...},        // ← NOT part of 12-step form
  "gs_assessment": {...},          // ← NOT part of 12-step form
  "signature_data": {...}          // ← NOT part of 12-step form
}
```

---

## Why This Approach?

### ✅ Benefits:
1. **Consistency**: All 12 form steps in ONE place (`form_metadata`)
2. **Simplicity**: Frontend fetches ONE field to get all form data
3. **Flexibility**: Easy to add/remove form fields without migrations
4. **Auditability**: Complete form snapshot in one JSONB object
5. **Performance**: Can still index frequently-queried fields separately

### 🔄 Data Flow:
```
Agent fills form → All 12 steps stored in form_metadata
                ↓
Application submitted → Copy critical fields to dedicated columns
                      (emergency_contacts, health_cover for business use)
                ↓
Application processed → Add enrollment_data, gs_assessment
                ↓
Student enrolled → Create student_profile from form_metadata
```

---

## Implementation Recommendation

### Phase 1: Consolidate Form Data (Do Now)
Move ALL 12 steps into `form_metadata`:
- ✅ Personal details (already there)
- ✅ Emergency contacts (move from `emergency_contacts` column)
- ✅ Health cover (move from `health_cover_policy` column)
- ✅ Language/cultural (move from `language_cultural_data` column)
- ✅ Disability (move from `disability_support` column)
- ✅ Survey (move from `survey_responses` column)
- ✅ Additional services (move from `additional_services` column)
- ✅ Add schooling, qualifications, employment to `form_metadata`

### Phase 2: Keep Business Columns (Optional)
If you need fast queries on specific data:
```sql
-- Example: Find applications with expired health cover
SELECT * FROM application 
WHERE health_cover_policy->>'end_date' < CURRENT_DATE;

-- Example: Find students needing disability support
SELECT * FROM application 
WHERE disability_support->>'has_disability' = 'true';
```

You can keep duplicating critical data to dedicated columns via triggers or application logic.

---

## Current vs Recommended Structure

### Current (Inconsistent):
```
Step 1  → form_metadata.personal_details  ❌ NESTED
Step 2  → emergency_contacts              ✓ TOP-LEVEL
Step 3  → health_cover_policy             ✓ TOP-LEVEL
Step 4  → language_cultural_data          ✓ TOP-LEVEL
Step 5  → disability_support              ✓ TOP-LEVEL
Step 6  → ??? WHERE STORED?               ❌ UNCLEAR
Step 7  → ??? WHERE STORED?               ❌ UNCLEAR
Step 8  → ??? WHERE STORED?               ❌ UNCLEAR
Step 9  → usi (VARCHAR column)            ⚠️ DIFFERENT TYPE
Step 10 → additional_services             ✓ TOP-LEVEL
Step 11 → survey_responses                ✓ TOP-LEVEL
Step 12 → (Documents separate table)     ✓ SEPARATE
```

### Recommended (Consistent):
```
Steps 1-12  → form_metadata.{step_name}  ✓ ALL IN ONE PLACE

Optional duplicates for business queries:
- emergency_contacts   (copy from form_metadata)
- health_cover_policy  (copy from form_metadata)
```

---

## Decision Matrix

| Approach | Consistency | Query Performance | Complexity | Recommended? |
|----------|-------------|-------------------|------------|--------------|
| **Current** (mixed) | ❌ Low | ⚠️ Medium | ⚠️ Medium | ❌ No |
| **All in form_metadata** | ✅ High | ✅ Good* | ✅ Low | ✅ **YES** |
| **Separate column per step** | ✅ High | ✅ Excellent | ❌ High | ⚠️ Only if heavy querying |

*With GIN indexes on JSONB, query performance is excellent

---

## Next Steps

Since you're in development and not worried about data:

1. ✅ **Refactor service methods** to store ALL steps in `form_metadata`
2. ✅ **Update frontend guide** to show consistent data access
3. ⚠️ **Optionally keep duplicate columns** if you need fast business queries
4. ✅ **Add GIN indexes** on `form_metadata` for fast JSONB queries

Would you like me to implement the refactoring to consolidate everything into `form_metadata`?
