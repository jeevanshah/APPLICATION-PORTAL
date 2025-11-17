# Churchill Application Portal

Student Application Management System with multi-stage workflow, document management, and OCR processing.

---

## 🚀 Quick Start (Frontend Developers)

**Need the backend API running?**

```powershell
.\quick-setup.ps1
```

**That's it!** API will be ready at: http://localhost:8000/docs

📖 **Step-by-step guide:** See [QUICKSTART.md](./QUICKSTART.md)

---

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[docs/SETUP.md](./docs/SETUP.md)** - Detailed setup guide
- **[docs/API_GUIDE.md](./docs/API_GUIDE.md)** - API reference
- **[docs/DATABASE.md](./docs/DATABASE.md)** - Database schema
- **[docs/FEATURES.md](./docs/FEATURES.md)** - Feature overview

---

## 🏗️ Architecture

**Backend:** FastAPI (Python 3.12) + PostgreSQL 16 + Redis 7  
**Deployment:** Docker Compose with 6 services  
**Database:** 16-table schema with multi-tenancy  
**Auth:** JWT-based with role-based access control

### Services
- **FastAPI Backend** (port 8000) - REST API
- **PostgreSQL 16** (port 5432) - Database
- **Redis 7** (port 6379) - Cache & message broker
- **pgAdmin** (port 5050) - Database UI
- **Celery Worker** - Background tasks
- **Celery Beat** - Scheduled tasks

---

## 🔧 Tech Stack

### Backend
- FastAPI 0.109.0 + Uvicorn
- SQLAlchemy 2.0 + Alembic
- Pydantic v2
- PostgreSQL (psycopg2)
- Redis + Celery
- Azure SDK (Storage, Form Recognizer, Vision, Email)
- JWT Auth (python-jose, passlib, pyotp)

### Database
16 tables including:
- User accounts (multi-role)
- Student profiles
- Applications (10-stage workflow)
- Documents (with OCR)
- Course offerings
- Communications & timeline

---

## 🌟 Features

### Core
- ✅ Multi-tenant RTO management
- ✅ Student profile management
- ✅ 10-stage application workflow
- ✅ Document upload & OCR extraction
- ✅ Role-based access (Student, Agent, Staff, Admin)
- ✅ JWT authentication
- ✅ File storage (local + Azure Blob)

### Workflow Stages
1. DRAFT
2. SUBMITTED
3. STAFF_REVIEW
4. AWAITING_DOCUMENTS
5. GS_ASSESSMENT
6. OFFER_GENERATED
7. OFFER_ACCEPTED
8. ENROLLED
9. REJECTED
10. WITHDRAWN

---

## 💻 Development

### Prerequisites
- Docker Desktop
- Git

### Setup
```powershell
git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git
cd APPLICATION-PORTAL
.\quick-setup.ps1
```

### Common Commands
```powershell
# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Restart backend
docker-compose restart backend

# Database shell
docker exec -it churchill_postgres psql -U churchill_user -d churchill_portal

# Backend shell
docker exec -it churchill_backend /bin/bash
```

---

## 🔌 API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Get access token
- `GET /auth/me` - Current user info

### Applications
- `POST /applications` - Create application
- `GET /applications` - List applications
- `GET /applications/{id}` - Get application
- `PATCH /applications/{id}/steps/{step}/{step_name}` - Update step

### Students
- `POST /students` - Create profile
- `GET /students` - List students
- `GET /students/{id}` - Get student

### Documents
- `POST /documents/upload` - Upload document
- `GET /documents/{id}` - Get document
- `GET /documents/{id}/download` - Download file

**Interactive docs:** http://localhost:8000/docs

---

## 🗄️ Database Access

**pgAdmin Web UI:**
- URL: http://localhost:5050
- Email: admin@admin.com
- Password: admin123

**Direct Connection:**
- Host: localhost
- Port: 5432
- User: churchill_user
- Password: churchill_password
- Database: churchill_portal

---

## 🧪 Testing

```powershell
# Run tests (when implemented)
docker exec churchill_backend pytest

# Test with coverage
docker exec churchill_backend pytest --cov
```

---

## 📦 Project Structure

```
APPLICATION-PORTAL/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # API routes
│   │   ├── core/              # Config & security
│   │   ├── db/                # Database
│   │   ├── models/            # SQLAlchemy models
│   │   ├── repositories/      # Data access
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── utils/             # Utilities
│   ├── alembic/               # Migrations
│   ├── tests/                 # Tests
│   ├── requirements.txt       # Dependencies
│   └── Dockerfile             # Container image
├── docs/                      # Documentation
├── docker-compose.yml         # Services config
├── quick-setup.ps1            # One-command setup
└── QUICKSTART.md              # Quick start guide
```

---

## 🚢 Deployment

### Production
```powershell
# Use production profile (includes Nginx + Let's Encrypt)
docker-compose --profile production up -d

# SSL certificates via Certbot
docker exec churchill_certbot certbot renew
```

### Environment Variables
See `backend/.env.example` for all configuration options.

**Critical settings:**
- `SECRET_KEY` - JWT secret (generate with `openssl rand -hex 32`)
- `POSTGRES_PASSWORD` - Database password
- `DEBUG` - Set to `False` in production
- `BACKEND_CORS_ORIGINS` - Frontend URLs

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

[Add your license here]

---

## 👥 Team

Churchill Education - RTO Student Application Portal

---

## 📞 Support

- **Documentation:** See `docs/` folder
- **API Docs:** http://localhost:8000/docs
- **Issues:** [GitHub Issues](https://github.com/jeevanshah/APPLICATION-PORTAL/issues)

---

**Built with FastAPI, PostgreSQL, and Docker** 🚀
