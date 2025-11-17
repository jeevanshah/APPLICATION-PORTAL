# 📚 Quick Reference - Churchill Application Portal

Essential IDs, credentials, and configuration values for quick lookup.

---

## 🔐 Test Credentials

### Agent Account
```
Email: test.agent@agency.com
Password: AgentPass123!
User ID: ddee69e2-a48f-4b4d-8440-3e8efc38c786
```

### Student Account
```
Email: test.student@example.com
Password: StudentPass123!
User ID: 0cfb9aec-5e16-48cb-b1a1-5f4dd8dde802
```

### pgAdmin
```
URL: http://localhost:5050
Email: admin@admin.com
Password: admin123
```

---

## 📄 Document Type IDs

### Mandatory Documents (with OCR)
```
Passport:       10000000-0000-0000-0000-000000000001
SLC Transcript: 10000000-0000-0000-0000-000000000002
HSC Transcript: 10000000-0000-0000-0000-000000000003
English Test:   10000000-0000-0000-0000-000000000004
```

### Optional Documents
```
ID Card:           10000000-0000-0000-0000-000000000005
Birth Certificate: 10000000-0000-0000-0000-000000000006
Previous Visa:     10000000-0000-0000-0000-000000000007
Health Cover:      10000000-0000-0000-0000-000000000008
Financial Proof:   10000000-0000-0000-0000-000000000009
Relation Proof:    10000000-0000-0000-0000-000000000010
Tax Income:        10000000-0000-0000-0000-000000000011
Business Income:   10000000-0000-0000-0000-000000000012
Other:             10000000-0000-0000-0000-000000000013
```

---

## 🌐 Service URLs

### Development
```
API Base:         http://localhost:8000/api/v1
Swagger Docs:     http://localhost:8000/docs
ReDoc:            http://localhost:8000/redoc
Health Check:     http://localhost:8000/health
pgAdmin:          http://localhost:5050
Database:         localhost:5432
Redis:            localhost:6379
```

---

## 🗄️ Database Credentials

### PostgreSQL
```
Host (external):  localhost
Host (Docker):    postgres
Port:             5432
Database:         churchill_portal
Username:         churchill_user
Password:         churchill_password
```

### Connection String
```
postgresql://churchill_user:churchill_password@localhost:5432/churchill_portal
```

---

## 🔑 Environment Variables

### Required (.env)
```env
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=churchill_user
POSTGRES_PASSWORD=churchill_password
POSTGRES_DB=churchill_portal

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
DEBUG=True

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### Optional (Azure)
```env
# Azure Computer Vision (for OCR)
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_VISION_KEY=your-api-key-here

# File Upload
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=20
```

---

## 📊 API Endpoints Quick Reference

### Authentication
```
POST   /auth/login       - Login
POST   /auth/register    - Create account
GET    /auth/me          - Current user
POST   /auth/refresh     - Refresh token
```

### Applications
```
POST   /applications                           - Create
GET    /applications/{id}                      - Get details
GET    /applications                           - List all
PATCH  /applications/{id}/steps/{n}/{name}    - Update step
```

### Documents
```
POST   /documents/upload                         - Upload with OCR
GET    /documents/{id}                           - Get details
GET    /documents/{id}/ocr                       - OCR results
GET    /documents/application/{app_id}/autofill  - Auto-fill suggestions
GET    /documents/application/{app_id}/stats     - Statistics
```

---

## 🎨 Frontend Configuration

### Vite React Project

**.env:**
```env
VITE_API_URL=http://localhost:8000/api/v1
```

**.env.production:**
```env
VITE_API_URL=https://api.yourdomain.com/api/v1
```

### API Client Setup
```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 🐳 Docker Commands

### Service Management
```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Check status
docker-compose ps
```

### Database Operations
```powershell
# Run migrations
docker-compose exec backend alembic upgrade head

# Create migration
docker-compose exec backend alembic revision --autogenerate -m "Message"

# Access PostgreSQL
docker-compose exec postgres psql -U churchill_user -d churchill_portal
```

---

## 📝 Example Requests

### Login (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test.agent@agency.com",
    "password": "AgentPass123!"
  }'
```

### Create Application (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/applications" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_profile_id": "student-uuid",
    "course_offering_id": "course-uuid"
  }'
```

### Upload Document (PowerShell)
```powershell
$form = @{
    application_id = "app-uuid"
    document_type_id = "10000000-0000-0000-0000-000000000001"
    file = Get-Item "C:\path\to\passport.pdf"
    process_ocr = "true"
}

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/upload" `
    -Method POST `
    -Headers @{"Authorization" = "Bearer your-token"} `
    -Form $form
```

---

## 📋 12-Step Form Names

| Step | Endpoint Path | Description |
|------|---------------|-------------|
| 1 | `personal-details` | Identity & contact |
| 2 | `emergency-contact` | Emergency contacts |
| 3 | `health-cover` | OSHC insurance |
| 4 | `language-cultural` | Languages & background |
| 5 | `disability` | Support needs |
| 6 | `schooling` | Education history |
| 7 | `qualifications` | Certifications |
| 8 | `employment` | Work experience |
| 9 | `usi` | Student identifier |
| 10 | `additional-services` | Optional services |
| 11 | `survey` | Pre-enrollment survey |
| 12 | `documents` | Upload status |

---

## 🔒 Permission Matrix

| Action | Student | Agent | Staff | Admin |
|--------|---------|-------|-------|-------|
| Create App | ❌ | ✅ | ✅ | ✅ |
| Edit App | ❌ | ✅ (own) | ✅ (all) | ✅ (all) |
| Upload Doc | ✅ (own) | ✅ (own) | ✅ (assigned) | ✅ (all) |
| Verify Doc | ❌ | ❌ | ✅ | ✅ |
| Submit App | ❌ | ✅ (own) | ✅ (all) | ✅ (all) |

---

## 🛠️ Generate Secrets

### SECRET_KEY (64 characters)

**Python:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

**OpenSSL:**
```bash
openssl rand -hex 32
```

---

## 📖 Business Requirements Summary

### User Roles
1. **Agent** - Creates applications, uploads documents, submits
2. **Student** - Views progress (read-only), signs offer
3. **Staff** - Reviews applications, verifies documents
4. **Admin** - Full system access

### Application Workflow
1. Agent creates student account
2. Agent creates application for student
3. Agent completes 12-step form
4. Agent uploads required documents
5. OCR auto-fills form fields
6. Agent reviews and submits
7. Staff reviews and verifies
8. Staff generates offer letter
9. Student signs offer (e-signature)
10. Staff conducts GS assessment
11. Student pays fees
12. Staff issues COE

### Document Requirements
- **Mandatory:** Passport, Transcripts, English Test
- **Optional:** ID Card, Financial Proof, Health Cover, etc.
- **Max Size:** 20MB per file
- **Formats:** PDF, JPG, PNG, TIFF, BMP, GIF

---

## 🔍 Troubleshooting Quick Fixes

### Port 8000 already in use
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database connection failed
```powershell
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

### Backend import errors
```powershell
docker-compose build --no-cache backend
docker-compose restart backend
```

### pgAdmin won't connect
```
Verify credentials:
- Host: postgres (not localhost)
- User: churchill_user
- Password: churchill_password
```

---

## 📚 Documentation Links

- **Main README**: [README.md](./README.md)
- **Setup Guide**: [SETUP.md](./SETUP.md)
- **API Reference**: [API_GUIDE.md](./API_GUIDE.md)
- **Features**: [FEATURES.md](./FEATURES.md)
- **Database**: [DATABASE.md](./DATABASE.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

**Last Updated:** November 18, 2025
