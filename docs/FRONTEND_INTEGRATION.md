# Frontend Integration Guide - Application Portal API

**Version:** 1.0  
**Last Updated:** November 17, 2025  
**Base URL:** `http://localhost:8000/api/v1`

This guide provides everything frontend developers need to integrate with the Application Portal backend API.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Application Workflow](#application-workflow)
3. [12-Step Form Endpoints](#12-step-form-endpoints)
4. [Progress Tracking](#progress-tracking)
5. [Error Handling](#error-handling)
6. [Request/Response Examples](#requestresponse-examples)
7. [Frontend Implementation Guide](#frontend-implementation-guide)
8. [Testing with Mock Data](#testing-with-mock-data)

---

## Authentication

### Login Flow

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "username": "agent@agency.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "agent@agency.com",
    "role": "AGENT",
    "status": "ACTIVE"
  }
}
```

### Using Tokens

Include the access token in all subsequent requests:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

### Token Refresh

**Endpoint:** `POST /auth/refresh`

```json
{
  "refresh_token": "your-refresh-token"
}
```

---

## Application Workflow

### 1. Create New Application

**Endpoint:** `POST /applications`

**Request:**
```json
{
  "student_profile_id": "uuid-of-student",
  "course_offering_id": "uuid-of-course"
}
```

**Response (201 Created):**
```json
{
  "application": {
    "id": "application-uuid",
    "student_profile_id": "student-uuid",
    "course_offering_id": "course-uuid",
    "agent_profile_id": "agent-uuid",
    "current_stage": "DRAFT",
    "created_at": "2025-11-17T10:00:00Z",
    "updated_at": "2025-11-17T10:00:00Z"
  },
  "message": "Application draft created successfully. You can now fill in the details."
}
```

**Important:** When an agent creates an application, it's automatically assigned to them. No need to provide `agent_profile_id`.

### 2. Get Application Details

**Endpoint:** `GET /applications/{application_id}`

**Response (200 OK):**
```json
{
  "id": "application-uuid",
  "student_profile_id": "student-uuid",
  "course_offering_id": "course-uuid",
  "agent_profile_id": "agent-uuid",
  "current_stage": "DRAFT",
  "form_metadata": {
    "completed_sections": ["personal_details", "emergency_contact"],
    "last_saved_at": "2025-11-17T10:30:00Z",
    "auto_save_count": 5
  },
  "created_at": "2025-11-17T10:00:00Z",
  "updated_at": "2025-11-17T10:30:00Z"
}
```

---

## 12-Step Form Endpoints

All step endpoints follow the same pattern:
- **Method:** `PATCH`
- **Path:** `/applications/{application_id}/steps/{step_number}/{step_name}`
- **Auth:** Required (Bearer token)
- **Permissions:** Agents only (students cannot edit)

### Standard Response Format

All step endpoints return:

```typescript
interface StepUpdateResponse {
  success: boolean;
  message: string;
  step_number: number;
  step_name: string;
  completion_percentage: number;  // 0-100
  next_step: string | null;       // Next incomplete step
  can_submit: boolean;             // True when 100% complete
}
```

**Example Success Response:**
```json
{
  "success": true,
  "message": "Personal details saved successfully",
  "step_number": 1,
  "step_name": "personal_details",
  "completion_percentage": 8,
  "next_step": "emergency_contact",
  "can_submit": false
}
```

---

### Step 1: Personal Details

**Endpoint:** `PATCH /applications/{application_id}/steps/1/personal-details`

**Request Body:**
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
- ✅ Address fields are **flat** (not nested objects)
- ✅ `date_of_birth` format: `YYYY-MM-DD`
- ✅ `gender` values: "Male", "Female", "Other", "Prefer not to say"
- ✅ `middle_name` and `passport_expiry` are optional

---

### Step 2: Emergency Contact

**Endpoint:** `PATCH /applications/{application_id}/steps/2/emergency-contact`

**Request Body:**
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

**Validation Rules:**
- ✅ At least one contact must have `is_primary: true`
- ✅ Minimum 1 contact, maximum 5 contacts
- ✅ Email is optional

---

### Step 3: Health Cover

**Endpoint:** `PATCH /applications/{application_id}/steps/3/health-cover`

**Request Body:**
```json
{
  "provider": "Medibank",
  "policy_number": "MB123456",
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "coverage_type": "Comprehensive"
}
```

**Field Notes:**
- ✅ All fields required
- ✅ Date format: `YYYY-MM-DD`
- ✅ `coverage_type` examples: "Basic", "Comprehensive", "Student"

---

### Step 4: Language & Cultural Background

**Endpoint:** `PATCH /applications/{application_id}/steps/4/language-cultural`

**Request Body:**
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

**Field Notes:**
- ✅ `other_languages` is an array (can be empty)
- ✅ `english_proficiency` values: "Native", "Fluent", "Intermediate", "Basic", "Minimal"
- ✅ `indigenous_status` values:
  - "Aboriginal"
  - "Torres Strait Islander"
  - "Both Aboriginal and Torres Strait Islander"
  - "Neither Aboriginal nor Torres Strait Islander"

---

### Step 5: Disability Support

**Endpoint:** `PATCH /applications/{application_id}/steps/5/disability`

**Request Body:**
```json
{
  "has_disability": true,
  "disability_type": "Mobility",
  "support_required": "Wheelchair access",
  "previous_support": "Yes, at previous institution",
  "consent_to_share": true
}
```

**If no disability:**
```json
{
  "has_disability": false,
  "disability_type": null,
  "support_required": null,
  "previous_support": null,
  "consent_to_share": false
}
```

---

### Step 6: Schooling History

**Endpoint:** `PATCH /applications/{application_id}/steps/6/schooling`

**Request Body:**
```json
{
  "schools": [
    {
      "school_name": "Sydney High School",
      "country": "Australia",
      "years_attended": "2014-2019",
      "qualification": "HSC",
      "year_completed": 2019
    }
  ]
}
```

**Field Notes:**
- ✅ Array of schools (minimum 1)
- ✅ `years_attended` is a string (e.g., "2014-2019")
- ✅ `year_completed` is a number

---

### Step 7: Previous Qualifications

**Endpoint:** `PATCH /applications/{application_id}/steps/7/qualifications`

**Request Body:**
```json
{
  "qualifications": [
    {
      "institution": "University of Sydney",
      "qualification_name": "Bachelor of Science",
      "field_of_study": "Computer Science",
      "country": "Australia",
      "year_completed": 2023,
      "grade_average": "Distinction"
    }
  ]
}
```

**Or if no qualifications:**
```json
{
  "qualifications": []
}
```

---

### Step 8: Employment History

**Endpoint:** `PATCH /applications/{application_id}/steps/8/employment`

**Request Body:**
```json
{
  "employment_records": [
    {
      "employer": "Tech Corp",
      "position": "Software Developer",
      "start_date": "2023-01-01",
      "end_date": "2024-12-31",
      "is_current": false,
      "responsibilities": "Full-stack development"
    },
    {
      "employer": "StartupCo",
      "position": "Senior Developer",
      "start_date": "2025-01-01",
      "end_date": null,
      "is_current": true,
      "responsibilities": "Team lead and architecture"
    }
  ]
}
```

**Field Notes:**
- ✅ `end_date` is `null` if `is_current: true`
- ✅ Can be empty array if no employment history

---

### Step 9: USI (Unique Student Identifier)

**Endpoint:** `PATCH /applications/{application_id}/steps/9/usi`

**Request Body:**
```json
{
  "usi": "ABCD123456",
  "consent_to_verify": true
}
```

**Validation:**
- ✅ USI format: 10 characters (letters and numbers)
- ✅ Example valid USI: "ABCD123456", "XYZ9876543"
- ❌ Invalid: too short, special characters, spaces

**Error Response (422):**
```json
{
  "detail": "USI must be exactly 10 characters (letters and numbers only)"
}
```

---

### Step 10: Additional Services

**Endpoint:** `PATCH /applications/{application_id}/steps/10/additional-services`

**Request Body:**
```json
{
  "services": [
    {
      "service_type": "Airport Pickup",
      "is_required": true,
      "notes": "Arriving on Jan 15, 2025 at 3PM"
    },
    {
      "service_type": "Accommodation Assistance",
      "is_required": true,
      "notes": "Prefer on-campus housing"
    }
  ]
}
```

**Or no additional services:**
```json
{
  "services": []
}
```

**Common service types:**
- "Airport Pickup"
- "Accommodation Assistance"
- "Orientation Program"
- "Career Counseling"

---

### Step 11: Survey

**Endpoint:** `PATCH /applications/{application_id}/steps/11/survey`

**Request Body:**
```json
{
  "responses": [
    {
      "question": "How did you hear about Churchill Institute?",
      "answer": "Google Search"
    },
    {
      "question": "What are your career goals?",
      "answer": "Become a software engineer"
    },
    {
      "question": "Why choose Churchill Institute?",
      "answer": "Excellent reputation and location"
    }
  ]
}
```

---

### Step 12: Document Upload Status

**Endpoint:** `GET /applications/{application_id}/steps/12/documents`

**Response (200 OK):**
```json
{
  "required_documents": [
    {
      "document_type": "passport",
      "display_name": "Passport Copy",
      "is_uploaded": true,
      "uploaded_at": "2025-11-17T10:00:00Z"
    },
    {
      "document_type": "academic_transcript",
      "display_name": "Academic Transcript",
      "is_uploaded": false,
      "uploaded_at": null
    },
    {
      "document_type": "english_proficiency",
      "display_name": "English Test Results",
      "is_uploaded": true,
      "uploaded_at": "2025-11-17T10:15:00Z"
    }
  ],
  "all_uploaded": false,
  "completion_percentage": 67
}
```

**Note:** Step 12 is **GET only** - documents are uploaded via separate document endpoints (to be implemented).

---

## Progress Tracking

### Understanding Completion Percentage

The API automatically calculates progress based on completed steps:

```javascript
// Each step completed adds ~8.33% (12 steps = 100%)
const progressPerStep = 100 / 12; // ≈ 8.33%
```

**After completing step 1:**
```json
{
  "completion_percentage": 8,
  "next_step": "emergency_contact",
  "can_submit": false
}
```

**After completing all steps:**
```json
{
  "completion_percentage": 100,
  "next_step": null,
  "can_submit": true
}
```

### Building a Progress Indicator

```typescript
interface ProgressInfo {
  completionPercentage: number;
  nextStep: string | null;
  canSubmit: boolean;
  completedSteps: string[];
}

// Example UI component
function ProgressBar({ progress }: { progress: ProgressInfo }) {
  return (
    <div>
      <div className="progress-bar" style={{ width: `${progress.completionPercentage}%` }}>
        {progress.completionPercentage}%
      </div>
      {progress.nextStep && (
        <p>Next: {formatStepName(progress.nextStep)}</p>
      )}
      {progress.canSubmit && (
        <button>Submit Application</button>
      )}
    </div>
  );
}
```

---

## Error Handling

### Common HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Continue |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Login required or token expired |
| 403 | Forbidden | Permission denied (e.g., student trying to edit) |
| 404 | Not Found | Application or resource doesn't exist |
| 422 | Validation Error | Fix validation errors in request |
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

### Frontend Error Handling Example

```typescript
async function updateStep(applicationId: string, stepData: any) {
  try {
    const response = await fetch(
      `/api/v1/applications/${applicationId}/steps/1/personal-details`,
      {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(stepData)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      
      switch (response.status) {
        case 401:
          // Token expired - redirect to login
          redirectToLogin();
          break;
        case 403:
          // Permission denied
          showError('You do not have permission to edit this application');
          break;
        case 422:
          // Validation error
          showValidationErrors(error.detail);
          break;
        default:
          showError('An error occurred. Please try again.');
      }
      
      return null;
    }

    return await response.json();
  } catch (err) {
    console.error('Network error:', err);
    showError('Network error. Please check your connection.');
    return null;
  }
}
```

---

## Request/Response Examples

### Complete Flow: Creating and Filling Application

#### 1. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "agent@agency.com",
    "password": "password123"
  }'
```

#### 2. Create Application
```bash
curl -X POST http://localhost:8000/api/v1/applications \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_profile_id": "student-uuid",
    "course_offering_id": "course-uuid"
  }'
```

#### 3. Fill Step 1
```bash
curl -X PATCH http://localhost:8000/api/v1/applications/APP_UUID/steps/1/personal-details \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "given_name": "John",
    "family_name": "Smith",
    "date_of_birth": "2000-01-15",
    "gender": "Male",
    "email": "john@example.com",
    "phone": "+61412345678",
    "street_address": "123 Main St",
    "suburb": "Sydney",
    "state": "NSW",
    "postcode": "2000",
    "country": "Australia",
    "passport_number": "N1234567",
    "nationality": "Australian",
    "country_of_birth": "Australia"
  }'
```

#### 4. Get Progress
```bash
curl -X GET http://localhost:8000/api/v1/applications/APP_UUID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Frontend Implementation Guide

### React Hook Example

```typescript
// hooks/useApplicationStep.ts
import { useState } from 'react';

interface StepUpdateResponse {
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
  ): Promise<StepUpdateResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/applications/${applicationId}/steps/${stepNumber}/${stepName}`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update step');
      }

      const result = await response.json();
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
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
      console.log('Progress:', result.completion_percentage);
      console.log('Next step:', result.next_step);
      
      // Navigate to next step if available
      if (result.next_step) {
        navigateToStep(result.next_step);
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

function useAutoSave(
  applicationId: string,
  stepNumber: number,
  stepName: string,
  formData: any
) {
  const { updateStep } = useApplicationStep(applicationId);
  
  // Create debounced save function
  const debouncedSave = useRef(
    debounce(async (data: any) => {
      await updateStep(stepNumber, stepName, data);
      console.log('Auto-saved');
    }, 2000) // Save 2 seconds after user stops typing
  ).current;

  // Auto-save when formData changes
  useEffect(() => {
    if (formData.given_name) { // Only save if form has data
      debouncedSave(formData);
    }
  }, [formData, debouncedSave]);

  // Cleanup
  useEffect(() => {
    return () => {
      debouncedSave.cancel();
    };
  }, [debouncedSave]);
}
```

---

## Testing with Mock Data

### Mock Service Worker (MSW) Setup

```typescript
// mocks/handlers.ts
import { rest } from 'msw';

export const handlers = [
  // Login
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-token',
        user: {
          id: 'user-123',
          email: 'agent@agency.com',
          role: 'AGENT'
        }
      })
    );
  }),

  // Create application
  rest.post('/api/v1/applications', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        application: {
          id: 'app-123',
          student_profile_id: 'student-123',
          course_offering_id: 'course-123',
          current_stage: 'DRAFT'
        },
        message: 'Application draft created successfully'
      })
    );
  }),

  // Update step 1
  rest.patch('/api/v1/applications/:appId/steps/1/personal-details', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        message: 'Personal details saved successfully',
        step_number: 1,
        step_name: 'personal_details',
        completion_percentage: 8,
        next_step: 'emergency_contact',
        can_submit: false
      })
    );
  }),

  // Update step 2
  rest.patch('/api/v1/applications/:appId/steps/2/emergency-contact', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        message: '1 emergency contact(s) saved',
        step_number: 2,
        step_name: 'emergency_contact',
        completion_percentage: 17,
        next_step: 'health_cover',
        can_submit: false
      })
    );
  }),

  // Add handlers for other steps...
];
```

### Test Data

```typescript
// testData/applications.ts
export const mockPersonalDetails = {
  given_name: "John",
  middle_name: "Robert",
  family_name: "Smith",
  date_of_birth: "2000-01-15",
  gender: "Male",
  email: "john.smith@example.com",
  phone: "+61412345678",
  street_address: "123 Main St",
  suburb: "Sydney",
  state: "NSW",
  postcode: "2000",
  country: "Australia",
  passport_number: "N1234567",
  passport_expiry: "2030-12-31",
  nationality: "Australian",
  country_of_birth: "Australia"
};

export const mockEmergencyContact = {
  contacts: [
    {
      name: "Jane Smith",
      relationship: "Mother",
      phone: "+61412345679",
      email: "jane.smith@example.com",
      is_primary: true
    }
  ]
};

export const mockHealthCover = {
  provider: "Medibank",
  policy_number: "MB123456",
  start_date: "2025-01-01",
  end_date: "2026-01-01",
  coverage_type: "Comprehensive"
};

// ... export mock data for all 12 steps
```

---

## Validation Rules Reference

### Step 1: Personal Details
- ✅ `given_name`: Required, 1-100 characters
- ✅ `family_name`: Required, 1-100 characters
- ✅ `date_of_birth`: Required, YYYY-MM-DD format
- ✅ `email`: Required, valid email format
- ✅ `phone`: Required, valid phone format
- ✅ `street_address`, `suburb`, `state`, `postcode`, `country`: All required
- ✅ `nationality`, `country_of_birth`: Required
- ⚠️ `middle_name`, `passport_expiry`: Optional

### Step 2: Emergency Contact
- ✅ Minimum 1 contact
- ✅ Maximum 5 contacts
- ✅ At least one must have `is_primary: true`
- ⚠️ `email` is optional

### Step 9: USI
- ✅ Exactly 10 characters
- ✅ Letters and numbers only
- ✅ No spaces or special characters

### General Rules
- 📅 All dates: YYYY-MM-DD format
- 📧 Email fields: Valid email format
- 📞 Phone fields: International format recommended (+61...)
- 🔒 **Permissions**: Only AGENT role can edit applications

---

## Quick Reference: All Endpoints

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

---

## Support & Questions

- **API Issues**: Check backend logs or create an issue
- **Validation Errors**: Refer to error messages and this documentation
- **Missing Features**: Document requests and prioritize with team

**Happy coding! 🚀**
