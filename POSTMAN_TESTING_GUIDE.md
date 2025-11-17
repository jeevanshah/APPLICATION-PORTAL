# Postman Testing Guide - Churchill Application Portal

## Quick Start

### 1. Base URL
```
http://localhost:8000
```

### 2. API Documentation (Swagger)
Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Authentication Flow

### Step 1: Create Test Users

First, you need to create user accounts for different roles. Run these in your terminal:

```powershell
# Create an Agent user
docker exec churchill_backend python -c "
from app.db.database import SessionLocal
from app.models import UserAccount, AgentProfile, RtoProfile
from app.core.security import get_password_hash
from sqlalchemy.orm import Session

db = SessionLocal()

# Get Churchill RTO
rto = db.query(RtoProfile).filter(RtoProfile.name == 'Churchill Education').first()

# Create agent user
agent = UserAccount(
    email='agent@test.com',
    password_hash=get_password_hash('Password123!'),
    role='AGENT',
    rto_profile_id=rto.id,
    status='active'
)
db.add(agent)
db.commit()
db.refresh(agent)

# Create agent profile
agent_profile = AgentProfile(
    user_account_id=agent.id,
    agency_name='Test Agency',
    phone='+61400000000',
    address='123 Test St',
    commission_rate=15.0
)
db.add(agent_profile)
db.commit()
print(f'Agent created: {agent.email}')
db.close()
"

# Create a Staff user
docker exec churchill_backend python -c "
from app.db.database import SessionLocal
from app.models import UserAccount, StaffProfile, RtoProfile
from app.core.security import get_password_hash

db = SessionLocal()
rto = db.query(RtoProfile).filter(RtoProfile.name == 'Churchill Education').first()

staff = UserAccount(
    email='staff@test.com',
    password_hash=get_password_hash('Password123!'),
    role='STAFF',
    rto_profile_id=rto.id,
    status='active'
)
db.add(staff)
db.commit()
db.refresh(staff)

staff_profile = StaffProfile(
    user_account_id=staff.id,
    department='Admissions',
    job_title='Admissions Officer'
)
db.add(staff_profile)
db.commit()
print(f'Staff created: {staff.email}')
db.close()
"

# Create a Student user (read-only for applications)
docker exec churchill_backend python -c "
from app.db.database import SessionLocal
from app.models import UserAccount, StudentProfile, RtoProfile
from app.core.security import get_password_hash
from datetime import date

db = SessionLocal()
rto = db.query(RtoProfile).filter(RtoProfile.name == 'Churchill Education').first()

student = UserAccount(
    email='student@test.com',
    password_hash=get_password_hash('Password123!'),
    role='STUDENT',
    rto_profile_id=rto.id,
    status='active'
)
db.add(student)
db.commit()
db.refresh(student)

student_profile = StudentProfile(
    user_account_id=student.id,
    given_name='John',
    family_name='Doe',
    date_of_birth=date(2000, 1, 1),
    nationality='Australia',
    phone='+61400000001',
    address='456 Student Ave'
)
db.add(student_profile)
db.commit()
print(f'Student created: {student.email}')
db.close()
"
```

### Step 2: Login and Get Access Token

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "agent@test.com",
  "password": "Password123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "agent@test.com",
    "role": "AGENT"
  }
}
```

**In Postman:**
1. Create a new request
2. Set method to `POST`
3. Set URL to `http://localhost:8000/api/v1/auth/login`
4. Go to Body → raw → JSON
5. Paste the login JSON
6. Click Send
7. **Copy the `access_token` from the response**

### Step 3: Set Authorization Header

For all subsequent requests, you need to include the token:

**In Postman:**
1. Go to the Authorization tab
2. Select Type: `Bearer Token`
3. Paste your access token in the Token field

**OR manually add header:**
- Key: `Authorization`
- Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

---

## Testing Application Workflow (Agent)

### 1. Create a Student for the Application

**Endpoint:** `POST /api/v1/students`

