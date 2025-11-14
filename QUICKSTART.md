# 🚀 Quick Start - Docker Development

## One-Command Setup

```powershell
.\start-docker.ps1
```

This script will:
1. ✅ Check Docker is installed and running
2. ✅ Create `.env` file if missing
3. ✅ Start PostgreSQL + Redis + FastAPI
4. ✅ Run database migrations
5. ✅ Open API docs in browser

## Manual Setup (Alternative)

```powershell
# 1. Copy environment file (if not exists)
Copy-Item backend\.env.example backend\.env

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d --build

# 3. Run migrations
docker exec churchill_backend alembic upgrade head

# 4. Open API docs
start http://localhost:8000/docs
```

## Useful Commands

### Service Management
```powershell
# View logs (all services)
docker-compose -f docker-compose.dev.yml logs -f

# View backend logs only
docker-compose -f docker-compose.dev.yml logs -f backend

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Restart backend (after code changes that need restart)
docker-compose -f docker-compose.dev.yml restart backend

# Check service status
docker-compose -f docker-compose.dev.yml ps
```

### Database
```powershell
# Access PostgreSQL shell
docker exec -it churchill_postgres psql -U churchill_user -d churchill_portal

# Run migrations
docker exec churchill_backend alembic upgrade head

# Create new migration (after model changes)
docker exec churchill_backend alembic revision --autogenerate -m "Description"

# View migration history
docker exec churchill_backend alembic history
```

### Backend Container
```powershell
# Access backend shell
docker exec -it churchill_backend /bin/bash

# Run Python commands
docker exec churchill_backend python -c "print('Hello from Docker!')"

# Run tests (when implemented)
docker exec churchill_backend pytest

# Format code
docker exec churchill_backend black .
```

## Access Points

- **API Swagger Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **PostgreSQL**: `localhost:5432` (user: `churchill_user`, password: `churchill_dev_password_123`)
- **Redis**: `localhost:6379`

## Test the API

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "role": "admin",
    "rto_profile_id": "00000000-0000-0000-0000-000000000001"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Test123!@#"
```

### 3. Use Swagger UI
1. Go to http://localhost:8000/docs
2. Click "POST /api/v1/auth/register"
3. Try it out with test data
4. Execute
5. Copy the `access_token`
6. Click 🔒 "Authorize" button
7. Enter: `Bearer YOUR_ACCESS_TOKEN`
8. Try protected endpoints like `GET /api/v1/auth/me`

## Troubleshooting

### Services won't start
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Remove old containers and start fresh
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d --build
```

### Backend shows import errors
```powershell
# Rebuild without cache
docker-compose -f docker-compose.dev.yml build --no-cache backend
docker-compose -f docker-compose.dev.yml restart backend
```

### Database connection failed
```powershell
# Check if PostgreSQL is healthy
docker-compose -f docker-compose.dev.yml ps

# View PostgreSQL logs
docker-compose -f docker-compose.dev.yml logs postgres

# Reset everything (DELETES DATA!)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

## Development Workflow

1. **Code changes**: Just save files - FastAPI hot-reloads automatically ✨
2. **Model changes**: Run `docker exec churchill_backend alembic revision --autogenerate -m "msg"`
3. **Dependency changes**: Edit `requirements.txt` → rebuild: `docker-compose -f docker-compose.dev.yml build backend`
4. **View logs**: `docker-compose -f docker-compose.dev.yml logs -f backend`

## Clean Up

```powershell
# Stop services (keeps data)
docker-compose -f docker-compose.dev.yml down

# Stop and delete all data (fresh start)
docker-compose -f docker-compose.dev.yml down -v

# Full system cleanup
docker system prune -a
```

---

**🎉 Happy coding!**

For detailed documentation, see [DOCKER_SETUP.md](DOCKER_SETUP.md)
