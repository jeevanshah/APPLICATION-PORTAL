# Churchill Application Portal

A modern student application management system for Churchill Education, built with FastAPI, PostgreSQL 16, and a lean JSONB-first architecture.

## 📋 Project Overview

**Purpose**: Streamline the student application lifecycle from submission through enrollment, with support for agents, staff workflows, document management, GS assessments, and automated notifications.

**Target Users**:
- **Students**: Submit and track applications
- **Agents**: Manage multiple student applications
- **Staff**: Review applications, request documents, conduct GS assessments
- **Admins**: Manage users, configure workflows, generate reports

**Tech Stack**:
- **Backend**: FastAPI + Python 3.12 + SQLAlchemy 2.0 + Alembic
- **Database**: PostgreSQL 16 with JSONB-first lean schema (16 tables)
- **Frontend**: React + TypeScript + Vite (TODO)
- **Background Tasks**: Celery + Redis
- **Document Storage**: Azure Blob Storage
- **OCR**: Azure Form Recognizer
- **Email**: Azure Communication Services
- **Deployment**: Docker + Hostinger VPS + Nginx

## 🎯 Key Features

### MVP (Phase 1 - Current)
- ✅ JWT authentication with MFA (TOTP)
- ✅ Multi-tenancy (RTO profile-based)
- ✅ Role-based access control (Student, Agent, Staff, Admin)
- ✅ 16-table lean JSONB schema (53% reduction from original design)
- ✅ SQLAlchemy models with comprehensive JSONB support
- ✅ Docker deployment configuration
- 🚧 Application CRUD endpoints (TODO)
- 🚧 Document upload/versioning (TODO)
- 🚧 Timeline activity feed (TODO)

### Phase 2 (Next)
- Document OCR with Azure Form Recognizer
- Email notifications (Azure Communication Services)
- GS assessment workflow
- E-signature integration (DocuSeal)
- Staff dashboard with SLA tracking

### Phase 3 (Future)
- React frontend with real-time updates
- Advanced reporting and analytics
- Mobile app (React Native)
- White-label multi-RTO SaaS expansion

## 📁 Project Structure

```
Application-Portal/
├── docs/                           # Comprehensive documentation
│   ├── data-model-diagram.md       # UML + ER diagrams (v3.1)
│   ├── solution-architecture.md    # Full architecture blueprint
│   ├── SCHEMA_MIGRATION_v3.md      # Migration guide (v2.0 → v3.1)
│   └── requirements.md             # Original requirements
├── backend/                        # FastAPI backend (COMPLETE)
│   ├── app/
│   │   ├── api/v1/endpoints/       # API routes (auth DONE, others TODO)
│   │   ├── core/                   # Config, security, utilities
│   │   ├── db/                     # Database connection
│   │   ├── models/                 # SQLAlchemy models (16 tables)
│   │   ├── schemas/                # Pydantic schemas + JSONB models
│   │   └── main.py                 # FastAPI app entry
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # Unit & integration tests (TODO)
│   ├── Dockerfile                  # Multi-stage build
│   ├── requirements.txt
│   └── README.md                   # Backend-specific docs
├── frontend/                       # React frontend (TODO)
├── docker-compose.yml              # Full stack orchestration
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** for Windows (includes docker-compose)
- Python 3.12+ (for local development)
- PostgreSQL 16 (for local development)
- Redis 7 (for local development)
- Node.js 20+ (for frontend, when implemented)

### Option 1: Docker (Recommended) - 1 Command Setup

```powershell
# Run the automated setup script
.\start-docker.ps1
```

This will:
- ✅ Check Docker installation
- ✅ Create `.env` configuration
- ✅ Start PostgreSQL, Redis, FastAPI
- ✅ Run database migrations
- ✅ Open API docs in browser

**Access the API**: http://localhost:8000/docs

**See [QUICKSTART.md](QUICKSTART.md) for Docker commands**

### Option 1b: Docker (Manual)

```powershell
# 1. Create environment file
Copy-Item backend\.env.example backend\.env
# Edit backend\.env if needed

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d --build

# 3. Run database migrations
docker exec -it churchill_backend alembic upgrade head

# 4. Access API docs
start http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Run migrations
alembic upgrade head

# 4. Start server
uvicorn app.main:app --reload
```

## 📊 Database Schema (v3.1)

**16 tables** with JSONB-first lean architecture:

### Core Identity & Multi-tenancy
1. `rto_profile` - RTO/organization metadata
2. `user_account` - Unified auth (all roles)
3. `agent_profile`, `staff_profile`, `student_profile` - Role-specific data

### Application Workflow
6. `course_offering` - Course catalog
7. `application` - Central record with **10 JSONB fields**
8. `application_stage_history` - Workflow transitions

### History (Normalized for Performance)
9. `schooling_history`, 10. `qualification_history`, 11. `employment_history`

### Document Management
12. `document_type`, 13. `document`, 14. `document_version`

### Activity & Compliance
15. `timeline_entry`, 16. `audit_log`

**JSONB consolidation**: 19 former tables → 10 JSONB fields in `application` table
- `enrollment_data`, `emergency_contacts`, `health_cover_policy`, `disability_support`
- `language_cultural_data`, `survey_responses`, `additional_services`
- `gs_assessment`, `signature_data`, `form_metadata`

**See `docs/data-model-diagram.md` for full UML diagrams.**

## 🔐 Authentication & Security

### JWT Authentication
- Access tokens (30 min expiry)
- Refresh tokens (7 day expiry)
- MFA support via TOTP (Google Authenticator, Authy)

### Role-Based Access Control
```python
from app.api.dependencies import require_admin, require_staff

