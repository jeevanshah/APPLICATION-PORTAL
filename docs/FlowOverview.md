# Application Portal API Specification

## Overview
This document defines the complete API structure for the Churchill Institute Application Portal, featuring a 12-step application process with OCR-powered auto-population and real-time validation.

---

## Table of Contents
1. [Application Process Flow](#application-process-flow)
2. [Authentication & Authorization](#authentication--authorization)
3. [Application Lifecycle Endpoints](#application-lifecycle-endpoints)
4. [Step-by-Step Endpoints](#step-by-step-endpoints)
5. [Document Management](#document-management)
6. [Validation & Flags](#validation--flags)
7. [Staff Review Workflow](#staff-review-workflow)
8. [Real-time Updates](#real-time-updates)
9. [Response Formats](#response-formats)
10. [Error Handling](#error-handling)

---

## Application Process Flow

### Stage Overview
```
STAGE 1: Create Application (Agent selects student + course)
   ↓
STAGE 2-12: Multi-Step Form (12 steps with Save & Continue)
   ├── Step 1: Personal Details
   ├── Step 2: Emergency Contact
   ├── Step 3: Overseas Student Health Cover
   ├── Step 4: Language and Cultural Diversity
   ├── Step 5: Disability
   ├── Step 6: Schooling
   ├── Step 7: Previous Qualifications Achieved
   ├── Step 8: Employment
   ├── Step 9: USI
   ├── Step 10: Additional Services
   ├── Step 11: Survey Status
   └── Step 12: Document
   ↓
STAGE 13: Review & Submit
   ↓
STAGE 14: Staff Review & Document Verification
   ↓
STAGE 15: GS Assessment
   ↓
STAGE 16: Offer Generation
   ↓
STAGE 17: Enrollment
```

### Progress Calculation
```
Progress % = (Completed Steps / 12) × 100
```

---

## Authentication & Authorization

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
  "email": "agent@example.com",
  "password": "Password123!"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "user-uuid-123",
    "email": "agent@example.com",
    "role": "AGENT",
    "profile": {
      "given_name": "Test",
      "family_name": "Agent",
      "company_name": "Nepal Education Consultancy"
    }
  }
}
```

### Refresh Token
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}

Response (200 OK):
{
  "access_token": "new_token_here...",
  "expires_in": 3600
}
```

### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}

Response (200 OK):
{
  "id": "user-uuid-123",
  "email": "agent@example.com",
  "role": "AGENT",
  "profile": {...},
  "permissions": [
    "create_student",
    "create_application",
    "upload_documents"
  ]
}
```

---

## Application Lifecycle Endpoints

### Create Application
```http
POST /api/v1/applications
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "student_profile_id": "student-uuid-789",
  "course_offering_id": "course-uuid-1"
}

Response (201 Created):
{
  "id": "app-uuid-456",
  "student_profile_id": "student-uuid-789",
  "course_offering_id": "course-uuid-1",
  "current_step": "personal_details",
  "status": "draft",
  "created_at": "2025-11-17T10:00:00Z",
  "progress_percentage": 0,
  "next_step": {
    "step": "personal_details",
    "message": "Complete personal details to continue"
  }
}
```

### Get Application
```http
GET /api/v1/applications/{app_id}
Authorization: Bearer {access_token}

Response (200 OK):
{
  "id": "app-uuid-456",
  "student": {
    "id": "student-uuid-789",
    "given_name": "Ram",
    "family_name": "Sharma"
  },
  "course": {
    "id": "course-uuid-1",
    "course_name": "Bachelor of IT",
    "campus": "Melbourne"
  },
  "current_step": "employment",
  "completed_steps": ["personal_details", "emergency_contact", ...],
  "status": "draft",
  "progress_percentage": 66.66,
  "created_at": "2025-11-17T10:00:00Z",
  "updated_at": "2025-11-17T10:45:00Z"
}
```

### Get Application Progress
```http
GET /api/v1/applications/{app_id}/progress
Authorization: Bearer {access_token}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "total_steps": 12,
  "completed_steps": 8,
  "current_step": "employment",
  "progress_percentage": 66.66,
  "steps_status": {
    "personal_details": "completed",
    "emergency_contact": "completed",
    "health_cover": "completed",
    "language_cultural": "completed",
    "disability": "completed",
    "schooling": "completed",
    "previous_qualifications": "completed",
    "employment": "in_progress",
    "usi": "not_started",
    "additional_services": "not_started",
    "survey": "not_started",
    "document": "not_started"
  },
  "can_submit": false,
  "missing_steps": ["employment", "usi", "additional_services", "survey", "document"]
}
```

### List Applications
```http
GET /api/v1/applications
Authorization: Bearer {access_token}

Query Parameters:
  ?student_id=student-uuid-789    # Filter by student
  ?status=draft                   # Filter by status (draft, submitted, approved, rejected)
  ?page=1                         # Pagination
  &limit=20

Response (200 OK):
{
  "applications": [
    {
      "id": "app-uuid-456",
      "student": {
        "given_name": "Ram",
        "family_name": "Sharma"
      },
      "course": {
        "course_name": "Bachelor of IT"
      },
      "status": "draft",
      "progress_percentage": 66.66,
      "created_at": "2025-11-17T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

---

## Step-by-Step Endpoints

### Standard Request/Response Pattern

All step endpoints follow this pattern:

**Request:**
```http
PATCH /api/v1/applications/{app_id}/steps/{step_name}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  // Step-specific fields
}
```

**Response:**
```json
{
  "application_id": "app-uuid-456",
  "current_step": "step_name",
  "completed_steps": ["step1", "step2", "step_name"],
  "next_step": "next_step_name",
  "progress_percentage": 41.66,
  "can_proceed": true,
  "validation_errors": [],
  "flags": [],
  "message": "Step saved successfully"
}
```

---

### Step 1: Personal Details

```http
PATCH /api/v1/applications/{app_id}/steps/personal-details
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "given_name": "Ram",
  "family_name": "Sharma",
  "date_of_birth": "2000-05-15",
  "gender": "Male",
  "passport_number": "C1234567",
  "nationality": "Nepalese",
  "country_of_birth": "Nepal",
  "town_city_of_birth": "Kathmandu",
  "residential_address": {
    "street_address": "123 Main Street",
    "suburb": "Kathmandu",
    "state": "Bagmati",
    "postcode": "44600",
    "country": "Nepal"
  },
  "contact_details": {
    "email": "ram.sharma@example.com",
    "phone": "+977 1 4444444",
    "mobile": "+977 9841234567"
  }
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "personal_details",
  "completed_steps": ["personal_details"],
  "next_step": "emergency_contact",
  "progress_percentage": 8.33,
  "message": "Personal details saved successfully"
}
```

**Auto-Populate with Passport Upload:**
```http
POST /api/v1/applications/{app_id}/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Request:
{
  "document_type": "passport",
  "file": <passport.pdf>,
  "auto_populate": true
}

Response (201 Created):
{
  "document": {
    "id": "doc-passport-123",
    "status": "ready"
  },
  "ocr_result": {
    "status": "success",
    "processing_time_ms": 4200,
    "overall_confidence": 0.98,
    "extracted_fields": {
      "given_name": {"value": "Ram", "confidence": 0.99},
      "family_name": {"value": "Sharma", "confidence": 0.99},
      "date_of_birth": {"value": "2000-05-15", "confidence": 0.95},
      "passport_number": {"value": "C1234567", "confidence": 0.98},
      "nationality": {"value": "Nepalese", "confidence": 0.97},
      "gender": {"value": "Male", "confidence": 0.96}
    }
  },
  "auto_populate_result": {
    "status": "success",
    "populated_fields": [
      {"field": "given_name", "old_value": null, "new_value": "Ram"},
      {"field": "family_name", "old_value": null, "new_value": "Sharma"},
      {"field": "date_of_birth", "old_value": null, "new_value": "2000-05-15"},
      {"field": "passport_number", "old_value": null, "new_value": "C1234567"},
      {"field": "nationality", "old_value": null, "new_value": "Nepalese"},
      {"field": "gender", "old_value": null, "new_value": "Male"}
    ],
    "total_populated": 6
  }
}
```

---

### Step 2: Emergency Contact

```http
PATCH /api/v1/applications/{app_id}/steps/emergency-contact
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "emergency_contacts": [
    {
      "name": "Sumitra Sharma",
      "relationship": "Mother",
      "phone": "+977 9841234568",
      "email": "sumitra.sharma@example.com",
      "address": "Kathmandu, Nepal"
    },
    {
      "name": "Ravi Sharma",
      "relationship": "Father",
      "phone": "+977 9841234569",
      "email": "ravi.sharma@example.com",
      "address": "Kathmandu, Nepal"
    }
  ]
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "emergency_contact",
  "completed_steps": ["personal_details", "emergency_contact"],
  "next_step": "health_cover",
  "progress_percentage": 16.66
}
```

---

### Step 3: Overseas Student Health Cover

```http
PATCH /api/v1/applications/{app_id}/steps/health-cover
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "health_cover_policy": {
    "provider": "Allianz Care Australia",
    "policy_number": "OSHC-123456",
    "coverage_type": "Comprehensive",
    "start_date": "2026-01-01",
    "end_date": "2029-12-31",
    "coverage_amount": 50000.00,
    "policy_holder_name": "Ram Sharma",
    "policy_holder_relationship": "Self"
  }
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "health_cover",
  "completed_steps": ["personal_details", "emergency_contact", "health_cover"],
  "next_step": "language_cultural",
  "progress_percentage": 25,
  "validation": {
    "coverage_duration_valid": true,
    "course_duration_weeks": 156,
    "coverage_duration_weeks": 156
  },
  "flags": []
}
```

**Auto-Populate with Health Insurance Upload:**
```http
POST /api/v1/applications/{app_id}/documents/upload
Content-Type: multipart/form-data

Request:
{
  "document_type": "health_insurance",
  "file": <insurance.pdf>,
  "auto_populate": true
}

Response:
{
  "ocr_result": {
    "extracted_fields": {
      "provider": "Allianz Care Australia",
      "policy_number": "OSHC-123456",
      "start_date": "2026-01-01",
      "end_date": "2029-12-31"
    }
  },
  "auto_populate_result": {
    "populated_fields": 4
  }
}
```

---

### Step 4: Language and Cultural Diversity

```http
PATCH /api/v1/applications/{app_id}/steps/language-cultural
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "language_cultural_data": {
    "first_language": "Nepali",
    "other_languages": ["English", "Hindi"],
    "english_proficiency": "Fluent",
    "ethnic_background": "South Asian",
    "religion": "Hindu",
    "indigenous_status": false
  },
  "english_test": {
    "test_type": "IELTS",
    "overall_score": 6.5,
    "reading": 6.0,
    "writing": 6.5,
    "speaking": 7.0,
    "listening": 6.5,
    "test_date": "2024-11-17"
  }
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "language_cultural",
  "completed_steps": ["personal_details", "emergency_contact", "health_cover", "language_cultural"],
  "next_step": "disability",
  "progress_percentage": 33.33,
  "validation": {
    "meets_english_requirement": true,
    "minimum_required": 6.0,
    "student_score": 6.5
  },
  "flags": [
    {
      "type": "VALIDITY_WARNING",
      "severity": "warning",
      "message": "IELTS expires 2026-11-17 (1.5 years remaining)"
    }
  ]
}
```

**Auto-Populate with IELTS Upload:**
```http
POST /api/v1/applications/{app_id}/documents/upload
Content-Type: multipart/form-data

Request:
{
  "document_type": "ielts",
  "file": <ielts.pdf>,
  "auto_populate": true
}

Response:
{
  "ocr_result": {
    "extracted_fields": {
      "test_type": "IELTS",
      "overall_band": "6.5",
      "reading": "6.0",
      "writing": "6.5",
      "speaking": "7.0",
      "listening": "6.5",
      "test_date": "2024-11-17"
    }
  },
  "auto_populate_result": {
    "populated_fields": 7
  }
}
```

---

### Step 5: Disability

```http
PATCH /api/v1/applications/{app_id}/steps/disability
Authorization: Bearer {access_token}
Content-Type: application/json

Request (No Disability):
{
  "has_disability": false,
  "disability_details": null,
  "requires_accommodation": false,
  "accommodation_details": null
}

Request (With Disability):
{
  "has_disability": true,
  "disability_details": {
    "type": "Visual Impairment",
    "description": "Partially sighted - requires large print materials"
  },
  "requires_accommodation": true,
  "accommodation_details": "Need seating near front of classroom, extended time for exams"
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "disability",
  "completed_steps": [..., "disability"],
  "next_step": "schooling",
  "progress_percentage": 41.66
}
```

---

### Step 6: Schooling

```http
PATCH /api/v1/applications/{app_id}/steps/schooling
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "schooling_history": [
    {
      "institution": "Kathmandu Model Secondary School",
      "country": "Nepal",
      "start_year": 2018,
      "end_year": 2020,
      "qualification_level": "High School Diploma",
      "field_of_study": "General Studies",
      "result": "Grade A (85%)",
      "currently_studying": false
    },
    {
      "institution": "Tribhuvan University",
      "country": "Nepal",
      "start_year": 2020,
      "end_year": 2023,
      "qualification_level": "Bachelor's Degree",
      "field_of_study": "Computer Science",
      "result": "First Class (75%)",
      "currently_studying": false
    }
  ]
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "schooling",
  "completed_steps": [..., "schooling"],
  "next_step": "previous_qualifications",
  "progress_percentage": 50
}
```

**Auto-Populate with Transcript Upload:**
```http
POST /api/v1/applications/{app_id}/documents/upload
Content-Type: multipart/form-data

Request:
{
  "document_type": "transcript",
  "file": <transcript.pdf>,
  "auto_populate": true
}

Response:
{
  "ocr_result": {
    "extracted_fields": {
      "institution": "Kathmandu Model Secondary School",
      "country": "Nepal",
      "start_year": "2018",
      "end_year": "2020",
      "qualification": "High School Diploma",
      "result": "Grade A (85%)"
    }
  },
  "auto_populate_result": {
    "created_record": {
      "type": "schooling_history",
      "id": "school-1",
      "institution": "Kathmandu Model Secondary School"
    }
  }
}
```

---

### Step 7: Previous Qualifications Achieved

```http
PATCH /api/v1/applications/{app_id}/steps/previous-qualifications
Authorization: Bearer {access_token}
Content-Type: application/json

Request (With Qualifications):
{
  "has_previous_qualifications": true,
  "qualifications": [
    {
      "qualification_name": "Certified Web Developer",
      "issuing_institution": "Nepal IT Academy",
      "country": "Nepal",
      "year_completed": 2022,
      "certificate_number": "CWD-2022-123"
    }
  ]
}

Request (No Qualifications):
{
  "has_previous_qualifications": false,
  "qualifications": []
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "previous_qualifications",
  "completed_steps": [..., "previous_qualifications"],
  "next_step": "employment",
  "progress_percentage": 58.33
}
```

---

### Step 8: Employment

```http
PATCH /api/v1/applications/{app_id}/steps/employment
Authorization: Bearer {access_token}
Content-Type: application/json

Request (With Employment):
{
  "has_employment": true,
  "employment_history": [
    {
      "employer": "Nepal Tech Consultancy",
      "job_title": "Full Stack Developer",
      "country": "Nepal",
      "start_date": "2023-06-01",
      "end_date": null,
      "is_current": true,
      "duties": "Developing web applications using React and Node.js"
    },
    {
      "employer": "Digital Nepal Pvt Ltd",
      "job_title": "Junior Developer",
      "country": "Nepal",
      "start_date": "2022-01-01",
      "end_date": "2023-05-31",
      "is_current": false,
      "duties": "Frontend development and testing"
    }
  ]
}

Request (No Employment):
{
  "has_employment": false,
  "employment_history": []
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "employment",
  "completed_steps": [..., "employment"],
  "next_step": "usi",
  "progress_percentage": 66.66
}
```

**Auto-Populate with Employment Letter Upload:**
```http
POST /api/v1/applications/{app_id}/documents/upload
Content-Type: multipart/form-data

Request:
{
  "document_type": "employment_letter",
  "file": <employment.pdf>,
  "auto_populate": true
}

Response:
{
  "ocr_result": {
    "extracted_fields": {
      "employer": "Nepal Tech Consultancy",
      "job_title": "Full Stack Developer",
      "start_date": "2023-06-01",
      "is_current": true
    }
  },
  "auto_populate_result": {
    "created_record": {
      "type": "employment_history",
      "id": "employment-1"
    }
  }
}
```

---

### Step 9: USI

```http
PATCH /api/v1/applications/{app_id}/steps/usi
Authorization: Bearer {access_token}
Content-Type: application/json

Request (Has USI):
{
  "has_usi": true,
  "usi_number": "ABC123DEF456"
}

Request (No USI):
{
  "has_usi": false,
  "usi_number": null,
  "authorize_creation": true
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "usi",
  "completed_steps": [..., "usi"],
  "next_step": "additional_services",
  "progress_percentage": 75
}
```

---

### Step 10: Additional Services

```http
PATCH /api/v1/applications/{app_id}/steps/additional-services
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "additional_services": [
    {
      "service_type": "airport_pickup",
      "selected": true,
      "cost": 50.00,
      "details": {
        "arrival_date": "2026-01-15",
        "flight_details": "QR123 - Doha to Sydney"
      }
    },
    {
      "service_type": "accommodation_assistance",
      "selected": false,
      "cost": 100.00
    },
    {
      "service_type": "career_counseling",
      "selected": true,
      "cost": 0.00
    },
    {
      "service_type": "airport_lounge",
      "selected": false,
      "cost": 30.00
    },
    {
      "service_type": "orientation_program",
      "selected": true,
      "cost": 0.00
    }
  ],
  "total_cost": 50.00
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "additional_services",
  "completed_steps": [..., "additional_services"],
  "next_step": "survey",
  "progress_percentage": 83.33
}
```

---

### Step 11: Survey Status

```http
PATCH /api/v1/applications/{app_id}/steps/survey
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "survey_responses": [
    {
      "question_id": "how_did_you_hear",
      "answer": "Agent/Consultant"
    },
    {
      "question_id": "decision_factors",
      "answer": ["Course Quality", "Location", "Career Opportunities"]
    },
    {
      "question_id": "career_goals",
      "answer": "To become a senior software engineer and eventually start my own tech company"
    },
    {
      "question_id": "work_while_studying",
      "answer": "Yes, part-time"
    },
    {
      "question_id": "additional_comments",
      "answer": "Very excited to study in Australia"
    }
  ]
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "survey",
  "completed_steps": [..., "survey"],
  "next_step": "document",
  "progress_percentage": 91.66
}
```

---

### Step 12: Document

```http
GET /api/v1/applications/{app_id}/steps/document
Authorization: Bearer {access_token}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "document",
  "required_documents": [
    {
      "type": "passport",
      "status": "verified",
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:35:00Z",
      "document_id": "doc-passport-123"
    },
    {
      "type": "ielts",
      "status": "verified",
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:38:00Z",
      "document_id": "doc-ielts-125"
    },
    {
      "type": "transcript",
      "status": "verified",
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:42:00Z",
      "document_id": "doc-transcript-124"
    },
    {
      "type": "health_insurance",
      "status": "pending_review",
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:45:00Z",
      "document_id": "doc-insurance-127"
    }
  ],
  "optional_documents": [
    {
      "type": "employment_letter",
      "status": "verified",
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:47:00Z",
      "document_id": "doc-employment-126"
    },
    {
      "type": "police_clearance",
      "status": "not_uploaded",
      "uploaded": false
    },
    {
      "type": "financial_statement",
      "status": "not_uploaded",
      "uploaded": false
    }
  ],
  "all_required_uploaded": true,
  "can_proceed": true
}
```

**Complete Document Step:**
```http
PATCH /api/v1/applications/{app_id}/steps/document
Authorization: Bearer {access_token}
Content-Type: application/json

Request:
{
  "acknowledge_required_documents": true
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_step": "document",
  "completed_steps": [
    "personal_details", "emergency_contact", "health_cover", 
    "language_cultural", "disability", "schooling", 
    "previous_qualifications", "employment", "usi", 
    "additional_services", "survey", "document"
  ],
  "next_step": "review_submit",
  "progress_percentage": 100,
  "all_steps_complete": true
}
```

---

## Document Management

### Upload Document (with OCR Auto-Populate)

```http
POST /api/v1/applications/{app_id}/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Request:
{
  "document_type": "passport",           # Required
  "file": <binary_file>,                 # Required (PDF, JPG, PNG - max 10MB)
  "auto_populate": true,                 # Optional (default: true)
  "description": "Student passport"      # Optional
}

Response (201 Created) - Waits for OCR (3-5 seconds):
{
  "document": {
    "id": "doc-uuid-123",
    "application_id": "app-uuid-456",
    "document_type": "passport",
    "status": "ready",
    "uploaded_by": "agent-uuid-123",
    "uploaded_at": "2025-11-17T10:35:00Z",
    "file_name": "passport.pdf",
    "file_size_bytes": 245000,
    "blob_url": "https://blob.../doc-uuid-123.pdf",
    "preview_url": "https://blob.../doc-uuid-123-thumb.jpg"
  },
  
  "ocr_result": {
    "status": "success",
    "processing_time_ms": 4200,
    "overall_confidence": 0.98,
    "extracted_fields": {
      "given_name": {"value": "Ram", "confidence": 0.99},
      "family_name": {"value": "Sharma", "confidence": 0.99},
      "date_of_birth": {"value": "2000-05-15", "confidence": 0.95},
      "passport_number": {"value": "C1234567", "confidence": 0.98},
      "nationality": {"value": "Nepalese", "confidence": 0.97},
      "gender": {"value": "Male", "confidence": 0.96},
      "expiry_date": {"value": "2030-05-14", "confidence": 0.96}
    }
  },
  
  "auto_populate_result": {
    "status": "success",
    "populated_fields": [
      {
        "field": "given_name",
        "old_value": null,
        "new_value": "Ram",
        "source": "passport_ocr"
      },
      {
        "field": "family_name",
        "old_value": null,
        "new_value": "Sharma",
        "source": "passport_ocr"
      },
      {
        "field": "date_of_birth",
        "old_value": null,
        "new_value": "2000-05-15",
        "source": "passport_ocr"
      }
    ],
    "total_populated": 5
  },
  
  "flags": [
    {
      "type": "INFO",
      "severity": "info",
      "message": "Passport valid for 5 years (expires 2030-05-14)"
    }
  ],
  
  "validation": {
    "all_matches": true,
    "mismatches": []
  },
  
  "message": "✅ Document uploaded successfully. 5 fields auto-populated."
}
```

### List Documents

```http
GET /api/v1/applications/{app_id}/documents
Authorization: Bearer {access_token}

Query Parameters:
  ?status=verified           # Filter by status
  ?document_type=passport    # Filter by type

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "documents": [
    {
      "id": "doc-uuid-123",
      "document_type": "passport",
      "status": "verified",
      "uploaded_by": {
        "id": "agent-uuid-123",
        "name": "Test Agent"
      },
      "uploaded_at": "2025-11-17T10:35:00Z",
      "file_name": "passport.pdf",
      "file_size_bytes": 245000,
      "ocr_confidence": 0.98,
      "preview_url": "https://blob.../doc-uuid-123-thumb.jpg",
      "verified_by": {
        "id": "staff-uuid-999",
        "name": "Staff Member"
      },
      "verified_at": "2025-11-17T10:40:00Z",
      "flags_count": 0
    }
  ],
  "summary": {
    "total": 5,
    "verified": 3,
    "pending_review": 1,
    "rejected": 1
  }
}
```

### Get Document Details

```http
GET /api/v1/applications/{app_id}/documents/{doc_id}
Authorization: Bearer {access_token}

Response (200 OK):
{
  "id": "doc-uuid-123",
  "application_id": "app-uuid-456",
  "document_type": "passport",
  "status": "verified",
  "uploaded_by": {...},
  "uploaded_at": "2025-11-17T10:35:00Z",
  "file_name": "passport.pdf",
  "blob_url": "https://blob.../doc-uuid-123.pdf",
  "preview_url": "https://blob.../doc-uuid-123-thumb.jpg",
  
  "ocr_data": {
    "status": "success",
    "completed_at": "2025-11-17T10:35:30Z",
    "overall_confidence": 0.98,
    "extracted_fields": {...}
  },
  
  "validation": {
    "matches": [...],
    "mismatches": []
  },
  
  "flags": [],
  
  "verification": {
    "status": "verified",
    "verified_by": {...},
    "verified_at": "2025-11-17T10:40:00Z",
    "notes": "All data matches. Passport valid."
  }
}
```

### Download Document

```http
GET /api/v1/documents/{doc_id}/download
Authorization: Bearer {access_token}

Response (302 Redirect):
Redirects to Azure Blob Storage signed URL
```

### Delete Document

```http
DELETE /api/v1/applications/{app_id}/documents/{doc_id}
Authorization: Bearer {access_token}

Response (200 OK):
{
  "message": "Document deleted successfully",
  "document_id": "doc-uuid-123"
}
```

---

## Validation & Flags

### Get All Flags for Application

```http
GET /api/v1/applications/{app_id}/flags
Authorization: Bearer {access_token}

Query Parameters:
  ?severity=error         # Filter by severity (error, warning, info)
  ?resolved=false         # Show only unresolved

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "flags": [
    {
      "flag_id": "flag-1",
      "document_id": "doc-uuid-124",
      "type": "VALIDITY_WARNING",
      "severity": "warning",
      "message": "IELTS expires 2026-11-17 (1.5 years remaining)",
      "created_at": "2025-11-17T10:37:00Z",
      "resolved": false
    },
    {
      "flag_id": "flag-2",
      "document_id": null,
      "type": "MISSING_DOCUMENT",
      "severity": "error",
      "message": "Health insurance certificate not uploaded",
      "created_at": "2025-11-17T10:50:00Z",
      "resolved": false,
      "document_type_required": "health_insurance"
    }
  ],
  "summary": {
    "total": 2,
    "errors": 1,
    "warnings": 1,
    "info": 0,
    "resolved": 0,
    "unresolved": 2
  }
}
```

### Resolve Flag (Staff Only)

```http
PATCH /api/v1/applications/{app_id}/flags/{flag_id}/resolve
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "action": "resolve",
  "resolution_notes": "Verified manually - IELTS validity acceptable"
}

Response (200 OK):
{
  "flag_id": "flag-1",
  "status": "resolved",
  "resolved_by": {
    "id": "staff-uuid-111",
    "name": "Staff Member"
  },
  "resolved_at": "2025-11-17T10:55:00Z",
  "resolution_notes": "Verified manually - IELTS validity acceptable"
}
```

---

## Staff Review Workflow

### Get Pending Applications (Staff Only)

```http
GET /api/v1/staff/applications/pending
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Response (200 OK):
{
  "applications": [
    {
      "id": "app-uuid-456",
      "student_name": "Ram Sharma",
      "course": "Bachelor of IT",
      "submitted_at": "2025-11-17T11:00:00Z",
      "sla_deadline": "2025-11-19T11:00:00Z",
      "sla_status": "on_time",
      "documents_pending": 5,
      "flags_count": 2
    }
  ]
}
```

### Verify Document (Staff Only)

```http
PATCH /api/v1/applications/{app_id}/documents/{doc_id}/verify
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "status": "verified",
  "notes": "All data matches. Document is valid."
}

Response (200 OK):
{
  "id": "doc-uuid-123",
  "status": "verified",
  "verified_by": {
    "id": "staff-uuid-999",
    "name": "Staff Member"
  },
  "verified_at": "2025-11-17T10:40:00Z",
  "notes": "All data matches. Document is valid.",
  "message": "Document verified successfully"
}
```

### Reject Document (Staff Only)

```http
PATCH /api/v1/applications/{app_id}/documents/{doc_id}/reject
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "status": "rejected",
  "rejection_reason": "Image quality too poor - unable to read text clearly"
}

Response (200 OK):
{
  "id": "doc-uuid-125",
  "status": "rejected",
  "rejected_by": {
    "id": "staff-uuid-111",
    "name": "Staff Member"
  },
  "rejected_at": "2025-11-17T10:47:00Z",
  "rejection_reason": "Image quality too poor - unable to read text clearly",
  "message": "Document rejected. Agent has been notified."
}
```

### Request Document (Staff Only)

```http
POST /api/v1/applications/{app_id}/documents/request
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "document_type": "ielts",
  "deadline": "2025-11-30",
  "message": "Please upload IELTS certificate",
  "is_mandatory": true
}

Response (201 Created):
{
  "request_id": "req-uuid-123",
  "application_id": "app-uuid-456",
  "document_type": "ielts",
  "requested_by": {
    "id": "staff-uuid-111",
    "name": "Staff Member"
  },
  "requested_at": "2025-11-17T10:50:00Z",
  "deadline": "2025-11-30",
  "message": "Please upload IELTS certificate",
  "status": "pending",
  "is_mandatory": true,
  "notification_sent": true
}
```

### Approve Application (Staff Only)

```http
PATCH /api/v1/applications/{app_id}/approve
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "stage": "document_verification",
  "next_stage": "gs_assessment",
  "notes": "All documents verified"
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "current_stage": "gs_assessment",
  "status": "approved_for_gs",
  "approved_by": {
    "id": "staff-uuid-999",
    "name": "Staff Member"
  },
  "approved_at": "2025-11-17T11:30:00Z"
}
```

### Reject Application (Staff Only)

```http
PATCH /api/v1/applications/{app_id}/reject
Authorization: Bearer {access_token}
Role: STAFF, ADMIN

Request:
{
  "rejection_reason": "Does not meet course requirements",
  "details": "IELTS score below minimum requirement"
}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "status": "rejected",
  "rejected_by": {
    "id": "staff-uuid-111",
    "name": "Staff Member"
  },
  "rejected_at": "2025-11-17T11:35:00Z",
  "rejection_reason": "Does not meet course requirements",
  "notification_sent": true
}
```

---

## Submit Application

### Review Application Before Submit

```http
GET /api/v1/applications/{app_id}/summary
Authorization: Bearer {access_token}

Response (200 OK):
{
  "application_id": "app-uuid-456",
  "student": {
    "given_name": "Ram",
    "family_name": "Sharma",
    "email": "ram.sharma@example.com"
  },
  "course": {
    "course_name": "Bachelor of IT",
    "campus": "Melbourne",
    "intake": "2025 Semester 1"
  },
  "completed_steps": [
    "personal_details", "emergency_contact", "health_cover",
    "language_cultural", "disability", "schooling",
    "previous_qualifications", "employment", "usi",
    "additional_services", "survey", "document"
  ],
  "form_completion_percentage": 100,
  "documents": [
    {
      "type": "passport",
      "status": "verified",
      "uploaded_at": "2025-11-17T10:35:00Z"
    },
    {
      "type": "ielts",
      "status": "verified",
      "uploaded_at": "2025-11-17T10:38:00Z"
    },
    {
      "type": "transcript",
      "status": "verified",
      "uploaded_at": "2025-11-17T10:42:00Z"
    },
    {
      "type": "health_insurance",
      "status": "pending_review",
      "uploaded_at": "2025-11-17T10:45:00Z"
    }
  ],
  "flags": [
    {
      "type": "VALIDITY_WARNING",
      "message": "IELTS expires in 1.5 years",
      "severity": "warning"
    }
  ],
  "can_submit": true,
  "blocking_issues": []
}
```

### Submit Application

```http
POST /api/v1/applications/{app_id}/submit
Authorization: Bearer {access_token}

Request:
{
  "confirm_accuracy": true,
  "understand_consequences": true,
  "agent_notes": "Application complete and ready for review"
}

Response (200 OK):
{
  "id": "app-uuid-456",
  "status": "submitted",
  "current_stage": "staff_review",
  "submitted_at": "2025-11-17T11:30:00Z",
  "submission_reference": "APP-2025-001234",
  "message": "Application submitted successfully",
  "next_steps": [
    "Staff will review your application within 2 business days",
    "Document verification will be completed",
    "You will receive email notifications on progress",
    "Track your application status in the dashboard"
  ],
  "estimated_review_completion": "2025-11-19T11:30:00Z"
}

Error (400 Bad Request) - Cannot Submit:
{
  "error": "CANNOT_SUBMIT",
  "message": "Cannot submit - blocking issues exist",
  "blocking_issues": [
    {
      "type": "MISSING_DOCUMENT",
      "message": "Transcript not uploaded"
    },
    {
      "type": "INCOMPLETE_STEP",
      "step": "employment",
      "message": "Employment history not completed"
    }
  ],
  "status_code": 400
}
```

---

## Real-time Updates (WebSocket)

### WebSocket Connection

```javascript
WS /api/v1/ws
Connection: Upgrade
Upgrade: websocket
Authorization: Bearer {access_token}

Connected Message:
{
  "type": "CONNECTED",
  "user_id": "agent-uuid-123",
  "message": "WebSocket connected successfully"
}
```

### Event Types

#### Document OCR Started
```json
{
  "type": "DOCUMENT_OCR_STARTED",
  "application_id": "app-uuid-456",
  "document_type": "passport",
  "timestamp": "2025-11-17T10:35:00Z"
}
```

#### Document OCR Completed
```json
{
  "type": "DOCUMENT_OCR_COMPLETED",
  "data": {
    "application_id": "app-uuid-456",
    "document_id": "doc-uuid-123",
    "document_type": "passport",
    "ocr_status": "success",
    "ocr_confidence": 0.98,
    "extracted_fields": {
      "given_name": "Ram",
      "family_name": "Sharma",
      "date_of_birth": "2000-05-15",
      "passport_number": "C1234567"
    },
    "auto_populated_fields": 5,
    "message": "Passport OCR complete - 5 fields auto-populated"
  },
  "timestamp": "2025-11-17T10:35:30Z"
}
```

#### Application Stage Changed
```json
{
  "type": "APPLICATION_STAGE_CHANGED",
  "data": {
    "application_id": "app-uuid-456",
    "old_stage": "submitted",
    "new_stage": "staff_review",
    "changed_by": {
      "id": "staff-uuid-111",
      "name": "Staff Member"
    },
    "message": "Your application is now under staff review"
  },
  "timestamp": "2025-11-17T11:00:00Z"
}
```

#### Document Verified
```json
{
  "type": "DOCUMENT_VERIFIED",
  "data": {
    "application_id": "app-uuid-456",
    "document_id": "doc-uuid-123",
    "document_type": "passport",
    "verified_by": {
      "id": "staff-uuid-999",
      "name": "Staff Member"
    },
    "message": "Passport verified successfully"
  },
  "timestamp": "2025-11-17T10:40:00Z"
}
```

#### Document Rejected
```json
{
  "type": "DOCUMENT_REJECTED",
  "data": {
    "application_id": "app-uuid-456",
    "document_id": "doc-uuid-125",
    "document_type": "employment_letter",
    "rejected_by": {
      "id": "staff-uuid-111",
      "name": "Staff Member"
    },
    "rejection_reason": "Image quality too poor",
    "message": "Employment letter rejected - please re-upload"
  },
  "timestamp": "2025-11-17T10:47:00Z"
}
```

---

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful",
  "timestamp": "2025-11-17T10:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {...},
    "status_code": 401
  },
  "timestamp": "2025-11-17T10:00:00Z"
}
```

### Validation Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "validation_errors": [
      {
        "field": "email",
        "message": "Invalid email format"
      },
      {
        "field": "password",
        "message": "Password must be at least 8 characters"
      }
    ],
    "status_code": 422
  },
  "timestamp": "2025-11-17T10:00:00Z"
}
```

### Pagination Format
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Meaning | Usage |
|------------|---------|-------|
| 200 | OK | Successful GET, PATCH, DELETE |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Invalid request data, validation errors |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists, duplicate entry |
| 413 | Payload Too Large | File size exceeds limit |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily down |

### Common Error Codes

| Error Code | Description |
|-----------|-------------|
| `INVALID_CREDENTIALS` | Invalid email/password |
| `TOKEN_EXPIRED` | JWT token expired |
| `VALIDATION_ERROR` | Input validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `DUPLICATE_ENTRY` | Resource already exists |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `INCOMPLETE_APPLICATION` | Application missing required data |
| `DOCUMENT_UPLOAD_FAILED` | Document upload error |
| `OCR_FAILED` | OCR processing failed |
| `LOW_OCR_CONFIDENCE` | OCR confidence below threshold |
| `FILE_TOO_LARGE` | File exceeds size limit |
| `INVALID_FILE_TYPE` | Unsupported file format |
| `MISSING_DOCUMENT` | Required document not uploaded |
| `CANNOT_SUBMIT` | Application cannot be submitted |

---

## Authentication Headers

All protected endpoints require:
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

Example:
```http
GET /api/v1/applications
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json
```

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|-----------|
| Authentication | 5 requests/minute |
| Document Upload | 10 requests/minute |
| All Other Endpoints | 100 requests/minute |

Rate Limit Headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1637164800
```

---

## File Upload Constraints

| Property | Value |
|----------|-------|
| Max File Size | 10 MB |
| Allowed Types | PDF, JPG, PNG |
| Max Files per Application | 20 |
| OCR Timeout | 10 seconds |
| Min OCR Confidence | 0.70 (70%) |

---

## Complete Endpoint Summary

### Authentication
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/api/v1/auth/login` | ❌ | Public | Login |
| POST | `/api/v1/auth/refresh` | ✅ | All | Refresh token |
| POST | `/api/v1/auth/logout` | ✅ | All | Logout |
| GET | `/api/v1/auth/me` | ✅ | All | Get current user |

### Application Lifecycle
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/api/v1/applications` | ✅ | Agent+ | Create application |
| GET | `/api/v1/applications` | ✅ | All | List applications |
| GET | `/api/v1/applications/{id}` | ✅ | All | Get application |
| GET | `/api/v1/applications/{id}/progress` | ✅ | All | Get progress |
| GET | `/api/v1/applications/{id}/summary` | ✅ | All | Get summary |
| POST | `/api/v1/applications/{id}/submit` | ✅ | Agent+ | Submit application |

### Application Steps
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| PATCH | `/api/v1/applications/{id}/steps/personal-details` | ✅ | Agent+ | Save personal details |
| PATCH | `/api/v1/applications/{id}/steps/emergency-contact` | ✅ | Agent+ | Save emergency contact |
| PATCH | `/api/v1/applications/{id}/steps/health-cover` | ✅ | Agent+ | Save health cover |
| PATCH | `/api/v1/applications/{id}/steps/language-cultural` | ✅ | Agent+ | Save language/cultural |
| PATCH | `/api/v1/applications/{id}/steps/disability` | ✅ | Agent+ | Save disability |
| PATCH | `/api/v1/applications/{id}/steps/schooling` | ✅ | Agent+ | Save schooling |
| PATCH | `/api/v1/applications/{id}/steps/previous-qualifications` | ✅ | Agent+ | Save qualifications |
| PATCH | `/api/v1/applications/{id}/steps/employment` | ✅ | Agent+ | Save employment |
| PATCH | `/api/v1/applications/{id}/steps/usi` | ✅ | Agent+ | Save USI |
| PATCH | `/api/v1/applications/{id}/steps/additional-services` | ✅ | Agent+ | Save services |
| PATCH | `/api/v1/applications/{id}/steps/survey` | ✅ | Agent+ | Save survey |
| GET | `/api/v1/applications/{id}/steps/document` | ✅ | Agent+ | Get document status |
| PATCH | `/api/v1/applications/{id}/steps/document` | ✅ | Agent+ | Complete document step |

### Document Management
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/api/v1/applications/{id}/documents/upload` | ✅ | Agent+ | Upload document (OCR) |
| GET | `/api/v1/applications/{id}/documents` | ✅ | All | List documents |
| GET | `/api/v1/applications/{id}/documents/{doc_id}` | ✅ | All | Get document |
| DELETE | `/api/v1/applications/{id}/documents/{doc_id}` | ✅ | Agent+ | Delete document |
| GET | `/api/v1/documents/{doc_id}/download` | ✅ | All | Download document |
| PATCH | `/api/v1/applications/{id}/documents/{doc_id}/verify` | ✅ | Staff+ | Verify document |
| PATCH | `/api/v1/applications/{id}/documents/{doc_id}/reject` | ✅ | Staff+ | Reject document |
| POST | `/api/v1/applications/{id}/documents/request` | ✅ | Staff+ | Request document |

### Flags & Validation
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/api/v1/applications/{id}/flags` | ✅ | All | Get flags |
| PATCH | `/api/v1/applications/{id}/flags/{flag_id}/resolve` | ✅ | Staff+ | Resolve flag |

### Staff Workflow
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/api/v1/staff/applications/pending` | ✅ | Staff+ | Get pending apps |
| PATCH | `/api/v1/applications/{id}/approve` | ✅ | Staff+ | Approve application |
| PATCH | `/api/v1/applications/{id}/reject` | ✅ | Staff+ | Reject application |

### WebSocket
| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| WS | `/api/v1/ws` | ✅ | All | Real-time updates |

**Legend:**
- ❌ = No auth required
- ✅ = Auth required
- Agent+ = Agent, Staff, Admin
- Staff+ = Staff, Admin

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-17 | Initial API specification |

---

## Notes for Frontend Developer

### Key Features
1. **12-Step Process**: Each step has independent save endpoint
2. **OCR Auto-Populate**: Upload document → Wait 3-5 seconds → Form auto-fills
3. **Real-time Updates**: WebSocket for OCR completion & status changes
4. **Save & Continue**: Every step can be saved as draft
5. **Progress Tracking**: Automatic calculation across all steps
6. **Validation**: Two levels - step-level and submission-level
7. **Document Management**: Upload anywhere, linked to application

### Best Practices
1. Show loading indicator during OCR (3-5 seconds)
2. Listen to WebSocket for real-time document processing
3. Display progress bar based on completed steps
4. Validate required fields before allowing "Save & Continue"
5. Show flags/warnings but allow progress unless critical error
6. Cache form data locally to prevent data loss
7. Implement auto-save every 30 seconds
8. Show document upload status clearly
9. Provide clear error messages from validation_errors array
10. Handle token refresh transparently

### Environment Variables
```env
DEV: http://localhost:8000/api/v1
STAGING: https://staging.churchillapp.com/api/v1
PROD: https://api.churchillapp.com/api/v1
WS_DEV: ws://localhost:8000/api/v1/ws
WS_STAGING: wss://staging.churchillapp.com/api/v1/ws
WS_PROD: wss://api.churchillapp.com/api/v1/ws
```

---

## References
- [Database Schema](./schema.dbml)
- [Solution Architecture](./solution-architecture.md)
- [Requirements Document](./requirements.md)

---

**Last Updated**: November 17, 2025  
**API Version**: 1.0  
**Base URL**: `/api/v1`