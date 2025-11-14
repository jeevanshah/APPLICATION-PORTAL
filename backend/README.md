# Churchill Application Portal - Backend

FastAPI backend for the Churchill Education student application management portal.

## Architecture Overview

- **Framework**: FastAPI + Pydantic v2 + SQLAlchemy 2.0
- **Database**: PostgreSQL 16 with JSONB-first lean architecture (16 tables)
- **Schema Version**: v3.1 (53% reduction from original 34 tables)
- **Authentication**: JWT with MFA (TOTP) support
- **Background Tasks**: Celery + Redis
- **Deployment**: Docker + docker-compose

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16
- Redis 7
- Docker & docker-compose (for containerized deployment)

### Local Development Setup

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set your database credentials and secret key
   ```

5. **Run database migrations**
   ```bash
   # Initialize Alembic (first time only)
   alembic init alembic
   
   # Create initial migration
   alembic revision --autogenerate -m "Initial v3.1 schema"
   
   # Apply migrations
   alembic upgrade head
   ```

6. **Start development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Start all services**
   ```bash
   # Development mode
   docker-compose up -d
   
   # Production mode (with Nginx + SSL)
   docker-compose --profile production up -d
   ```

3. **Run migrations in container**
   ```bash
   docker exec -it churchill_backend alembic upgrade head
   ```

4. **View logs**
   ```bash
   docker-compose logs -f backend
   ```

## Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── env.py                  # Alembic environment config
│   └── versions/               # Migration scripts
├── app/
│   ├── api/                    # API routes
│   │   ├── v1/
│   │   │   ├── endpoints/      # Endpoint implementations
│   │   │   │   ├── auth.py     # Authentication (login, register, MFA)
│   │   │   │   ├── applications.py  # Application CRUD (TODO)
│   │   │   │   ├── documents.py     # Document management (TODO)
│   │   │   │   └── timeline.py      # Timeline feed (TODO)
│   │   │   └── __init__.py     # API v1 router aggregator
│   │   └── dependencies.py     # Reusable dependencies (auth, RBAC)
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Settings (Pydantic v2)
│   │   └── security.py         # JWT, password hashing, MFA
│   ├── db/                     # Database
│   │   └── database.py         # SQLAlchemy engine, session
│   ├── models/                 # SQLAlchemy models
│   │   └── __init__.py         # All 16 table models + enums
│   ├── schemas/                # Pydantic schemas
│   │   └── jsonb_schemas.py    # JSONB nested models
│   ├── services/               # Business logic layer (TODO)
│   ├── utils/                  # Utility functions (TODO)
│   └── main.py                 # FastAPI app entry point
├── tests/                      # Unit & integration tests (TODO)
├── .env.example                # Environment variables template
├── .gitignore
├── alembic.ini                 # Alembic configuration
├── Dockerfile                  # Multi-stage Docker build
└── requirements.txt            # Python dependencies
```

## Database Schema (v3.1)

**16 tables with JSONB-first approach:**

### Core Tables
1. **rto_profile** - RTO/organization metadata (multi-tenancy)
2. **user_account** - Unified auth for all roles
3. **agent_profile** - Agent-specific data
4. **staff_profile** - Staff-specific data
5. **student_profile** - Student-specific data
6. **course_offering** - Course catalog

### Application Workflow
7. **application** - Central record with 10 JSONB fields
8. **application_stage_history** - Workflow transitions

### History Tables (Normalized for Query Performance)
9. **schooling_history** - Education background
10. **qualification_history** - Certifications
11. **employment_history** - Work experience

### Document Management
12. **document_type** - Document categories
13. **document** - Document records
14. **document_version** - Immutable version history

### Activity & Audit
15. **timeline_entry** - User-facing activity feed
16. **audit_log** - Compliance audit trail

**Key JSONB Fields in APPLICATION:**
- `enrollment_data` - Replaces COURSE_ENROLLMENT table
- `emergency_contacts` - Replaces EMERGENCY_CONTACT table
- `health_cover_policy` - Replaces HEALTH_COVER_POLICY table
- `disability_support` - Replaces DISABILITY_SUPPORT table
- `language_cultural_data` - Replaces LANGUAGE_CULTURAL_PROFILE table
- `survey_responses` - Replaces SURVEY_QUESTION + SURVEY_RESPONSE tables
- `additional_services` - Replaces ADDITIONAL_SERVICE tables
- `gs_assessment` - Replaces GS_ASSESSMENT table
- `signature_data` - Replaces SIGNATURE_ENVELOPE + SIGNATURE_PARTY tables
- `form_metadata` - Submission metadata