**Headers:**
- `Authorization: Bearer {agent_token}`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "email": "newstudent@test.com",
  "password": "StudentPass123!",
  "given_name": "Jane",
  "family_name": "Smith",
  "date_of_birth": "1998-05-15",
  "nationality": "India",
  "passport_number": "N1234567",
  "visa_type": "Student Visa (500)",
  "phone": "+61412345678",
  "address": "789 Student Road, Melbourne VIC 3000"
}
```

**Response:**
```json
{
  "id": "student-uuid",
  "email": "newstudent@test.com",
  "role": "STUDENT",
  "profile": {
    "id": "profile-uuid",
    "given_name": "Jane",
    "family_name": "Smith",
    ...
  }
}
```

**Save the `profile.id` - you'll need it for creating applications!**

### 2. Get Available Courses

**Endpoint:** `GET /api/v1/applications/courses`

**Headers:**
- `Authorization: Bearer {agent_token}`

**Response:**
```json
[
  {
    "id": "course-uuid",
    "course_code": "CHU-BSB50120",
    "course_name": "Diploma of Business",
    "intake": "2025 Semester 1",
    "campus": "Melbourne",
    "tuition_fee": 15000.00,
    "is_active": true
  }
]
```

**Save a `course_offering.id` for the next step!**

### 3. Create Application Draft (Agent Only)

**Endpoint:** `POST /api/v1/applications`

**Headers:**
- `Authorization: Bearer {agent_token}`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "student_profile_id": "student-profile-uuid-from-step-1",
  "course_offering_id": "course-uuid-from-step-2"
}
```

**Response:**
```json
{
  "id": "application-uuid",
  "student_profile_id": "...",
  "agent_profile_id": "...",
  "course_offering_id": "...",
  "current_stage": "DRAFT",
  "created_at": "2025-11-17T10:30:00Z",
  ...
}
```

**Save the `application.id`!**

### 4. Update Application (Fill the Form)

**Endpoint:** `PATCH /api/v1/applications/{application_id}`

**Headers:**
- `Authorization: Bearer {agent_token}`
- `Content-Type: application/json`

**Request Body (Example - add any fields you want):**
```json
{
  "usi": "ABC1234567",
  "emergency_contacts": [
    {
      "name": "Mary Smith",
      "relationship": "Mother",
      "phone": "+61400111222",
      "email": "mary.smith@email.com"
    }
  ],
  "health_cover_policy": {
    "provider": "OSHC Worldcare",
    "policy_number": "POL123456",
    "start_date": "2025-02-01",
    "end_date": "2026-02-01",
    "coverage_type": "Single"
  },
  "language_cultural_data": {
    "first_language": "Hindi",
    "other_languages": ["English", "Punjabi"],
    "country_of_birth": "India",
    "citizenship_status": "International Student"
  },
  "disability_support": {
    "has_disability": false,
    "disability_details": null,
    "support_required": null
  }
}
```

**Response:**
```json
{
  "id": "application-uuid",
  "current_stage": "DRAFT",
  "usi": "ABC1234567",
  "emergency_contacts": [...],
  "health_cover_policy": {...},
  ...
}
```

### 5. Submit Application (Agent Only)

**Endpoint:** `POST /api/v1/applications/{application_id}/submit`

**Headers:**
- `Authorization: Bearer {agent_token}`

**Request Body:**
```json
{
  "notes": "Application completed and verified by agent"
}
```

**Response:**
```json
{
  "id": "application-uuid",
  "current_stage": "SUBMITTED",
  "submitted_at": "2025-11-17T11:00:00Z",
  ...
}
```

### 6. Get Application Details

**Endpoint:** `GET /api/v1/applications/{application_id}`

**Headers:**
- `Authorization: Bearer {agent_token}`

**Response:**
```json
{
  "id": "application-uuid",
  "student_profile_id": "...",
  "current_stage": "SUBMITTED",
  "timeline": [
    {
      "id": "timeline-uuid",
      "entry_type": "APPLICATION_CREATED",
      "message": "Application draft created by agent Test Agency",
      "created_at": "2025-11-17T10:30:00Z"
    },
    {
      "id": "timeline-uuid-2",
      "entry_type": "STAGE_CHANGED",
      "message": "Application submitted by agent Test Agency",
      "created_at": "2025-11-17T11:00:00Z"
    }
  ],
  ...
}
```

---

## Testing Permission Restrictions

### Test 1: Student Cannot Create Application

**Login as Student:**
```json
{
  "email": "student@test.com",
  "password": "Password123!"
}
```

**Try to Create Application:**
`POST /api/v1/applications` (with student token)

