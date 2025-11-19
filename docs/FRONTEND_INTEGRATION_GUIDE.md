# Frontend Integration Guide - Churchill Application Portal

## 🎯 Overview
This guide helps frontend developers integrate with the Churchill Application Portal backend API.

### 🔑 Key Business Rule
**ONLY AGENTS can create and fill applications on behalf of students.**
- Students do NOT have login access to create applications
- Agents act as intermediaries, collecting student information and submitting applications
- All 12 application steps are filled by agents, not students

---

## 🎯 Quick Reference: Which API to Hit?

### Creating & Editing Application Flow

```
1. Agent creates application (empty) 
   → POST /api/v1/applications

2. Agent fills Step 1 (Personal Details)
   → PATCH /api/v1/applications/{id}/steps/1/personal-details

3. Agent fills Step 2 (Emergency Contact)
   → PATCH /api/v1/applications/{id}/steps/2/emergency-contact

4. Agent fills Step 3 (Health Cover)
   → PATCH /api/v1/applications/{id}/steps/3/health-cover

... and so on for all 12 steps ...

12. Agent submits completed application
   → POST /api/v1/applications/{id}/submit
```

### Editing/Resuming Draft

```
1. Load application data
   → GET /api/v1/applications/{id}

2. Agent edits any step (same PATCH endpoints)
   → PATCH /api/v1/applications/{id}/steps/{step_number}/{step_name}

3. Auto-save uses the same PATCH endpoints
```

**Key Point**: Use the **SAME PATCH endpoints** for both initial fill and editing!

---

## 📋 Complete API Endpoint Reference

### Application Lifecycle Endpoints

#### 1️⃣ Create New Application (Empty Draft)
```
POST /api/v1/applications
```
**Request Body**:
```json
{
  "course_offering_id": "uuid-here"
  // student_profile_id is optional - omit for new students
}
```
**Response**: Returns application with `id` - use this ID for all subsequent steps

---

#### 2️⃣ Fill/Edit Application Steps (Use SAME endpoints for create AND edit)

**Step 1: Personal Details**
```
PATCH /api/v1/applications/{application_id}/steps/1/personal-details
```
```json
{
  "given_name": "John",
  "family_name": "Doe",
  "date_of_birth": "1995-06-15",
  "gender": "Male",
  "nationality": "India",
  "passport_number": "AB1234567",
  "passport_expiry": "2030-12-31",
  "passport_country": "India",
  "email": "john.doe@example.com",
  "phone": "+61412345678",
  "address": {
    "street": "123 Main St",
    "city": "Sydney",
    "state": "NSW",
    "postcode": "2000",
    "country": "Australia"
  }
}
```

**Step 2: Emergency Contact**
```
PATCH /api/v1/applications/{application_id}/steps/2/emergency-contact
```
```json
{
  "contacts": [
    {
      "name": "Jane Doe",
      "relationship": "Mother",
      "phone": "+61412345679",
      "email": "jane.doe@example.com",
      "is_primary": true
    }
  ]
}
```

**Step 3: Health Cover (OSHC)**
```
PATCH /api/v1/applications/{application_id}/steps/3/health-cover
```
```json
{
  "provider": "Medibank",
  "policy_number": "OSC123456",
  "start_date": "2025-02-01",
  "end_date": "2027-02-01",
  "coverage_type": "Single"
}
```

**Step 4: Language & Cultural Background**
```
PATCH /api/v1/applications/{application_id}/steps/4/language-cultural
```

**Step 5: Disability Support**
```
PATCH /api/v1/applications/{application_id}/steps/5/disability-support
```

**Step 6: Schooling History**
```
PATCH /api/v1/applications/{application_id}/steps/6/schooling-history
```

**Step 7: Previous Qualifications**
```
PATCH /api/v1/applications/{application_id}/steps/7/qualifications
```

**Step 8: Employment History**
```
PATCH /api/v1/applications/{application_id}/steps/8/employment-history
```

**Step 9: USI (Unique Student Identifier)**
```
PATCH /api/v1/applications/{application_id}/steps/9/usi
```

**Step 10: Additional Services**
```
PATCH /api/v1/applications/{application_id}/steps/10/additional-services
```

**Step 11: Survey**
```
PATCH /api/v1/applications/{application_id}/steps/11/survey
```

**Step 12: View Document Status**
```
GET /api/v1/applications/{application_id}/steps/12/documents
```

---

#### 3️⃣ Submit Application
```
POST /api/v1/applications/{application_id}/submit
```
**Request Body**:
```json
{
  "confirm_accuracy": true
}
```

---

#### 4️⃣ Get Application (for editing/viewing)
```
GET /api/v1/applications/{application_id}
```
**Response**: Returns full application with all step data in dedicated JSONB fields

---

#### 5️⃣ List Applications
```
GET /api/v1/applications?limit=50&offset=0&stage=DRAFT
```

---

## 📍 Environment Setup

### Backend URLs
```
Development: http://localhost:8000
API Base: http://localhost:8000/api/v1
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/api/v1/openapi.json

### CORS Configuration
Backend allows these origins:
- `http://localhost:3000` (Next.js/React default)
- `http://localhost:5173` (Vite default)
- `http://localhost:5174` (Vite alternative)

---

---

## 💡 Practical Example: Creating & Editing Application

### Complete Flow

