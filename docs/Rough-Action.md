# Churchill Application Portal - Complete Workflow

**Key Principle:** Agents drive the entire application process. Students only interact to sign the final offer.

---

## Application Workflow Phases

| Phase | Actor   | Action                                      | Status          | Notes |
|------:|---------|---------------------------------------------|-----------------|-------|
| 1     | Agent   | Create student profile                      | ✅ BUILT        | Agent creates user credentials for student |
| 2     | Agent   | Create application draft                    | ✅ BUILT        | Links student + course + agent |
| 3     | Agent   | Fill entire application form                | ✅ BUILT        | Agent fills ALL fields (personal, education, employment, etc.) |
| 4     | Agent   | Upload all required documents               | ❌ NOT BUILT    | Passport, transcripts, certificates, etc. |
| 5     | Agent   | Submit application for review               | ✅ BUILT        | Agent confirms accuracy and submits |
| 6     | Student | View dashboard (read-only)                  | ✅ BUILT        | Student logs in to see application status |
| 7     | Student | Track progress (read-only)                  | ✅ BUILT        | Student sees timeline, stages, documents |
| 8     | Staff   | Review application & request documents      | ❌ NOT BUILT    | Staff can request missing/additional docs |
| 9     | Staff   | Verify uploaded documents                   | ❌ NOT BUILT    | Staff marks documents as verified/rejected |
| 10    | Staff   | Assign application to themselves            | ❌ NOT BUILT    | Staff takes ownership of application |
| 11    | Staff   | Conduct Genuine Student (GS) assessment     | ❌ NOT BUILT    | Interview + scoring |
| 12    | Staff   | Generate offer letter                       | ❌ NOT BUILT    | DocuSeal integration for eCOE/offer |
| 13    | Student | **Sign offer** (FIRST active participation!)| ❌ NOT BUILT    | Student reviews and digitally signs |
| 14    | Staff   | Enroll student                              | ❌ NOT BUILT    | Final stage - student enrolled |

---

## Detailed Phase Breakdown

### **Phase 1-3: Agent Creates & Fills Application** ✅

**What happens:**
1. Agent creates student profile (name, DOB, passport, email, password)
2. Agent creates application draft (selects course + intake)
3. Agent fills entire form over multiple sessions:
   - Personal details
   - Education history (high school, university)
   - Qualifications (degrees, certificates)
   - Employment history
   - Emergency contacts
   - Health cover policy details
   - Disability support requirements
   - Language & cultural background
   - Additional services needed
   - Survey responses

**Permissions:**
- ✅ Agent can create/edit applications they create
- ✅ Staff can create/edit any application in their RTO
- ❌ Students **CANNOT** edit applications (read-only access only)

**Endpoints:**
```
POST   /api/v1/students              # Agent creates student
POST   /api/v1/applications          # Agent creates draft
PATCH  /api/v1/applications/{id}     # Agent auto-saves (students forbidden)
```

---

### **Phase 4: Agent Uploads Documents** ❌ NOT BUILT

**What happens:**
- Agent uploads all required documents:
  - Passport scan
  - Academic transcripts
  - Employment letters
  - Health insurance policy
  - English test results (IELTS/TOEFL)
  - Any other supporting documents

**Permissions:**
- ✅ Agents can upload documents for applications they created
- ✅ Staff can upload documents for any application
- ❌ Students **CANNOT** upload documents

**Endpoints needed:**
```
POST   /api/v1/applications/{id}/documents/upload
GET    /api/v1/applications/{id}/documents
GET    /api/v1/documents/{doc_id}
```

---

### **Phase 5: Agent Submits Application** ✅

**What happens:**
1. Agent reviews all data for accuracy
2. Agent confirms all information is correct
3. Agent clicks "Submit Application"
4. Application transitions: DRAFT → SUBMITTED
5. Timeline entry created: "Application submitted by [Agent Name]"
6. Notification sent to staff (coming in Phase 2)

**Permissions:**
- ✅ Agents can submit applications they created
- ✅ Staff can submit any application
- ❌ Students **CANNOT** submit applications

**Endpoints:**
```
POST   /api/v1/applications/{id}/submit
```

---

### **Phase 6-7: Student Views Progress** ✅

**What happens:**
1. Student logs in with credentials provided by agent
2. Student sees dashboard with all applications
3. Student clicks application to see detailed tracking
4. Student sees:
   - Current stage (e.g., "Submitted", "Staff Review", "Awaiting Documents")
   - Progress bar (8 workflow stages)
   - Required documents status
   - Timeline of all activity
   - Assigned staff member contact info
   - Next steps (context-aware)

**Permissions:**
- ✅ Students can view their own applications (read-only)
- ✅ Students can view their own documents (read-only)
- ❌ Students **CANNOT** edit applications
- ❌ Students **CANNOT** upload documents
- ❌ Students **CANNOT** submit applications

**Endpoints:**
```
GET    /api/v1/students/me/dashboard
GET    /api/v1/students/me/applications/{id}/track
```

---

### **Phase 8-11: Staff Processing** ❌ NOT BUILT

