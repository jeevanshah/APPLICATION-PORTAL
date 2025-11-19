# Frontend Integration Guide - Churchill Application Portal

## 🎯 Overview
This guide helps frontend developers integrate with the Churchill Application Portal backend API.

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
GET /api/v1/applications?limit=20&offset=0
Authorization: Bearer {agent_token}
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
      "student_name": "John Doe",
      "course_name": "Certificate IV in Business",
      "intake": "Feb 2025"
    }
  ]
}
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

### 3. Document Upload Component

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
