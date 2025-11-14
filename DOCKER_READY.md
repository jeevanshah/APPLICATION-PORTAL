# 🐳 Docker Development - Ready to Start!

## ✅ What's Been Set Up

Your Churchill Application Portal is fully configured for Docker development:

### 1. Docker Configuration Files
- ✅ `docker-compose.dev.yml` - Simplified 3-service stack (PostgreSQL + Redis + FastAPI)
- ✅ `docker-compose.yml` - Full production stack (includes Nginx, Celery, SSL)
- ✅ `backend/Dockerfile` - Multi-stage FastAPI build
- ✅ `backend/.env` - Pre-configured development environment

### 2. Automation Scripts
- ✅ `start-docker.ps1` - One-command setup and start
- ✅ `setup.ps1` - Local Python environment setup

### 3. Documentation
- ✅ `QUICKSTART.md` - Quick reference for Docker commands
- ✅ `DOCKER_SETUP.md` - Comprehensive Docker development guide
- ✅ `README.md` - Updated with Docker quick start

### 4. Backend Application
- ✅ FastAPI with hot reload enabled
- ✅ SQLAlchemy models (16 tables)
- ✅ Pydantic schemas (JSONB models)
- ✅ Authentication API (8 endpoints)
- ✅ JWT + MFA (TOTP) security
- ✅ Role-based access control
- ✅ Alembic migrations ready

## 🚀 Start Development Now

### Step 1: Run the Setup Script

```powershell
cd C:\Users\j.shah\Desktop\Projects\Application-Portal
.\start-docker.ps1
```

**This will automatically:**
1. Check Docker installation
2. Create `.env` with secure random SECRET_KEY
3. Start PostgreSQL 16, Redis 7, FastAPI backend
4. Wait for services to be healthy
5. Run database migrations
6. Open API documentation in your browser

### Step 2: Test the API

Once the script completes, you'll see:
```
🚀 Churchill Portal is running!

Services:
  • API Documentation:  http://localhost:8000/docs
  • API ReDoc:          http://localhost:8000/redoc
  • Health Check:       http://localhost:8000/health
  • PostgreSQL:         localhost:5432
  • Redis:              localhost:6379
```

**Try it out:**
1. Go to http://localhost:8000/docs
2. Click **POST /api/v1/auth/register**
3. Click "Try it out"
4. Use this test data:
   ```json
   {
     "email": "admin@test.com",
     "password": "Test123!@#",
     "role": "admin",
     "rto_profile_id": "00000000-0000-0000-0000-000000000001",
     "given_name": "Admin",
     "family_name": "User"
   }
   ```
5. Click "Execute"
6. Copy the `access_token` from the response
7. Click 🔒 "Authorize" button at top
8. Enter: `Bearer YOUR_ACCESS_TOKEN`
9. Try **GET /api/v1/auth/me** to see your user info

### Step 3: Start Developing

**Code changes auto-reload!** Just edit files and save:
```powershell
# Open a file in VS Code
code backend\app\api\v1\endpoints\auth.py

# Make changes, save (Ctrl+S)
# Backend automatically reloads - check logs:
docker-compose -f docker-compose.dev.yml logs -f backend
```

**View logs in real-time:**
```powershell
docker-compose -f docker-compose.dev.yml logs -f
```

## 📋 Common Commands (Copy-Paste Ready)

### Daily Development
```powershell
# Start services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Stop services
docker-compose -f docker-compose.dev.yml down

# Restart backend (rarely needed - has hot reload)
docker-compose -f docker-compose.dev.yml restart backend
```

### Database Operations
```powershell
# Run migrations
docker exec churchill_backend alembic upgrade head

# Create migration after model changes
docker exec churchill_backend alembic revision --autogenerate -m "Add new field"

# Access PostgreSQL shell
docker exec -it churchill_postgres psql -U churchill_user -d churchill_portal

# Quick database queries
docker exec churchill_postgres psql -U churchill_user -d churchill_portal -c "SELECT * FROM user_account;"
```

### Debugging
```powershell
# Access backend container shell
docker exec -it churchill_backend /bin/bash

# Run Python in backend
docker exec churchill_backend python -c "from app.db.database import SessionLocal; print('DB connected!')"

# Check service status
docker-compose -f docker-compose.dev.yml ps

# View specific service logs
docker-compose -f docker-compose.dev.yml logs postgres
docker-compose -f docker-compose.dev.yml logs redis
docker-compose -f docker-compose.dev.yml logs backend
```