@router.get("/admin/settings")
async def admin_settings(user = Depends(require_admin)):
    # Admin only
    ...

@router.get("/applications")
async def list_applications(user = Depends(require_staff)):
    # Staff or Admin only
    ...
```

### Multi-tenancy (RTO Filtering)
All queries automatically filtered by `rto_profile_id`:
```python
from app.api.dependencies import get_rto_filter

@router.get("/applications")
async def list_apps(rto_id: str = Depends(get_rto_filter), db = Depends(get_db)):
    # Automatically scoped to current user's RTO
    ...
```

## 📡 API Endpoints

### Implemented ✅
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login (JWT)
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/mfa/setup` - Generate MFA secret
- `POST /api/v1/auth/mfa/verify` - Enable MFA
- `GET /api/v1/auth/me` - Current user info

### TODO 🚧
- Application CRUD (`/api/v1/applications`)
- Document management (`/api/v1/documents`)
- Timeline feed (`/api/v1/timeline`)
- User management (`/api/v1/users`)
- Reports (`/api/v1/reports`)

**Interactive API docs**: http://localhost:8000/docs

## 🐳 Docker Services

```yaml
services:
  postgres:        # PostgreSQL 16
  redis:           # Redis 7 (Celery broker)
  backend:         # FastAPI app
  celery_worker:   # Background tasks
  celery_beat:     # Scheduled tasks
  nginx:           # Reverse proxy (production profile)
  certbot:         # SSL certificates (production profile)
```

**Start development stack**:
```bash
docker-compose up -d
```

**Start production stack** (with Nginx + SSL):
```bash
docker-compose --profile production up -d
```

## 📚 Documentation

All documentation in `docs/`:

1. **[data-model-diagram.md](docs/data-model-diagram.md)**
   - UML class diagrams with all attributes
   - Entity-relationship diagrams
   - JSONB field examples
   - Schema evolution (v1.0 → v3.1)

2. **[solution-architecture.md](docs/solution-architecture.md)**
   - Complete system architecture
   - Technology stack decisions
   - API design patterns
   - Azure integration details
   - Deployment architecture

3. **[SCHEMA_MIGRATION_v3.md](docs/SCHEMA_MIGRATION_v3.md)**
   - Migration guide from v2.0 (28 tables) to v3.1 (16 tables)
   - SQL migration scripts
   - SQLAlchemy model examples
   - JSONB consolidation rationale

4. **[requirements.md](docs/requirements.md)**
   - Original business requirements
   - User stories
   - Functional specifications

5. **[backend/README.md](backend/README.md)**
   - Backend-specific setup
   - Development workflow
   - Testing guide
   - Deployment instructions

## 🔧 Development

### Running Tests
```bash
cd backend
pytest
pytest --cov=app tests/  # With coverage
```

### Code Quality
```bash
black .          # Format
flake8 .         # Lint
mypy app/        # Type check
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🚀 Deployment to Hostinger VPS

1. **Provision VPS** (VPS 2: 2 vCPU, 4GB RAM, Ubuntu 22.04)
2. **Install Docker + docker-compose**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo apt install docker-compose-plugin
   ```
3. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/Application-Portal.git
   cd Application-Portal
   ```
4. **Configure environment**
   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env  # Set production values
   ```
5. **Start services**
   ```bash
   docker-compose --profile production up -d
   ```
6. **SSL Setup** (automatic via Let's Encrypt/certbot in docker-compose)

## 📈 Roadmap

### ✅ Completed
- [x] Comprehensive documentation (v3.1 schema locked)
- [x] SQLAlchemy models (16 tables with JSONB)
- [x] Pydantic schemas (nested JSONB models)
- [x] Authentication API (JWT + MFA)
- [x] Docker deployment configuration
- [x] Alembic migration setup

### 🚧 In Progress
- [ ] Application CRUD endpoints
- [ ] Document upload/versioning
- [ ] Timeline activity feed

### 📅 Next Phase
- [ ] Azure Blob Storage integration
- [ ] Azure Form Recognizer OCR
- [ ] Email notifications (Azure Communication Services)
- [ ] GS assessment workflow
- [ ] E-signature integration (DocuSeal)
- [ ] Staff dashboard
- [ ] React frontend scaffolding

### 🔮 Future
- [ ] Advanced reporting
- [ ] Mobile app
- [ ] White-label multi-RTO SaaS

## 🤝 Contributing

This is a proprietary project for Churchill Education. Internal development only.

### Branching Strategy
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - Feature branches
- `hotfix/*` - Production hotfixes

### Commit Convention
```
feat: Add application CRUD endpoints
fix: Correct MFA token validation
docs: Update schema diagrams to v3.1
refactor: Consolidate JSONB models
test: Add auth endpoint tests
```

## 📄 License

Proprietary - Churchill Education © 2025

---

**Built with ❤️ for Churchill Education**

For questions or support, contact: dev@churchilleducation.edu.au