**See `docs/SCHEMA_MIGRATION_v3.md` for detailed migration guide.**

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - Login with email/password
- `POST /refresh` - Refresh access token
- `POST /mfa/setup` - Generate MFA secret
- `POST /mfa/verify` - Enable MFA
- `POST /mfa/disable` - Disable MFA
- `GET /me` - Get current user info

### Applications (`/api/v1/applications`) - TODO
- `GET /applications` - List applications (filtered by RTO)
- `POST /applications` - Create application
- `GET /applications/{id}` - Get application details
- `PATCH /applications/{id}` - Update application
- `POST /applications/{id}/stage` - Change workflow stage

### Documents (`/api/v1/documents`) - TODO
- `POST /documents` - Upload document
- `GET /documents/{id}` - Download document
- `POST /documents/{id}/verify` - Verify document
- `GET /documents/{id}/versions` - List versions

### Timeline (`/api/v1/timeline`) - TODO
- `GET /applications/{id}/timeline` - Get application timeline
- `POST /applications/{id}/timeline` - Add timeline entry

## Environment Variables

See `.env.example` for all configuration options.

**Critical settings:**
- `POSTGRES_*` - Database connection
- `SECRET_KEY` - JWT signing key (generate with `openssl rand -hex 32`)
- `AZURE_*` - Azure services (Blob Storage, Form Recognizer, Communication)
- `REDIS_URL` - Redis for Celery

## Development Workflow

### Running Tests
```bash
pytest
pytest --cov=app tests/  # With coverage
```

### Code Quality
```bash
black .                  # Format code
flake8 .                 # Lint
mypy app/                # Type checking
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Celery Workers (Background Tasks)
```bash
# Start worker
celery -A app.celery_app worker --loglevel=info

# Start beat scheduler
celery -A app.celery_app beat --loglevel=info
```

## Multi-Tenancy & Row-Level Security

All queries automatically filtered by `rto_profile_id`:

```python
from app.api.dependencies import get_rto_filter

@router.get("/applications")
async def list_applications(
    rto_id: str = Depends(get_rto_filter),
    db: Session = Depends(get_db)
):
    # Automatically filtered to current user's RTO
    applications = db.query(Application).join(StudentProfile).join(UserAccount).filter(
        UserAccount.rto_profile_id == rto_id
    ).all()
```

## Role-Based Access Control (RBAC)

```python
from app.api.dependencies import require_admin, require_staff, RoleChecker

# Admin only
@router.post("/admin/users")
async def create_user(user: UserAccount = Depends(require_admin)):
    ...

# Staff or Admin
@router.get("/applications")
async def list_applications(user: UserAccount = Depends(require_staff)):
    ...

# Custom role check
@router.get("/reports")
async def generate_report(
    user: UserAccount = Depends(RoleChecker([UserRole.ADMIN, UserRole.STAFF]))
):
    ...
```

## Deployment to Hostinger VPS

1. **Provision VPS** (VPS 2: 2 vCPU, 4GB RAM)
2. **Install Docker + docker-compose**
3. **Clone repository**
4. **Configure `.env` with production values**
5. **Run `docker-compose --profile production up -d`**
6. **Set up SSL with Let's Encrypt** (automatic renewal via certbot)
7. **Configure Nginx reverse proxy** (included in `nginx/`)

## Next Steps

- [ ] Implement application CRUD endpoints
- [ ] Add document upload/OCR integration (Azure Form Recognizer)
- [ ] Create timeline feed endpoint
- [ ] Set up Celery tasks (email notifications, OCR processing)
- [ ] Add comprehensive tests
- [ ] Implement GS assessment workflow
- [ ] Add e-signature integration (DocuSeal)

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 ORM](https://docs.sqlalchemy.org/en/20/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)

## License

Proprietary - Churchill Education © 2025