**What happens:**
1. Staff reviews application
2. Staff may request additional documents
3. Agent uploads requested documents
4. Staff verifies all documents
5. Staff conducts GS assessment interview
6. Staff generates offer letter

**Permissions:**
- ✅ Staff can review any application in their RTO
- ✅ Staff can request documents
- ✅ Staff can verify/reject documents
- ✅ Staff can conduct GS assessment
- ✅ Staff can generate offers

**Endpoints needed:**
```
GET    /api/v1/staff/me/assigned-applications
POST   /api/v1/applications/{id}/assign
POST   /api/v1/applications/{id}/request-document
PATCH  /api/v1/documents/{doc_id}/verify
POST   /api/v1/applications/{id}/gs-assessment
POST   /api/v1/applications/{id}/generate-offer
```

---

### **Phase 13: Student Signs Offer** ❌ NOT BUILT

**What happens:**
1. Staff generates offer letter (via DocuSeal)
2. Student gets notification: "Your offer is ready for signature"
3. Student logs in and reviews offer
4. Student digitally signs offer (DocuSeal integration)
5. Application transitions: OFFER_GENERATED → OFFER_ACCEPTED
6. Timeline entry: "Offer accepted by [Student Name]"

**THIS IS THE FIRST (AND ONLY) ACTIVE PARTICIPATION FROM STUDENT!**

**Permissions:**
- ✅ Students can sign their own offers
- ❌ Agents/Staff cannot sign on behalf of student

**Endpoints needed:**
```
GET    /api/v1/applications/{id}/offer
POST   /api/v1/applications/{id}/sign-offer
```

---

### **Phase 14: Enrollment** ❌ NOT BUILT

**What happens:**
1. Staff finalizes enrollment
2. Student added to learning management system
3. eCOE issued
4. Application transitions: OFFER_ACCEPTED → ENROLLED

**Endpoints needed:**
```
POST   /api/v1/applications/{id}/enroll
GET    /api/v1/applications/{id}/coe
```

---

## Permission Matrix

| Action | Agent | Staff | Student |
|--------|-------|-------|---------|
| Create student profile | ✅ | ✅ | ❌ |
| Create application | ✅ | ✅ | ❌ |
| Edit application | ✅ Own only | ✅ All in RTO | ❌ FORBIDDEN |
| Upload documents | ✅ Own only | ✅ All | ❌ FORBIDDEN |
| Submit application | ✅ Own only | ✅ All | ❌ FORBIDDEN |
| View dashboard | ✅ | ✅ | ✅ Read-only |
| Track progress | ✅ | ✅ | ✅ Read-only |
| Request documents | ❌ | ✅ | ❌ |
| Verify documents | ❌ | ✅ | ❌ |
| Conduct GS assessment | ❌ | ✅ | ❌ |
| Generate offer | ❌ | ✅ | ❌ |
| **Sign offer** | ❌ | ❌ | ✅ **ONLY ACTION!** |
| Enroll student | ❌ | ✅ | ❌ |

---

## Data Flow Summary

```
┌─────────────┐
│   AGENT     │
└──────┬──────┘
       │
       ├─→ Creates StudentProfile (with login credentials)
       │
       ├─→ Creates Application (DRAFT stage)
       │
       ├─→ Fills entire form (personal, education, employment, etc.)
       │   └─→ Auto-saves to Application JSONB fields
       │
       ├─→ Uploads documents (passport, transcripts, etc.)
       │   └─→ Creates Document + DocumentVersion records
       │
       └─→ Submits application
           └─→ Application.current_stage = SUBMITTED
           └─→ Creates ApplicationStageHistory record
           └─→ Creates TimelineEntry record
           └─→ Notifies staff

┌─────────────┐
│  STUDENT    │ (Passive until offer signing)
└──────┬──────┘
       │
       ├─→ Logs in (credentials from agent)
       │
       ├─→ Views dashboard (read-only)
       │   └─→ Sees application status, progress, timeline
       │
       ├─→ Tracks application (read-only)
       │   └─→ Sees stages, documents, next steps
       │
       └─→ WAITS for offer to sign (only active participation)

┌─────────────┐
│   STAFF     │
└──────┬──────┘
       │
       ├─→ Reviews application
       │
       ├─→ Requests additional documents (if needed)
       │   └─→ Agent uploads requested docs
       │
       ├─→ Verifies documents
       │   └─→ Document.status = VERIFIED or REJECTED
       │
       ├─→ Conducts GS assessment
       │   └─→ Application.gs_assessment JSONB populated
       │
       ├─→ Generates offer
       │   └─→ Application.current_stage = OFFER_GENERATED
       │
       └─→ Enrolls student (after offer signed)
           └─→ Application.current_stage = ENROLLED
```

---

## Next Development Priority

**Phase 2: Document Management** (Unblocks workflow)

1. **Document upload endpoints** (agents upload for students)
2. **Document verification endpoints** (staff verifies)
3. **Document request endpoints** (staff requests missing docs)

This is critical because without documents, the workflow is blocked at "AWAITING_DOCUMENTS" stage.

**Should we build this next?** ✅