```javascript
// ============================================================
// STEP 1: Create Empty Application
// ============================================================
const createApplication = async (courseOfferingId) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/applications', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      course_offering_id: courseOfferingId
      // student_profile_id omitted - will be created at enrollment
    })
  });
  
  const result = await response.json();
  const applicationId = result.application.id; // Save this!
  
  // Redirect to form
  navigate(`/applications/${applicationId}/steps`);
};

// ============================================================
// STEP 2: Fill/Edit Step 1 (Personal Details)
// Same endpoint for CREATE and EDIT!
// ============================================================
const savePersonalDetails = async (applicationId, formData) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications/${applicationId}/steps/1/personal-details`,
    {
      method: 'PATCH', // Always PATCH for steps
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        given_name: formData.given_name,
        family_name: formData.family_name,
        date_of_birth: formData.date_of_birth,
        gender: formData.gender,
        nationality: formData.nationality,
        passport_number: formData.passport_number,
        passport_expiry: formData.passport_expiry,
        passport_country: formData.passport_country,
        email: formData.email,
        phone: formData.phone,
        address: formData.address
      })
    }
  );
  
  const result = await response.json();
  // result.completion_percentage - show progress
  // result.next_step - show which step to go to next
  return result;
};

// ============================================================
// STEP 3: Load Application for Editing
// ============================================================
const loadApplicationForEditing = async (applicationId) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications/${applicationId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const application = await response.json();
  
  // Extract data from dedicated JSONB columns
  const personalDetails = application.personal_details || {};
  const emergencyContacts = application.emergency_contacts || [];
  const healthCover = application.health_cover_policy || {};
  
  // Pre-fill forms with this data
  return {
    personalDetails,
    emergencyContacts,
    healthCover,
    completedSteps: application.form_metadata?.completed_sections || []
  };
};

// ============================================================
// STEP 4: Edit Existing Step (Same as filling!)
// ============================================================
const editPersonalDetails = async (applicationId, updatedData) => {
  // Uses SAME endpoint as initial fill
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications/${applicationId}/steps/1/personal-details`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updatedData) // Send updated data
    }
  );
  
  return await response.json();
};

// ============================================================
// STEP 5: Auto-Save While Editing
// ============================================================
const useAutoSave = (applicationId, stepEndpoint, formData) => {
  useEffect(() => {
    // Auto-save every 30 seconds
    const timer = setInterval(async () => {
      if (Object.values(formData).some(val => val)) { // Has any data
        const token = localStorage.getItem('access_token');
        
        await fetch(
          `http://localhost:8000/api/v1/applications/${applicationId}${stepEndpoint}`,
          {
            method: 'PATCH',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
          }
        );
        // Silent save - no notification
      }
    }, 30000);
    
    return () => clearInterval(timer);
  }, [formData]);
};

// ============================================================
// STEP 6: Submit Final Application
// ============================================================
const submitApplication = async (applicationId) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications/${applicationId}/submit`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        confirm_accuracy: true
      })
    }
  );
  
  if (response.ok) {
    toast.success('🎉 Application submitted successfully!');
    navigate('/applications');
  }
};
```

### Key Takeaways:

1. **Create**: `POST /api/v1/applications` → Get `application_id`
2. **Fill ANY Step**: `PATCH /api/v1/applications/{id}/steps/{n}/{name}`
3. **Edit ANY Step**: **Same PATCH endpoint** - just send updated data
4. **Load for Editing**: `GET /api/v1/applications/{id}` → Extract from dedicated JSONB fields
5. **Submit**: `POST /api/v1/applications/{id}/submit`

**There's NO separate "edit" endpoint - editing uses the same PATCH endpoints as initial filling!**

---

## 📊 Visual Flow: Application Form Filling & Editing

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT CREATES APPLICATION                                    │
├─────────────────────────────────────────────────────────────┤
│ POST /api/v1/applications                                    │
│ { course_offering_id: "uuid" }                               │
│                                                              │
│ ← Returns: { id: "app-uuid-123", current_stage: "DRAFT" }   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT FILLS STEP 1                                           │
├─────────────────────────────────────────────────────────────┤
│ PATCH /api/v1/applications/app-uuid-123/steps/1/personal... │
│ { given_name: "John", family_name: "Doe", ... }             │
│                                                              │
│ ← Returns: { completion_percentage: 8, next_step: "..." }   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT FILLS STEPS 2-11 (same pattern)                       │
├─────────────────────────────────────────────────────────────┤
│ Each step: PATCH /api/v1/applications/{id}/steps/{n}/...    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ AUTO-SAVE (every 30 seconds)                                 │
├─────────────────────────────────────────────────────────────┤
│ Same PATCH endpoints - silent background saves              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT COMES BACK TO EDIT                                     │
├─────────────────────────────────────────────────────────────┤
│ GET /api/v1/applications/app-uuid-123                        │
│ ← Returns full data including form_metadata                 │
│                                                              │
│ Frontend pre-fills forms with returned data                 │
│                                                              │
│ Agent changes Step 1:                                        │
│ PATCH /api/v1/applications/app-uuid-123/steps/1/personal... │
│ { given_name: "Jane", ... } ← SAME endpoint!                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT SUBMITS APPLICATION                                    │
├─────────────────────────────────────────────────────────────┤
│ POST /api/v1/applications/app-uuid-123/submit               │
│ { confirm_accuracy: true }                                  │
│                                                              │
│ Application stage: DRAFT → SUBMITTED                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Storage Structure