**Expected Response: 403 Forbidden**
```json
{
  "detail": "Students cannot create applications. Please contact your agent."
}
```

### Test 2: Student Cannot Edit Application

**Try to Update Application:**
`PATCH /api/v1/applications/{application_id}` (with student token)

**Expected Response: 403 Forbidden**
```json
{
  "detail": "Students cannot edit applications. Please contact your agent."
}
```

### Test 3: Student Cannot Submit Application

**Try to Submit Application:**
`POST /api/v1/applications/{application_id}/submit` (with student token)

**Expected Response: 403 Forbidden**
```json
{
  "detail": "Students cannot submit applications. Please contact your agent."
}
```

### Test 4: Student CAN View Application

**View Application:**
`GET /api/v1/applications/{application_id}` (with student token)

**Expected Response: 200 OK** (if they own it)

---

## Postman Collection Setup

### Environment Variables

Create a Postman Environment with these variables:

| Variable | Initial Value |
|----------|--------------|
| `base_url` | `http://localhost:8000` |
| `agent_token` | _(set after login)_ |
| `student_token` | _(set after login)_ |
| `staff_token` | _(set after login)_ |
| `student_profile_id` | _(set after creating student)_ |
| `course_offering_id` | _(set after getting courses)_ |
| `application_id` | _(set after creating application)_ |

### Using Variables in Requests

**URL Example:**
```
{{base_url}}/api/v1/applications/{{application_id}}
```

**Authorization Example:**
```
Bearer {{agent_token}}
```

### Auto-Setting Tokens (Tests Tab)

In the login request's **Tests** tab, add:

```javascript
// Parse response
var jsonData = pm.response.json();

// Save token to environment
pm.environment.set("agent_token", jsonData.access_token);

// Log success
console.log("Token saved:", jsonData.access_token);
```

---

## Common API Endpoints Reference

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

### Students (Agent/Staff only)
- `POST /api/v1/students` - Create student
- `GET /api/v1/students` - List students (your agency's students)
- `GET /api/v1/students/{id}` - Get student details
- `PATCH /api/v1/students/{id}` - Update student

### Applications
- `GET /api/v1/applications/courses` - List available courses
- `POST /api/v1/applications` - Create application (Agent/Staff only)
- `GET /api/v1/applications` - List applications (filtered by role)
- `GET /api/v1/applications/{id}` - Get application details
- `PATCH /api/v1/applications/{id}` - Update application (Agent/Staff only)
- `POST /api/v1/applications/{id}/submit` - Submit application (Agent/Staff only)

---

## Troubleshooting

### 401 Unauthorized
- Your token expired (tokens last 30 minutes by default)
- Login again to get a fresh token

### 403 Forbidden
- You don't have permission for this action
- Check you're using the correct role's token (agent vs student)

### 404 Not Found
- The resource doesn't exist
- Check the UUID is correct
- Ensure the application belongs to your agency (for agents)

### 422 Unprocessable Entity
- Request body validation failed
- Check the response for specific field errors
- Ensure all required fields are present

### Docker Not Running
```powershell
# Start the application
docker-compose -f docker-compose.dev.yml up -d
```

### Check API is Running
```powershell
# Test connection
curl http://localhost:8000/docs
```

---

## Sample Postman Collection Structure

```
📁 Churchill Application Portal
├── 📁 Auth
│   ├── Login (Agent)
│   ├── Login (Student)
│   ├── Login (Staff)
│   └── Get Current User
├── 📁 Students
│   ├── Create Student
│   ├── List Students
│   └── Get Student Details
├── 📁 Applications
│   ├── Get Available Courses
│   ├── Create Application (Agent)
│   ├── Update Application (Agent)
│   ├── Submit Application (Agent)
│   ├── Get Application Details
│   └── List My Applications
└── 📁 Permission Tests
    ├── Student Try Create (403)
    ├── Student Try Edit (403)
    └── Student Try Submit (403)
```

---

## Next Steps

1. **Import this guide into Postman** as a collection using the examples above
2. **Run the user creation scripts** in your terminal
3. **Login with each role** to get tokens
4. **Test the complete workflow** as an agent
5. **Test permission restrictions** as a student
6. **Check the timeline** to see all events tracked

Happy Testing! 🚀
