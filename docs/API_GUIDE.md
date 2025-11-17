# 📡 API Guide - Churchill Application Portal

Complete API reference for frontend integration and testing.

**Base URL**: `http://localhost:8000/api/v1`  
**Interactive Docs**: http://localhost:8000/docs

---

## Table of Contents

1. [Authentication](#authentication)
2. [Application Lifecycle](#application-lifecycle)
3. [12-Step Form Endpoints](#12-step-form-endpoints)
4. [Document Upload & OCR](#document-upload--ocr)
5. [Testing with Postman](#testing-with-postman)
6. [Frontend Integration Examples](#frontend-integration-examples)
7. [Error Handling](#error-handling)

---

## Authentication

### Login

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "username": "test.agent@agency.com",
  "password": "AgentPass123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "test.agent@agency.com",
    "role": "AGENT",
    "status": "active"
  }
}
```

### Using Tokens

Include access token in all requests:

**Header:**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**JavaScript:**
```javascript
headers: {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
}
```

### Get Current User

**Endpoint:** `GET /auth/me`

**Response (200 OK):**
```json
{
  "id": "user-uuid",
  "email": "test.agent@agency.com",
  "role": "AGENT",
  "status": "active",
  "created_at": "2025-11-17T10:00:00Z"
}
```

---

## Application Lifecycle

### Create Application

**Endpoint:** `POST /applications`  
**Permission:** Agent, Staff, Admin only

**Request:**
```json
{
  "student_profile_id": "student-uuid",
  "course_offering_id": "course-uuid"
}
```

**Response (201 Created):**
```json
{
  "application": {
    "id": "app-uuid",
    "student_profile_id": "student-uuid",
    "course_offering_id": "course-uuid",
    "agent_profile_id": "agent-uuid",
    "current_stage": "DRAFT",
    "created_at": "2025-11-17T10:00:00Z"
  },
  "message": "Application draft created successfully"
}
```

### Get Application

**Endpoint:** `GET /applications/{application_id}`

**Response (200 OK):**
```json
{
  "id": "app-uuid",
  "student_profile_id": "student-uuid",
  "course_offering_id": "course-uuid",
  "current_stage": "DRAFT",
  "form_metadata": {
    "completed_sections": ["personal_details", "emergency_contact"],
    "last_saved_at": "2025-11-17T10:30:00Z"
  },
  "created_at": "2025-11-17T10:00:00Z"
}
```

### List Applications

**Endpoint:** `GET /applications`

**Query Parameters:**
- `?status=draft` - Filter by status
- `?page=1&limit=20` - Pagination

**Response (200 OK):**
```json
{
  "applications": [
    {
      "id": "app-uuid",
      "student_name": "John Smith",
      "course_name": "Bachelor of IT",
      "current_stage": "DRAFT",
      "created_at": "2025-11-17T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20
}
```

---

## 12-Step Form Endpoints

All step endpoints follow this pattern:

**Pattern:** `PATCH /applications/{app_id}/steps/{step_number}/{step_name}`  
**Permission:** Agent, Staff, Admin only (Students cannot edit)

### Standard Response

Every step endpoint returns:

```json
{
  "success": true,
  "message": "Step saved successfully",
  "step_number": 1,
  "step_name": "personal_details",
  "completion_percentage": 8,
  "next_step": "emergency_contact",
  "can_submit": false
}
```

---

### Step 1: Personal Details

**Endpoint:** `PATCH /applications/{app_id}/steps/1/personal-details`

**Request:**
```json
{
  "given_name": "John",
  "middle_name": "Robert",
  "family_name": "Smith",
  "date_of_birth": "2000-01-15",
  "gender": "Male",
  "email": "john.smith@example.com",
  "phone": "+61412345678",
  "street_address": "123 Main St",
  "suburb": "Sydney",
  "state": "NSW",
  "postcode": "2000",
  "country": "Australia",
  "passport_number": "N1234567",
  "passport_expiry": "2030-12-31",
  "nationality": "Australian",
  "country_of_birth": "Australia"
}
```

**Field Notes:**
- ✅ Address fields are flat (not nested objects)
- ✅ Date format: `YYYY-MM-DD`
- ✅ `middle_name` and `passport_expiry` are optional

---

### Step 2: Emergency Contact

**Endpoint:** `PATCH /applications/{app_id}/steps/2/emergency-contact`

**Request:**
```json
{
  "contacts": [
    {
      "name": "Jane Smith",
      "relationship": "Mother",
      "phone": "+61412345679",
      "email": "jane.smith@example.com",
      "is_primary": true
    },
    {
      "name": "Bob Smith",
      "relationship": "Father",
      "phone": "+61412345680",
      "email": "bob.smith@example.com",
      "is_primary": false
    }
  ]
}
```

**Validation:**
- ✅ At least 1 contact required
- ✅ Maximum 5 contacts
- ✅ At least one must have `is_primary: true`

---

### Step 3: Health Cover

**Endpoint:** `PATCH /applications/{app_id}/steps/3/health-cover`

**Request:**
```json
{
  "provider": "Medibank",
  "policy_number": "MB123456",
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "coverage_type": "Comprehensive"
}
```

---

### Step 4: Language & Cultural

**Endpoint:** `PATCH /applications/{app_id}/steps/4/language-cultural`

**Request:**
```json
{
  "first_language": "English",
  "other_languages": ["Mandarin", "Spanish"],
  "english_proficiency": "Native",
  "requires_language_support": false,
  "cultural_background": "Australian",
  "indigenous_status": "Neither Aboriginal nor Torres Strait Islander"
}
```

**`english_proficiency` values:**
- "Native", "Fluent", "Intermediate", "Basic", "Minimal"

---

### Step 5: Disability Support

**Endpoint:** `PATCH /applications/{app_id}/steps/5/disability`

**Request (No Disability):**
```json
{
  "has_disability": false,
  "disability_type": null,
  "support_required": null,
  "previous_support": null,
  "consent_to_share": false
}
```

**Request (With Disability):**
```json
{
  "has_disability": true,
  "disability_type": "Mobility",
  "support_required": "Wheelchair access",
  "previous_support": "Yes, at previous institution",
  "consent_to_share": true
}
```

---

### Step 6-11: Other Steps

**Step 6: Schooling** - `PATCH /steps/6/schooling`
- `schools` array with institution, years, qualifications

**Step 7: Qualifications** - `PATCH /steps/7/qualifications`
- `qualifications` array (can be empty)

**Step 8: Employment** - `PATCH /steps/8/employment`
- `employment_records` array (can be empty)

**Step 9: USI** - `PATCH /steps/9/usi`
- `usi` string (10 characters, alphanumeric)
- `consent_to_verify` boolean

**Step 10: Additional Services** - `PATCH /steps/10/additional-services`
- `services` array with service_type, is_required, notes

**Step 11: Survey** - `PATCH /steps/11/survey`
- `responses` array with question/answer pairs

---

### Step 12: Documents

**Endpoint:** `GET /applications/{app_id}/steps/12/documents` (read-only)

**Response:**
```json
{
  "required_documents": [
    {
      "document_type_code": "PASSPORT",
      "document_type_name": "Passport Copy",
      "is_mandatory": true,
      "uploaded": true,
      "uploaded_at": "2025-11-17T10:30:00Z",
      "status": "verified"
    },
    {
      "document_type_code": "TRANSCRIPT",
      "document_type_name": "Academic Transcript",
      "is_mandatory": true,
      "uploaded": false
    }
  ],
  "total_required": 4,
  "total_uploaded": 1,
  "all_mandatory_uploaded": false
}
```

---

## Document Upload & OCR

### Upload Document

**Endpoint:** `POST /documents/upload`  
**Content-Type:** `multipart/form-data`

**Request (Form Data):**
```
application_id: app-uuid
document_type_id: 10000000-0000-0000-0000-000000000001
file: <binary_file>
process_ocr: true
```

**Response (201 Created):**
```json
{
  "document": {
    "id": "doc-uuid",
    "application_id": "app-uuid",
    "document_type_id": "10000000-0000-0000-0000-000000000001",
    "status": "PENDING_REVIEW",
    "uploaded_at": "2025-11-17T10:35:00Z",
    "file_name": "passport.pdf",
    "file_size_bytes": 245000
  },
  "ocr_result": {
    "status": "COMPLETED",
    "extracted_data": {
      "given_name": "John",
      "family_name": "Smith",
      "passport_number": "N1234567",
      "date_of_birth": "2000-01-15",
      "nationality": "Australian"
    },
    "overall_confidence": 0.95
  },
  "message": "Document uploaded and processed successfully"
}
```

### Get OCR Results

**Endpoint:** `GET /documents/{document_id}/ocr`

**Response:**
```json
{
  "document_id": "doc-uuid",
  "ocr_status": "COMPLETED",
  "extracted_data": {
    "given_name": "John",
    "family_name": "Smith",
    "passport_number": "N1234567",
    "date_of_birth": "2000-01-15"
  },
  "overall_confidence": 0.95,
  "processed_at": "2025-11-17T10:35:30Z"
}
```

### Get Auto-fill Suggestions

**Endpoint:** `GET /documents/application/{app_id}/autofill`

**Response:**
```json
{
  "application_id": "app-uuid",
  "suggestions": [
    {
      "field_path": "personal_details.given_name",
      "current_value": null,
      "extracted_value": "John",
      "confidence": 0.95,
      "source_document_id": "doc-uuid",
      "source_document_type": "PASSPORT"
    },
    {
      "field_path": "personal_details.passport_number",
      "current_value": null,
      "extracted_value": "N1234567",
      "confidence": 0.98,
      "source_document_id": "doc-uuid",
      "source_document_type": "PASSPORT"
    }
  ],
  "total_suggestions": 5
}
```

### Document Statistics

**Endpoint:** `GET /documents/application/{app_id}/stats`

**Response:**
```json
{
  "total_documents": 3,
  "by_status": {
    "PENDING_REVIEW": 1,
    "APPROVED": 2,
    "REJECTED": 0
  },
  "by_ocr_status": {
    "COMPLETED": 2,
    "FAILED": 1
  },
  "missing_mandatory": [
    "TRANSCRIPT",
    "ENGLISH_TEST"
  ]
}
```

---

## Testing with Postman

### 1. Setup Environment Variables

Create Postman Environment:

| Variable | Value |
|----------|-------|
| `base_url` | `http://localhost:8000/api/v1` |
| `agent_token` | _(set after login)_ |
| `student_profile_id` | _(set after creating student)_ |
| `application_id` | _(set after creating app)_ |

### 2. Login and Save Token

**POST** `{{base_url}}/auth/login`

**Body:**
```json
{
  "username": "test.agent@agency.com",
  "password": "AgentPass123!"
}
```

**Tests Tab (Auto-save token):**
```javascript
var jsonData = pm.response.json();
pm.environment.set("agent_token", jsonData.access_token);
console.log("Token saved:", jsonData.access_token);
```

### 3. Create Test Student

**POST** `{{base_url}}/students`

**Headers:**
```
Authorization: Bearer {{agent_token}}
```

**Body:**
```json
{
  "email": "student@test.com",
  "password": "StudentPass123!",
  "given_name": "John",
  "family_name": "Smith",
  "date_of_birth": "2000-01-15",
  "nationality": "Australia",
  "phone": "+61412345678",
  "address": "123 Main St, Sydney NSW 2000"
}
```

**Tests Tab:**
```javascript
var jsonData = pm.response.json();
pm.environment.set("student_profile_id", jsonData.profile.id);
```

### 4. Create Application

**POST** `{{base_url}}/applications`

**Body:**
```json
{
  "student_profile_id": "{{student_profile_id}}",
  "course_offering_id": "get-from-database"
}
```

**Tests Tab:**
```javascript
var jsonData = pm.response.json();
pm.environment.set("application_id", jsonData.application.id);
```

### 5. Update Step 1

**PATCH** `{{base_url}}/applications/{{application_id}}/steps/1/personal-details`

**Body:** _(see Step 1 example above)_

---

## Frontend Integration Examples

### React Hook for Step Updates

```typescript
// hooks/useApplicationStep.ts
import { useState } from 'react';
import { apiClient } from '../api/client';

interface StepResponse {
  success: boolean;
  message: string;
  completion_percentage: number;
  next_step: string | null;
  can_submit: boolean;
}

export function useApplicationStep(applicationId: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateStep = async (
    stepNumber: number,
    stepName: string,
    data: any
  ): Promise<StepResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.patch(
        `/applications/${applicationId}/steps/${stepNumber}/${stepName}`,
        data
      );
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update step');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { updateStep, loading, error };
}
```

### Using the Hook

```typescript
// components/PersonalDetailsForm.tsx
import { useApplicationStep } from '../hooks/useApplicationStep';

function PersonalDetailsForm({ applicationId }: { applicationId: string }) {
  const { updateStep, loading, error } = useApplicationStep(applicationId);
  const [formData, setFormData] = useState({
    given_name: '',
    family_name: '',
    date_of_birth: '',
    // ... other fields
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const result = await updateStep(1, 'personal-details', formData);
    
    if (result) {
      console.log('Progress:', result.completion_percentage + '%');
      console.log('Next step:', result.next_step);
      
      if (result.next_step) {
        // Navigate to next step
        navigate(`/applications/${applicationId}/${result.next_step}`);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={formData.given_name}
        onChange={(e) => setFormData({ ...formData, given_name: e.target.value })}
        placeholder="Given Name"
        required
      />
      {/* ... other fields */}
      
      {error && <div className="error">{error}</div>}
      
      <button type="submit" disabled={loading}>
        {loading ? 'Saving...' : 'Save & Continue'}
      </button>
    </form>
  );
}
```

### Auto-Save Implementation

```typescript
import { useEffect, useRef } from 'react';
import { debounce } from 'lodash';

function useAutoSave(applicationId: string, stepNumber: number, stepName: string, formData: any) {
  const { updateStep } = useApplicationStep(applicationId);
  
  const debouncedSave = useRef(
    debounce(async (data: any) => {
      if (data.given_name) { // Only save if form has data
        await updateStep(stepNumber, stepName, data);
        console.log('Auto-saved');
      }
    }, 2000) // Save 2 seconds after user stops typing
  ).current;

  useEffect(() => {
    debouncedSave(formData);
  }, [formData, debouncedSave]);

  useEffect(() => {
    return () => debouncedSave.cancel();
  }, [debouncedSave]);
}
```

### Document Upload Component

```typescript
async function uploadDocument(
  applicationId: string,
  documentTypeId: string,
  file: File
) {
  const formData = new FormData();
  formData.append('application_id', applicationId);
  formData.append('document_type_id', documentTypeId);
  formData.append('file', file);
  formData.append('process_ocr', 'true');
  
  const response = await fetch('/api/v1/documents/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error('Upload failed');
  }
  
  return response.json();
}

// Usage
const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;
  
  setUploading(true);
  try {
    const result = await uploadDocument(
      applicationId,
      '10000000-0000-0000-0000-000000000001', // Passport
      file
    );
    
    console.log('OCR extracted:', result.ocr_result.extracted_data);
    
    // Show auto-fill suggestions
    if (result.ocr_result.status === 'COMPLETED') {
      showAutoFillDialog(result.ocr_result.extracted_data);
    }
  } catch (err) {
    console.error('Upload failed:', err);
  } finally {
    setUploading(false);
  }
};
```

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Continue |
| 201 | Created | Resource created |
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Token expired - re-login |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Fix validation errors |
| 500 | Server Error | Report to backend team |

### Error Response Format

**Validation Error (422):**
```json
{
  "detail": "USI must be exactly 10 characters (letters and numbers only)"
}
```

**Permission Error (403):**
```json
{
  "detail": "Students cannot edit applications. Please contact your agent."
}
```

**Pydantic Validation Error (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "date_of_birth"],
      "msg": "invalid date format",
      "type": "value_error"
    }
  ]
}
```

### Error Handling Example

```typescript
async function handleApiError(error: any) {
  if (!error.response) {
    return 'Network error. Please check your connection.';
  }
  
  const { status, data } = error.response;
  
  switch (status) {
    case 401:
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      return 'Please log in to continue';
      
    case 403:
      return 'You do not have permission to perform this action';
      
    case 422:
      if (Array.isArray(data.detail)) {
        return data.detail.map((err: any) => 
          `${err.loc.join('.')}: ${err.msg}`
        ).join(', ');
      }
      return data.detail;
      
    case 404:
      return 'Resource not found';
      
    default:
      return 'An error occurred. Please try again.';
  }
}
```

---

## Quick Reference

### All Step Endpoints

| Step | Endpoint | Method |
|------|----------|--------|
| 1 | `/applications/{id}/steps/1/personal-details` | PATCH |
| 2 | `/applications/{id}/steps/2/emergency-contact` | PATCH |
| 3 | `/applications/{id}/steps/3/health-cover` | PATCH |
| 4 | `/applications/{id}/steps/4/language-cultural` | PATCH |
| 5 | `/applications/{id}/steps/5/disability` | PATCH |
| 6 | `/applications/{id}/steps/6/schooling` | PATCH |
| 7 | `/applications/{id}/steps/7/qualifications` | PATCH |
| 8 | `/applications/{id}/steps/8/employment` | PATCH |
| 9 | `/applications/{id}/steps/9/usi` | PATCH |
| 10 | `/applications/{id}/steps/10/additional-services` | PATCH |
| 11 | `/applications/{id}/steps/11/survey` | PATCH |
| 12 | `/applications/{id}/steps/12/documents` | GET |

### Permission Matrix

| Action | Student | Agent | Staff | Admin |
|--------|---------|-------|-------|-------|
| Create Application | ❌ 403 | ✅ | ✅ | ✅ |
| Edit Application | ❌ 403 | ✅ (own) | ✅ (all) | ✅ (all) |
| Upload Document | ✅ (own) | ✅ (own) | ✅ (assigned) | ✅ (all) |
| View Application | ✅ (own) | ✅ (own) | ✅ (all) | ✅ (all) |

---

## Additional Resources

- **Interactive API Docs**: http://localhost:8000/docs
- **Setup Guide**: [SETUP.md](./SETUP.md)
- **Features Guide**: [FEATURES.md](./FEATURES.md)
- **Database Reference**: [DATABASE.md](./DATABASE.md)

---

**Last Updated:** November 18, 2025  
**API Version:** 1.0