```json
{
  "id": "app-uuid-123",
  "course_offering_id": "course-uuid",
  "current_stage": "DRAFT",
  "personal_details": { 
    "given_name": "John",
    "family_name": "Doe",
    ...
  },
  "emergency_contacts": [...],
  "health_cover_policy": {...},
  "language_cultural_data": {...},
  "disability_support": {...},
  "form_metadata": {
    "completed_sections": ["personal_details", "emergency_contact"],
    "version": "3.1",
    "last_saved_at": "2025-11-19T10:30:00"
  },
  "usi": "ABC123XYZ",
  ...
}
```

When you hit `GET /api/v1/applications/{id}`, you get this entire structure back.
Extract the data from dedicated JSONB columns, pre-fill your forms, and use the same PATCH endpoints to update!

---

## 🔐 Authentication Flow

### 1. Login Process

**Endpoint**: `POST /api/v1/auth/login`

**Request**:
```javascript
const formData = new URLSearchParams();
formData.append('username', email); // Note: use 'username' field for email
formData.append('password', password);

const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: formData.toString(),
});

const data = await response.json();
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": "uuid",
  "email": "agent@test.com",
  "role": "agent",
  "mfa_required": false
}
```

**Store Tokens**:
```javascript
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
localStorage.setItem('user', JSON.stringify({
  id: data.user_id,
  email: data.email,
  role: data.role
}));
```

### 2. Authenticated Requests

**Include token in all API calls**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/students/me', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json',
  },
});
```

### 3. Token Refresh

**When access token expires (401 response)**:
```javascript
const refreshToken = async () => {
  const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token')
    }),
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data.access_token;
};
```

### 4. Logout
```javascript
const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
};
```

---

## 🎭 User Roles & Dashboards

### Role-Based Routing
```javascript
const user = JSON.parse(localStorage.getItem('user'));

switch(user.role) {
  case 'STUDENT':
    navigate('/student/dashboard');
    break;
  case 'AGENT':
    navigate('/agent/dashboard');
    break;
  case 'STAFF':
    navigate('/staff/dashboard');
    break;
  case 'ADMIN':
    navigate('/admin/dashboard');
    break;
}
```

### Protected Routes Example (React Router)
```javascript
const ProtectedRoute = ({ allowedRoles, children }) => {
  const user = JSON.parse(localStorage.getItem('user'));
  const token = localStorage.getItem('access_token');
  
  if (!token) {
    return <Navigate to="/login" />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
};

// Usage
<Route path="/agent/*" element={
  <ProtectedRoute allowedRoles={['AGENT']}>
    <AgentDashboard />
  </ProtectedRoute>
} />
```

---

## 🤝 Agent Portal - Key Features

### 1. Agent Dashboard

**Get Agent Profile**:
```javascript
GET /api/v1/students/me
Authorization: Bearer {token}
```

**Response**:
```json
{
  "user_id": "uuid",
  "email": "agent@test.com",
  "role": "agent",
  "agent_profile": {
    "agency_name": "Global Education Services",
    "phone": "+61 2 1234 5678",
    "commission_rate": 15.00
  }
}
```

### 2. Agent - Submit Student Application

**Endpoint**: `POST /api/v1/applications`

**Request Body**:
```json
{
  "student_id": "student-uuid",
  "course_id": "course-uuid",
  "intake": "Feb 2025",
  "personal_data": {
    "given_name": "John",
    "family_name": "Doe",
    "date_of_birth": "1995-01-15",
    "gender": "Male",
    "nationality": "India",
    "passport_number": "AB1234567",
    "passport_expiry": "2028-12-31"
  },
  "contact_data": {
    "email": "john.doe@email.com",
    "phone": "+91 98765 43210",
    "address": {
      "street": "123 Main St",
      "city": "Mumbai",
      "state": "Maharashtra",
      "postcode": "400001",
      "country": "India"
    }
  },
  "emergency_contacts": [
    {
      "name": "Jane Doe",
      "relationship": "Mother",
      "phone": "+91 98765 43211"
    }
  ],
  "english_proficiency": {
    "test_type": "IELTS",
    "overall_score": 7.0,
    "test_date": "2024-10-15"
  }
}
```

### 3. Agent - View Applications

**List All Applications (for agent's students)**:
```javascript
// Fetch all applications with pagination
const fetchApplications = async (page = 1, limit = 20) => {
  const offset = (page - 1) * limit;
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications?limit=${limit}&offset=${offset}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  const data = await response.json();
  return data;
};

// Usage in component
const ApplicationsList = () => {
  const [applications, setApplications] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadApplications = async () => {
      const data = await fetchApplications(1, 20);
      setApplications(data.items);
      setTotal(data.total);
      setLoading(false);
    };
    loadApplications();
  }, []);

  return (
    <div>
      <h2>Applications ({total})</h2>
      {applications.map(app => (
        <ApplicationCard key={app.id} application={app} />
      ))}
    </div>
  );
};
```

**Response**:
```json
{
  "total": 15,
  "items": [
    {
      "id": "app-uuid",
      "student_id": "student-uuid",
      "course_id": "course-uuid",
      "stage": "SUBMITTED",
      "created_at": "2025-11-19T10:30:00Z",
      "updated_at": "2025-11-19T11:00:00Z",
      "student_name": "John Doe",
      "course_name": "Certificate IV in Business",
      "intake": "Feb 2025",
      "completed_steps": [1, 2, 3, 4, 5]
    }
  ]
}
```

**Get Single Application (with full details)**:
```javascript
const getApplication = async (applicationId) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications/${applicationId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (response.ok) {
    const application = await response.json();
    return application;
  } else {
    throw new Error('Failed to fetch application');
  }
};

