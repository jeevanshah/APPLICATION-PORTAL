# 🐳 Churchill Application Portal - Local Docker Development

Complete guide to run the full stack locally with Docker.

## Prerequisites

- **Docker Desktop** for Windows (includes docker-compose)
  - Download: https://www.docker.com/products/docker-desktop
- **Git** (to clone/pull updates)
- **Code Editor** (VS Code recommended)

## Quick Start (5 Minutes)

### 1. Configure Environment

```powershell
# Navigate to project root
cd C:\Users\j.shah\Desktop\Projects\Application-Portal

# Create environment file from template
Copy-Item backend\.env.example backend\.env

# Edit .env file
notepad backend\.env
```

**Minimal `.env` configuration for local development:**
```env
# Database (defaults work for Docker)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=churchill_user
POSTGRES_PASSWORD=churchill_dev_password
POSTGRES_DB=churchill_portal

# Security (generate new secret key)
SECRET_KEY=your_secret_key_here_run_openssl_rand_hex_32
DEBUG=True

# CORS (allow React dev server)
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Redis
REDIS_URL=redis://redis:6379/0

# Optional: Leave Azure services empty for MVP
AZURE_STORAGE_CONNECTION_STRING=
AZURE_FORM_RECOGNIZER_ENDPOINT=
AZURE_FORM_RECOGNIZER_KEY=
```

**Generate SECRET_KEY:**
```powershell
# Option 1: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Using PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

### 2. Start Docker Services

```powershell
# Build and start all services (first time - takes 2-3 minutes)
docker-compose up -d --build

# Subsequent starts (faster)
docker-compose up -d
```

This starts:
- ✅ PostgreSQL 16 (port 5432)
- ✅ Redis 7 (port 6379)
- ✅ FastAPI backend (port 8000)
- ✅ Celery worker (background tasks)
- ✅ Celery beat (scheduled tasks)

### 3. Initialize Database

```powershell
# Wait for services to be healthy (check logs)
docker-compose logs -f backend

# Once you see "Application startup complete", press Ctrl+C

# Run database migrations
docker exec -it churchill_backend alembic upgrade head
```

### 4. Access the Application

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

### 5. Test Authentication

Open http://localhost:8000/docs and try:

1. **Register a new user** (`POST /api/v1/auth/register`)
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

2. **Login** (`POST /api/v1/auth/login`)
   - Username: `admin@test.com`
   - Password: `Test123!@#`
   - Copy the `access_token` from response

3. **Authorize** (click 🔒 button in Swagger UI)
   - Enter: `Bearer YOUR_ACCESS_TOKEN`

4. **Test protected endpoint** (`GET /api/v1/auth/me`)

## Docker Commands Reference

### Service Management

```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (DELETES DATABASE!)
docker-compose down -v

# Restart specific service
docker-compose restart backend

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f celery_worker

# Check service status
docker-compose ps
```

### Database Operations

```powershell
# Run migrations
docker exec -it churchill_backend alembic upgrade head

# Rollback last migration
docker exec -it churchill_backend alembic downgrade -1

# Create new migration
docker exec -it churchill_backend alembic revision --autogenerate -m "Description"

# Access PostgreSQL shell
docker exec -it churchill_postgres psql -U churchill_user -d churchill_portal

# Backup database
docker exec churchill_postgres pg_dump -U churchill_user churchill_portal > backup.sql

# Restore database
cat backup.sql | docker exec -i churchill_postgres psql -U churchill_user -d churchill_portal
```

### Container Shell Access

```powershell
# Access backend container shell
docker exec -it churchill_backend /bin/bash

# Run Python commands in backend
docker exec -it churchill_backend python -c "print('Hello from Docker')"

# Run Django/FastAPI management commands
docker exec -it churchill_backend python app/main.py
```

### Rebuild & Clean

```powershell
# Rebuild backend image (after dependency changes)
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache backend

# Remove all stopped containers, unused networks, images
docker system prune -a

# Remove only this project's volumes (DELETES DATA!)
docker-compose down -v
```

## Development Workflow

### 1. Code Changes (Hot Reload)

The backend service has **hot reload enabled**. Just edit files and save:

```powershell
# Edit a file in VS Code
code backend\app\api\v1\endpoints\auth.py

# Save changes (Ctrl+S)
# FastAPI automatically reloads (watch backend logs)
docker-compose logs -f backend
```

You'll see:
```
churchill_backend | INFO:     Uvicorn running on http://0.0.0.0:8000
churchill_backend | INFO:     Will watch for changes in these directories: ['/app']
churchill_backend | INFO:     Application startup complete.
```

### 2. Add New Dependencies

```powershell
# 1. Edit requirements.txt
code backend\requirements.txt

# 2. Rebuild backend image
docker-compose build backend

# 3. Restart backend service
docker-compose restart backend
```

### 3. Database Schema Changes