### Clean Up / Reset
```powershell
# Stop services (keeps data)
docker-compose -f docker-compose.dev.yml down

# Stop and delete database (fresh start)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d

# Rebuild backend after requirements.txt changes
docker-compose -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.dev.yml restart backend
```

## 🗂️ What's Running

When you start the services, Docker creates:

### Containers
- **churchill_postgres** - PostgreSQL 16 database
- **churchill_redis** - Redis 7 for caching/Celery
- **churchill_backend** - FastAPI application

### Volumes (Persistent Data)
- **postgres_data** - Database files (survives restarts)
- **redis_data** - Redis persistence
- **backend_uploads** - Uploaded files

### Network
- **churchill_network** - Internal Docker network for service communication

## 📊 Service Health Checks

The Docker setup includes automatic health checks:

**PostgreSQL**: Checks if database is accepting connections
```bash
pg_isready -U churchill_user
```

**Redis**: Pings Redis
```bash
redis-cli ping
```

**FastAPI**: HTTP health endpoint
```bash
http://localhost:8000/health
```

Services won't start until dependencies are healthy!

## 🎯 Next Steps for Development

### 1. Create Your First Migration
```powershell
# Generate initial schema migration
docker exec churchill_backend alembic revision --autogenerate -m "Initial v3.1 schema with 16 tables"

# Check the migration file
code backend\alembic\versions\*_initial_v3_1_schema.py

# Apply it
docker exec churchill_backend alembic upgrade head
```

### 2. Add Sample RTO Profile
```powershell
docker exec churchill_backend python -c "
from app.db.database import SessionLocal
from app.models import RtoProfile
from uuid import uuid4

db = SessionLocal()
churchill = RtoProfile(
    id=uuid4(),
    name='Churchill Education',
    abn='12345678901',
    cricos_code='03089G',
    contact_email='info@churchilleducation.edu.au',
    contact_phone='+61 2 1234 5678',
    is_active=True
)
db.add(churchill)
db.commit()
print(f'Created RTO: {churchill.id}')
"
```

### 3. Implement Application Endpoints
Create `backend/app/api/v1/endpoints/applications.py`:
```python
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user, require_staff

router = APIRouter()

@router.get("/")
async def list_applications(user = Depends(require_staff)):
    return {"message": "List applications here"}

@router.post("/")
async def create_application(user = Depends(get_current_user)):
    return {"message": "Create application here"}
```

Then register it in `backend/app/api/v1/__init__.py`

### 4. Add Tests
Create `backend/tests/test_auth.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "Test123!@#",
        "role": "student",
        "rto_profile_id": "00000000-0000-0000-0000-000000000001"
    })
    assert response.status_code == 201
```

Run tests:
```powershell
docker exec churchill_backend pytest
```

## 🐛 Troubleshooting

### Problem: Port 8000 already in use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill it (replace PID)
taskkill /PID 1234 /F

# Or change port in docker-compose.dev.yml
# ports: - "8001:8000"
```

### Problem: Docker daemon not running
```
Error: Cannot connect to the Docker daemon
```
**Solution**: Start Docker Desktop from Windows Start menu

### Problem: Services won't start
```powershell
# Check what failed
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs

# Full reset
docker-compose -f docker-compose.dev.yml down -v
docker system prune -f
docker-compose -f docker-compose.dev.yml up -d --build
```

### Problem: Database connection refused
```powershell
# Make sure PostgreSQL is healthy
docker-compose -f docker-compose.dev.yml ps postgres

# Should show "healthy" - if not, check logs:
docker-compose -f docker-compose.dev.yml logs postgres

# Reset database
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

## 📚 Documentation Quick Links

- **Quick Start**: [QUICKSTART.md](QUICKSTART.md) - Command cheat sheet
- **Docker Guide**: [DOCKER_SETUP.md](DOCKER_SETUP.md) - Full Docker documentation
- **Backend Docs**: [backend/README.md](backend/README.md) - Backend-specific info
- **Schema Docs**: [docs/data-model-diagram.md](docs/data-model-diagram.md) - Database schema
- **Architecture**: [docs/solution-architecture.md](docs/solution-architecture.md) - System design

## 🎉 You're Ready!

Everything is set up and ready to go. Just run:

```powershell
.\start-docker.ps1
```

And start building! The schema is locked, the foundation is solid, and hot reload makes development fast. 

**Happy coding! 🚀**

---

Need help? Check logs: `docker-compose -f docker-compose.dev.yml logs -f`