// Usage
const ApplicationDetails = ({ applicationId }) => {
  const [application, setApplication] = useState(null);

  useEffect(() => {
    getApplication(applicationId).then(setApplication);
  }, [applicationId]);

  if (!application) return <div>Loading...</div>;

  return (
    <div>
      <h1>Application #{application.id.slice(0, 8)}</h1>
      <p>Student: {application.personal_data?.given_name} {application.personal_data?.family_name}</p>
      <p>Stage: {application.stage}</p>
      <p>Progress: {application.completed_steps?.length || 0} of 12 steps</p>
      
      {/* Display all saved data */}
      <pre>{JSON.stringify(application, null, 2)}</pre>
    </div>
  );
};
```

**Single Application Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "student_id": "student-uuid",
  "course_id": "course-uuid",
  "stage": "DRAFT",
  "intake": "Feb 2025",
  "completed_steps": [1, 2, 3],
  "created_at": "2025-11-19T10:00:00Z",
  "updated_at": "2025-11-19T14:30:00Z",
  
  "personal_data": {
    "given_name": "John",
    "family_name": "Doe",
    "date_of_birth": "1995-01-15",
    "gender": "Male",
    "nationality": "India",
    "passport_number": "AB1234567",
    "passport_expiry": "2028-12-31",
    "passport_country": "India"
  },
  
  "emergency_contacts": [
    {
      "name": "Jane Doe",
      "relationship": "Mother",
      "phone": "+91 98765 43210",
      "email": "jane@example.com"
    }
  ],
  
  "health_cover": {
    "has_oshc": true,
    "provider": "Medibank",
    "policy_number": "MB123456"
  },
  
  "language_cultural": {
    "english_first_language": false,
    "other_languages": ["Hindi", "Punjabi"],
    "aboriginal_torres_strait": false
  },
  
  "education_history": [...],
  "employment_history": [...],
  "usi": {...},
  
  "submitted_at": null,
  "assigned_staff_id": null
}
```

**Filter Applications by Stage**:
```javascript
const fetchApplicationsByStage = async (stage) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `http://localhost:8000/api/v1/applications?stage=${stage}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  return await response.json();
};

// Usage: Get all submitted applications
const submittedApps = await fetchApplicationsByStage('SUBMITTED');
const draftApps = await fetchApplicationsByStage('DRAFT');
```

### 4. Agent - Upload Documents

**Step 1: Get Document Types**:
```javascript
GET /api/v1/documents/types
```

**Step 2: Upload Document**:
```javascript
const formData = new FormData();
formData.append('file', selectedFile);
formData.append('application_id', applicationId);
formData.append('document_type_id', documentTypeId);