```powershell
# 1. Edit SQLAlchemy models
code backend\app\models\__init__.py

# 2. Generate migration
docker exec -it churchill_backend alembic revision --autogenerate -m "Add new column"

# 3. Review migration file
code backend\alembic\versions\*.py

# 4. Apply migration
docker exec -it churchill_backend alembic upgrade head
```

### 4. Run Tests

```powershell
# Run all tests
docker exec -it churchill_backend pytest

# Run with coverage
docker exec -it churchill_backend pytest --cov=app tests/

# Run specific test file
docker exec -it churchill_backend pytest tests/test_auth.py

# Run in watch mode (requires pytest-watch)
docker exec -it churchill_backend ptw
```

### 5. Code Quality Checks

```powershell
# Format code with Black
docker exec -it churchill_backend black .

# Lint with flake8
docker exec -it churchill_backend flake8 .

# Type checking with mypy
docker exec -it churchill_backend mypy app/
```

## Troubleshooting

### Problem: Containers won't start

```powershell
# Check logs
docker-compose logs

# Check specific service
docker-compose logs backend

# Common fixes:
# 1. Port conflict (another app using 8000, 5432, or 6379)
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# 2. Remove old containers and volumes
docker-compose down -v
docker-compose up -d --build
```

### Problem: Database connection errors

```powershell
# Check if PostgreSQL is healthy
docker-compose ps

# Should show "healthy" status for postgres
# If not, check logs:
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
docker exec -it churchill_backend alembic upgrade head
```

### Problem: Import errors in backend

```powershell
# Rebuild backend without cache
docker-compose build --no-cache backend
docker-compose restart backend
```

### Problem: "alembic: command not found"

```powershell
# This means you're trying to run alembic outside Docker
# Always use docker exec:
docker exec -it churchill_backend alembic upgrade head
```

### Problem: Hot reload not working

```powershell
# Check volume mounts in docker-compose.yml
# Should have: - ./backend:/app

# Restart backend with rebuild
docker-compose up -d --build backend
```

## VS Code Integration

### Recommended Extensions

- **Docker** (ms-azuretools.vscode-docker)
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Thunder Client** (rangav.vscode-thunder-client) - API testing
- **PostgreSQL** (ckolkman.vscode-postgres) - Database management

### Connect VS Code to Docker Container

1. Install "Remote - Containers" extension
2. Press `Ctrl+Shift+P` → "Remote-Containers: Attach to Running Container"
3. Select `churchill_backend`
4. Opens new VS Code window inside container

### Database Connection in VS Code

Install PostgreSQL extension, then add connection:
- Host: `localhost`
- Port: `5432`
- User: `churchill_user`
- Password: `churchill_dev_password`
- Database: `churchill_portal`

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | Database hostname (use `postgres` for Docker) |
| `POSTGRES_USER` | `churchill_user` | Database username |
| `POSTGRES_PASSWORD` | - | Database password (REQUIRED) |
| `POSTGRES_DB` | `churchill_portal` | Database name |
| `SECRET_KEY` | - | JWT signing key (REQUIRED - generate new) |
| `DEBUG` | `False` | Enable debug mode and SQL logging |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `BACKEND_CORS_ORIGINS` | `[]` | Allowed frontend origins (JSON array) |

## Performance Tips

### 1. Use Docker Compose Watch (Docker Desktop 4.24+)

```yaml
# Add to docker-compose.yml under backend service
develop:
  watch:
    - path: ./backend/app
      action: sync
      target: /app/app
```

Then run:
```powershell
docker-compose watch
```

### 2. Optimize Volume Performance

For Windows, enable WSL 2 backend in Docker Desktop settings for better I/O performance.

### 3. Limit Container Resources

Add to `docker-compose.yml`:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## Next Steps

1. ✅ **Setup complete** - Services running
2. 🔄 **Implement endpoints** - Add Application CRUD, Document upload
3. 🧪 **Write tests** - Add pytest tests for all endpoints
4. 📊 **Add monitoring** - Integrate logging, metrics
5. 🚀 **Deploy** - Push to Hostinger VPS

## Useful Docker Compose Snippets

### Start only database and Redis (no backend)

```powershell
docker-compose up -d postgres redis
```

Then run backend locally:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Run one-off commands

```powershell
# Create admin user via Python script
docker exec -it churchill_backend python -c "
from app.db.database import SessionLocal
from app.models import UserAccount, UserRole
from app.core.security import get_password_hash

db = SessionLocal()
admin = UserAccount(
    email='admin@churchill.edu.au',
    password_hash=get_password_hash('Admin123!'),
    role=UserRole.ADMIN,
    rto_profile_id='00000000-0000-0000-0000-000000000001'
)
db.add(admin)
db.commit()
print('Admin created!')
"
```

## Resources

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PostgreSQL 16 Docs](https://www.postgresql.org/docs/16/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)

---

**Happy coding! 🚀**

For issues, check logs: `docker-compose logs -f`