const response = await fetch('http://localhost:8000/api/v1/documents/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});
```

---

## 📱 UI Pages to Build

### 1. Agent Portal Structure

```
/agent
├── /login                    # Agent login page
├── /dashboard                # Overview (applications, stats)
├── /students                 # List of students
│   ├── /new                  # Add new student
│   └── /:id                  # Student details
├── /applications             # All applications
│   ├── /new                  # Create new application
│   ├── /:id                  # Application details
│   └── /:id/documents        # Upload documents
└── /profile                  # Agent profile settings
```

### 2. Application Workflow Stages

```javascript
const APPLICATION_STAGES = {
  DRAFT: { label: 'Draft', color: 'gray', icon: '📝' },
  SUBMITTED: { label: 'Submitted', color: 'blue', icon: '📨' },
  STAFF_REVIEW: { label: 'Under Review', color: 'yellow', icon: '👀' },
  AWAITING_DOCUMENTS: { label: 'Awaiting Documents', color: 'orange', icon: '📄' },
  GS_ASSESSMENT: { label: 'GS Assessment', color: 'purple', icon: '🔍' },
  OFFER_GENERATED: { label: 'Offer Generated', color: 'green', icon: '🎉' },
  OFFER_ACCEPTED: { label: 'Offer Accepted', color: 'teal', icon: '✅' },
  ENROLLED: { label: 'Enrolled', color: 'success', icon: '🎓' },
  REJECTED: { label: 'Rejected', color: 'red', icon: '❌' },
  WITHDRAWN: { label: 'Withdrawn', color: 'gray', icon: '🚫' }
};
```

### 3. Multi-Step Application Form (Complete Implementation)

#### Step-by-Step Architecture

```jsx
// 1. APPLICATION CONTAINER - Main orchestrator
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const ApplicationWizard = () => {
  const { applicationId } = useParams();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);

  const TOTAL_STEPS = 12;
  const token = localStorage.getItem('access_token');

  // Load existing application data
  useEffect(() => {
    const loadApplication = async () => {
      if (applicationId) {
        // Load existing draft - GET /api/v1/applications/{id}
        const token = localStorage.getItem('access_token');
        const response = await fetch(
          `http://localhost:8000/api/v1/applications/${applicationId}`,
          {
            headers: { 'Authorization': `Bearer ${token}` }
          }
        );
        const data = await response.json();
        setApplication(data);
        
        // Resume from last incomplete step
        const lastStep = Math.max(...(data.completed_steps || [0])) + 1;
        setCurrentStep(Math.min(lastStep, TOTAL_STEPS));
      } else {
        // Agent creates new draft - POST /api/v1/applications
        // Note: Only agents can create applications on behalf of students
        // student_profile_id is OPTIONAL - will be created when application reaches ENROLLED stage
        const token = localStorage.getItem('access_token');
        const response = await fetch('http://localhost:8000/api/v1/applications', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            course_offering_id: 'course-uuid-from-selection',
            // student_profile_id is optional - omit it for new students
            // agent_profile_id is optional - auto-filled from JWT token
          })
        });
        const newApp = await response.json();
        setApplication(newApp);
        navigate(`/agent/applications/${newApp.id}/steps`, { replace: true });
      }
      setLoading(false);
    };

    loadApplication();
  }, [applicationId]);

  const goToStep = (step) => {
    setCurrentStep(step);
  };

  const handleStepComplete = async (stepData) => {
    // Step completed, move to next
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep(currentStep + 1);
    }
    // Refresh application data to update progress
    const response = await fetch(
      `http://localhost:8000/api/v1/applications/${applicationId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const updated = await response.json();
    setApplication(updated);
  };

  if (loading) return <div>Loading application...</div>;

  return (
    <div className="application-wizard">
      {/* Progress Indicator */}
      <ApplicationProgress 
        currentStep={currentStep}
        completedSteps={application.completed_steps || []}
        totalSteps={TOTAL_STEPS}
      />

      {/* Step Navigation */}
      <StepNavigation 
        currentStep={currentStep}
        completedSteps={application.completed_steps || []}
        onStepClick={goToStep}
      />

      {/* Current Step Content */}
      <div className="step-content">
        {currentStep === 1 && (
          <PersonalDetailsStep 
            applicationId={application.id}
            initialData={application.personal_data}
            onComplete={handleStepComplete}
          />
        )}
        {currentStep === 2 && (
          <EmergencyContactStep 
            applicationId={application.id}
            initialData={application.emergency_contacts}
            onComplete={handleStepComplete}
          />
        )}
        {currentStep === 3 && (
          <HealthCoverStep 
            applicationId={application.id}
            initialData={application.health_cover}
            onComplete={handleStepComplete}
          />
        )}
        {/* ... other steps 4-11 ... */}
        {currentStep === 12 && (
          <DocumentsStep 
            applicationId={application.id}
            onComplete={handleStepComplete}
          />
        )}
      </div>

      {/* Final Submit */}
      {application.completed_steps?.length === TOTAL_STEPS && (
        <FinalSubmitButton applicationId={application.id} />
      )}
    </div>
  );
};
```

#### Individual Step Component Pattern

```jsx
// 2. STEP 1 - PERSONAL DETAILS
import React, { useState, useEffect } from 'react';

const PersonalDetailsStep = ({ applicationId, initialData, onComplete }) => {
  const [formData, setFormData] = useState({
    given_name: '',
    family_name: '',
    date_of_birth: '',
    gender: '',
    nationality: '',
    passport_number: '',
    passport_expiry: '',
    passport_country: '',
    ...initialData // Pre-fill if editing
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [autoSaveTimer, setAutoSaveTimer] = useState(null);

  // Auto-save every 30 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      if (formData.given_name || formData.family_name) {
        saveStep(false); // Silent save
      }
    }, 30000);

    return () => clearInterval(timer);
  }, [formData]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: null })); // Clear error
  };

  const saveStep = async (showNotification = true) => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/v1/applications/${applicationId}/steps/1/personal-details`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData)
        }
      );

      if (response.ok) {
        if (showNotification) {
          toast.success('✅ Personal details saved');
        }
        return true;
      } else {
        const error = await response.json();
        setErrors(error.detail || {});
        if (showNotification) {
          toast.error('❌ Please fix the errors');
        }
        return false;
      }
    } catch (error) {
      console.error('Save failed:', error);
      if (showNotification) {
        toast.error('Network error. Please try again.');
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndContinue = async () => {
    const success = await saveStep(true);
    if (success) {
      onComplete(formData); // Move to next step
    }
  };

  return (
    <div className="step-form">
      <h2>Step 1: Personal Details</h2>
      
      <div className="form-grid">
        <div className="form-group">
          <label>Given Name *</label>
          <input 
            type="text"
            value={formData.given_name}
            onChange={(e) => handleChange('given_name', e.target.value)}
            className={errors.given_name ? 'error' : ''}
          />
          {errors.given_name && (
            <span className="error-text">{errors.given_name}</span>
          )}
        </div>

        <div className="form-group">
          <label>Family Name *</label>
          <input 
            type="text"
            value={formData.family_name}
            onChange={(e) => handleChange('family_name', e.target.value)}
            className={errors.family_name ? 'error' : ''}
          />
          {errors.family_name && (
            <span className="error-text">{errors.family_name}</span>
          )}
        </div>

        <div className="form-group">
          <label>Date of Birth *</label>
          <input 
            type="date"
            value={formData.date_of_birth}
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            max={new Date().toISOString().split('T')[0]}
          />
          {errors.date_of_birth && (
            <span className="error-text">{errors.date_of_birth}</span>
          )}
        </div>

        <div className="form-group">
          <label>Gender *</label>
          <select 
            value={formData.gender}
            onChange={(e) => handleChange('gender', e.target.value)}
          >
            <option value="">Select...</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
            <option value="Prefer not to say">Prefer not to say</option>
          </select>
        </div>

        <div className="form-group">
          <label>Nationality *</label>
          <input 
            type="text"
            value={formData.nationality}
            onChange={(e) => handleChange('nationality', e.target.value)}
            placeholder="e.g., Nepalese, Chinese"
          />
        </div>

        <div className="form-group">
          <label>Passport Number *</label>
          <input 
            type="text"
            value={formData.passport_number}
            onChange={(e) => handleChange('passport_number', e.target.value)}
            placeholder="AB1234567"
          />
        </div>

        <div className="form-group">
          <label>Passport Expiry Date *</label>
          <input 
            type="date"
            value={formData.passport_expiry}
            onChange={(e) => handleChange('passport_expiry', e.target.value)}
            min={new Date().toISOString().split('T')[0]}
          />
        </div>

        <div className="form-group">
          <label>Passport Issuing Country *</label>
          <input 
            type="text"
            value={formData.passport_country}
            onChange={(e) => handleChange('passport_country', e.target.value)}
          />
        </div>
      </div>

      <div className="step-actions">
        <button 
          onClick={() => saveStep(true)}
          disabled={saving}
          className="btn-secondary"
        >
          {saving ? 'Saving...' : '💾 Save Draft'}
        </button>

        <button 
          onClick={handleSaveAndContinue}
          disabled={saving}
          className="btn-primary"
        >
          Save & Continue →
        </button>
      </div>

      {saving && <div className="auto-save-indicator">💾 Saving...</div>}
    </div>
  );
};
```

#### Progress Indicator Component

```jsx
// 3. PROGRESS INDICATOR
const ApplicationProgress = ({ currentStep, completedSteps, totalSteps }) => {
  const progress = (completedSteps.length / totalSteps) * 100;

  return (
    <div className="progress-section">
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progress}%` }}></div>
      </div>
      <p className="progress-text">
        Step {currentStep} of {totalSteps} • {completedSteps.length} completed ({Math.round(progress)}%)
      </p>
    </div>
  );
};
```

#### Step Navigation Sidebar

```jsx
// 4. STEP NAVIGATION
const StepNavigation = ({ currentStep, completedSteps, onStepClick }) => {
  const steps = [
    { id: 1, title: 'Personal Details', icon: '👤' },
    { id: 2, title: 'Emergency Contact', icon: '🚨' },
    { id: 3, title: 'Health Cover', icon: '🏥' },
    { id: 4, title: 'Language & Cultural', icon: '🌍' },
    { id: 5, title: 'Disability Support', icon: '♿' },
    { id: 6, title: 'Schooling History', icon: '🏫' },
    { id: 7, title: 'Qualifications', icon: '🎓' },
    { id: 8, title: 'Employment History', icon: '💼' },
    { id: 9, title: 'USI', icon: '🆔' },
    { id: 10, title: 'Additional Services', icon: '➕' },
    { id: 11, title: 'Survey', icon: '📋' },
    { id: 12, title: 'Documents', icon: '📄' }
  ];

  return (
    <div className="step-navigation">
      {steps.map(step => {
        const isCompleted = completedSteps.includes(step.id);
        const isCurrent = currentStep === step.id;
        const isAccessible = step.id <= currentStep;

        return (
          <div
            key={step.id}
            className={`step-item ${isCurrent ? 'current' : ''} ${isCompleted ? 'completed' : ''} ${!isAccessible ? 'disabled' : ''}`}
            onClick={() => isAccessible && onStepClick(step.id)}
          >
            <div className="step-number">
              {isCompleted ? '✓' : step.id}
            </div>
            <div className="step-info">
              <span className="step-icon">{step.icon}</span>
              <span className="step-title">{step.title}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
```

#### Final Submit

```jsx
// 5. FINAL SUBMIT BUTTON
const FinalSubmitButton = ({ applicationId }) => {
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleFinalSubmit = async () => {
    if (!confirm('Submit application? You cannot edit after submission.')) {
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:8000/api/v1/applications/${applicationId}/submit`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.ok) {
        toast.success('🎉 Application submitted successfully!');
        navigate('/agent/applications');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Submission failed');
      }
    } catch (error) {
      toast.error('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="final-submit-section">
      <h3>✅ All steps completed!</h3>
      <p>Review your application and submit when ready.</p>
      <button 
        onClick={handleFinalSubmit}
        disabled={submitting}
        className="btn-success btn-large"
      >
        {submitting ? 'Submitting...' : '🚀 Submit Application'}
      </button>
    </div>
  );
};
```

#### Other Step Examples

```jsx
// 6. STEP 2 - EMERGENCY CONTACT
const EmergencyContactStep = ({ applicationId, initialData, onComplete }) => {
  const [contacts, setContacts] = useState(initialData || [
    { name: '', relationship: '', phone: '', email: '' }
  ]);

  const addContact = () => {
    setContacts([...contacts, { name: '', relationship: '', phone: '', email: '' }]);
  };

  const removeContact = (index) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  const updateContact = (index, field, value) => {
    const updated = [...contacts];
    updated[index][field] = value;
    setContacts(updated);
  };

  const saveStep = async () => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(
      `http://localhost:8000/api/v1/applications/${applicationId}/steps/2/emergency-contact`,
      {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ emergency_contacts: contacts })
      }
    );

    if (response.ok) {
      toast.success('✅ Emergency contacts saved');
      onComplete({ emergency_contacts: contacts });
      return true;
    }
    return false;
  };

  return (
    <div className="step-form">
      <h2>Step 2: Emergency Contacts</h2>
      <p>Provide at least one emergency contact</p>

      {contacts.map((contact, index) => (
        <div key={index} className="emergency-contact-card">
          <h4>Contact {index + 1}</h4>
          
          <div className="form-grid">
            <input 
              type="text"
              placeholder="Full Name *"
              value={contact.name}
              onChange={(e) => updateContact(index, 'name', e.target.value)}
            />
            
            <input 
              type="text"
              placeholder="Relationship *"
              value={contact.relationship}
              onChange={(e) => updateContact(index, 'relationship', e.target.value)}
            />
            
            <input 
              type="tel"
              placeholder="Phone Number *"
              value={contact.phone}
              onChange={(e) => updateContact(index, 'phone', e.target.value)}
            />
            
            <input 
              type="email"
              placeholder="Email (optional)"
              value={contact.email}
              onChange={(e) => updateContact(index, 'email', e.target.value)}
            />
          </div>

          {contacts.length > 1 && (
            <button 
              onClick={() => removeContact(index)}
              className="btn-danger btn-small"
            >
              Remove Contact
            </button>
          )}
        </div>
      ))}

      <button onClick={addContact} className="btn-secondary">
        ➕ Add Another Contact
      </button>

      <div className="step-actions">
        <button onClick={saveStep} className="btn-primary">
          Save & Continue →
        </button>
      </div>
    </div>
  );
};

// 7. STEP 9 - USI (Unique Student Identifier)
const USIStep = ({ applicationId, initialData, onComplete }) => {
  const [usiData, setUsiData] = useState({
    has_usi: initialData?.has_usi || false,
    usi_number: initialData?.usi_number || '',
    permission_to_verify: initialData?.permission_to_verify || false
  });

  const saveStep = async () => {
    const token = localStorage.getItem('access_token');
    const response = await fetch(
      `http://localhost:8000/api/v1/applications/${applicationId}/steps/9/usi`,
      {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(usiData)
      }
    );

    if (response.ok) {
      toast.success('✅ USI information saved');
      onComplete(usiData);
    }
  };

  return (
    <div className="step-form">
      <h2>Step 9: Unique Student Identifier (USI)</h2>
      
      <div className="info-box">
        <p>A USI is required to study nationally recognized training in Australia.</p>
        <a href="https://www.usi.gov.au" target="_blank">Get your USI here</a>
      </div>

      <div className="form-group">
        <label>
          <input 
            type="checkbox"
            checked={usiData.has_usi}
            onChange={(e) => setUsiData({...usiData, has_usi: e.target.checked})}
          />
          I have a USI
        </label>
      </div>

      {usiData.has_usi && (
        <div className="form-group">
          <label>USI Number *</label>
          <input 
            type="text"
            value={usiData.usi_number}
            onChange={(e) => setUsiData({...usiData, usi_number: e.target.value})}
            placeholder="10 characters (letters and numbers)"
            maxLength={10}
          />
        </div>
      )}

      <div className="form-group">
        <label>
          <input 
            type="checkbox"
            checked={usiData.permission_to_verify}
            onChange={(e) => setUsiData({...usiData, permission_to_verify: e.target.checked})}
            required
          />
          I give permission to verify my USI
        </label>
      </div>

      <div className="step-actions">
        <button onClick={saveStep} className="btn-primary">
          Save & Continue →
        </button>
      </div>
    </div>
  );
};
```

#### Styling Example

```css
/* Application Wizard Styles */
.application-wizard {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.progress-section {
  grid-column: 1 / -1;
  margin-bottom: 1rem;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.step-navigation {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.step-item.current {
  background: #f0f4ff;
  border-color: #667eea;
}

.step-item.completed {
  background: #f0fdf4;
}

.step-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  font-weight: bold;
}

.step-item.completed .step-number {
  background: #48bb78;
  color: white;
}

.step-item.current .step-number {
  background: #667eea;
  color: white;
}

.step-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #2d3748;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
}

.form-group input.error {
  border-color: #f56565;
}

.error-text {
  color: #f56565;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.step-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e2e8f0;
}

.auto-save-indicator {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  background: #667eea;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
```

---

### 4. Document Upload Component

```jsx
import React, { useState } from 'react';

const DocumentUpload = ({ applicationId, documentTypes }) => {
  const [file, setFile] = useState(null);
  const [selectedType, setSelectedType] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!file || !selectedType) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('application_id', applicationId);
    formData.append('document_type_id', selectedType);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/v1/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        alert('Document uploaded successfully');
        setFile(null);
        setSelectedType('');
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-upload">
      <select 
        value={selectedType} 
        onChange={(e) => setSelectedType(e.target.value)}
      >
        <option value="">Select Document Type</option>
        {documentTypes.map(type => (
          <option key={type.id} value={type.id}>
            {type.name} {type.is_mandatory ? '*' : ''}
          </option>
        ))}
      </select>

      <input 
        type="file" 
        onChange={(e) => setFile(e.target.files[0])}
        accept=".pdf,.jpg,.jpeg,.png"
      />

      <button 
        onClick={handleUpload} 
        disabled={!file || !selectedType || uploading}
      >
        {uploading ? 'Uploading...' : 'Upload Document'}
      </button>
    </div>
  );
};
```

---

## 🔄 Forgot Password Flow

### 1. Request Password Reset
```javascript
const requestPasswordReset = async (email) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  
  const data = await response.json();
  // Show: "If the email exists, a password reset link has been sent."
};
```

### 2. Reset Password Page
```javascript
// Get token from URL: /reset-password?token=xyz
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

const resetPassword = async (newPassword) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      token: token,
      new_password: newPassword 
    }),
  });
  
  if (response.ok) {
    // Redirect to login
    window.location.href = '/login';
  }
};
```

---

## 🧪 Test Accounts

```javascript
const TEST_ACCOUNTS = {
  admin: {
    email: 'admin@churchill.edu.au',
    password: 'test1234',
    role: 'ADMIN'
  },
  agent: {
    email: 'agent@test.com',
    password: 'test123',
    role: 'AGENT',
    organization: 'Test Agency'
  },
  student: {
    email: 'student@test.com',
    password: 'test123',
    role: 'STUDENT'
  },
  staff: {
    email: 'staff@churchill.nsw.edu.au',
    password: 'test123',
    role: 'STAFF'
  }
};
```

---

## 📊 API Response Patterns

### Success Response
```json
{
  "id": "uuid",
  "data": {...},
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 🎨 Design Guidelines

### Color Scheme (from Admin Panel)
```css
:root {
  --primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --primary-solid: #667eea;
  --success: #48bb78;
  --danger: #f56565;
  --warning: #ffc107;
  --info: #bee3f8;
  --gray: #f5f7fa;
}
```

### Status Badge Colors
```javascript
const getStatusColor = (status) => {
  const colors = {
    ACTIVE: 'green',
    INACTIVE: 'gray',
    SUBMITTED: 'blue',
    UNDER_REVIEW: 'yellow',
    APPROVED: 'green',
    REJECTED: 'red'
  };
  return colors[status] || 'gray';
};
```

---

## 🚀 Quick Start Checklist

### Phase 1: Authentication
- [ ] Build login page
- [ ] Implement token storage
- [ ] Add protected route wrapper
- [ ] Create logout function
- [ ] Add forgot password flow

### Phase 2: Agent Dashboard
- [ ] Dashboard overview (stats)
- [ ] Student list view
- [ ] Application list view
- [ ] Profile settings

### Phase 3: Application Flow
- [ ] Create application form (multi-step)
- [ ] Document upload component
- [ ] Application status tracker
- [ ] Application details view

### Phase 4: Polish
- [ ] Error handling
- [ ] Loading states
- [ ] Form validation
- [ ] Responsive design
- [ ] Accessibility

---

## 📞 API Endpoints Reference

### Authentication
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
GET    /api/v1/auth/me
```

### Students
```
GET    /api/v1/students/me
PATCH  /api/v1/students/me
GET    /api/v1/students/{id}
```

### Applications
```
GET    /api/v1/applications
POST   /api/v1/applications
GET    /api/v1/applications/{id}
PATCH  /api/v1/applications/{id}
GET    /api/v1/applications/{id}/timeline
```

### Documents
```
GET    /api/v1/documents/types
POST   /api/v1/documents/upload
GET    /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
GET    /api/v1/applications/{id}/documents
```

### Application Steps
```
POST   /api/v1/application-steps/personal
POST   /api/v1/application-steps/contact
POST   /api/v1/application-steps/education
POST   /api/v1/application-steps/employment
POST   /api/v1/application-steps/english
POST   /api/v1/application-steps/emergency
POST   /api/v1/application-steps/submit
```

---

## 💡 Best Practices

1. **Token Management**
   - Store tokens in localStorage
   - Implement token refresh logic
   - Clear tokens on logout

2. **Error Handling**
   - Handle 401 (unauthorized) → redirect to login
   - Handle 403 (forbidden) → show access denied
   - Handle 422 (validation) → show field errors

3. **Loading States**
   - Show spinners during API calls
   - Disable buttons while submitting
   - Display skeleton loaders for lists

4. **User Feedback**
   - Success toasts for actions
   - Error messages for failures
   - Confirmation dialogs for deletions

5. **Performance**
   - Implement pagination for lists
   - Cache user profile data
   - Lazy load heavy components

---

## 🐛 Troubleshooting

### CORS Issues
```javascript
// If you see CORS errors, check:
// 1. Backend is running on localhost:8000
// 2. Frontend is on allowed origin (3000, 5173, 5174)
// 3. Include credentials if needed
fetch(url, {
  credentials: 'include', // if using cookies
});
```

### 401 Unauthorized
```javascript
// Token expired or invalid
// Implement auto-refresh:
const makeAuthRequest = async (url, options) => {
  let response = await fetch(url, options);
  
  if (response.status === 401) {
    // Try to refresh token
    const newToken = await refreshToken();
    options.headers.Authorization = `Bearer ${newToken}`;
    response = await fetch(url, options);
  }
  
  return response;
};
```

---

## 📚 Additional Resources

- **Full API Docs**: http://localhost:8000/docs
- **Postman Collection**: `/docs/Application_Portal_API.postman_collection.json`
- **TypeScript Types**: `/docs/api-types.ts`
- **Database Schema**: `/docs/DATABASE.md`

---

## 🤝 Support

For questions or issues:
1. Check Swagger UI for endpoint details
2. Review error responses carefully
3. Test with Postman/curl first
4. Check backend logs: `docker-compose logs backend`

---

**Last Updated**: November 19, 2025
**Backend Version**: v3.1
**API Version**: v1
