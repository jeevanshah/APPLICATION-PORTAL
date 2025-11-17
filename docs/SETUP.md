# 🚀 Setup Guide - Churchill Application Portal

Complete guide to get the Application Portal running locally with Docker.

---

## Quick Start (1 Command)

```powershell
.\start-docker.ps1
```

This automated script will:
1. ✅ Check Docker is installed and running
2. ✅ Create `.env` configuration with secure keys
3. ✅ Start PostgreSQL, Redis, FastAPI, Celery, pgAdmin
4. ✅ Run database migrations
5. ✅ Open API docs in browser

**Access Points:**
- **API Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (admin@admin.com / admin123)
- **Database**: localhost:5432 (churchill_user / churchill_password)

---

## Prerequisites

- **Docker Desktop** for Windows
  - Download: https://www.docker.com/products/docker-desktop
- **Git** (for cloning/pulling updates)
- **Code Editor** (VS Code recommended)

---

## Manual Setup

### 1. Create Environment File

```powershell
# Copy template
Copy-Item backend\.env.example backend\.env

# Edit if needed
notepad backend\.env
```

**Key Settings:**
```env
# Database (defaults work for Docker)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=churchill_user
POSTGRES_PASSWORD=churchill_password
POSTGRES_DB=churchill_portal

# Generate new secret key
SECRET_KEY=your_secret_key_here

# Development mode
DEBUG=True

# CORS for frontend
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Redis
REDIS_URL=redis://redis:6379/0
```

**Generate SECRET_KEY:**
```powershell
# Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Using PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

### 2. Start Docker Services

```powershell
# First time (builds images)
docker-compose up -d --build

# Subsequent starts
docker-compose up -d
```

### 3. Run Database Migrations

```powershell
# Wait for services to be healthy
docker-compose logs -f backend

# Once you see "Application startup complete", run migrations
docker-compose exec backend alembic upgrade head
```

### 4. Test the API

Visit http://localhost:8000/docs and try:
- POST /api/v1/auth/register - Create test user
- POST /api/v1/auth/login - Get access token
- Click 🔒 Authorize - Enter `Bearer YOUR_TOKEN`
- GET /api/v1/auth/me - Verify authentication

---

## Common Commands

### Service Management
```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Restart service
docker-compose restart backend

# Check service status
docker-compose ps
```

### Database Operations
```powershell
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Access PostgreSQL shell
docker-compose exec postgres psql -U churchill_user -d churchill_portal

# Quick query
docker-compose exec postgres psql -U churchill_user -d churchill_portal -c "SELECT email, role FROM user_account;"
```

### Container Access
```powershell
# Access backend shell
docker-compose exec backend /bin/bash

# Run Python in backend
docker-compose exec backend python -c "print('Hello from Docker')"

# Run tests (when implemented)
docker-compose exec backend pytest
```

### Clean Up
```powershell
# Stop services (keeps data)
docker-compose down

# Stop and delete database (fresh start)
docker-compose down -v
docker-compose up -d --build

# Full system cleanup
docker system prune -a
```

---

## Development Workflow

### Hot Reload (Automatic)
Backend has hot reload enabled. Just edit files and save:

```powershell
# Edit any Python file
code backend\app\api\v1\endpoints\applications.py

# Save (Ctrl+S) - Backend automatically reloads
# Watch logs to confirm:
docker-compose logs -f backend
```

### Adding Dependencies
```powershell
# 1. Edit requirements.txt
code backend\requirements.txt

# 2. Rebuild backend
docker-compose build backend

# 3. Restart
docker-compose restart backend
```

### Database Schema Changes
```powershell
# 1. Edit SQLAlchemy models
code backend\app\models\__init__.py

# 2. Generate migration
docker-compose exec backend alembic revision --autogenerate -m "Add new field"

# 3. Review migration
code backend\alembic\versions\*.py

# 4. Apply migration
docker-compose exec backend alembic upgrade head
```

---

## pgAdmin Setup

**Access**: http://localhost:5050

### Login
- Email: `admin@admin.com`
- Password: `admin123`

### Add Server Connection
1. Right-click **Servers** → **Register** → **Server**
2. **General Tab**: Name = `Churchill Portal`
3. **Connection Tab**:
   - Host: `postgres`
   - Port: `5432`
   - Database: `churchill_portal`
   - Username: `churchill_user`
   - Password: `churchill_password`
   - ✅ Save password
4. Click **Save**

### View Tables
1. Expand: **Servers** → **Churchill Portal** → **Databases** → **churchill_portal** → **Schemas** → **public** → **Tables**
2. Right-click table → **View/Edit Data** → **All Rows**

### Run Queries
1. Click database name
2. **Tools** → **Query Tool** (or `Alt+Shift+Q`)
3. Type SQL and press **F5**

**Example Queries:**
```sql
-- View all users
SELECT id, email, role, status FROM user_account;

-- View document types
SELECT name, code, is_mandatory FROM document_type ORDER BY display_order;

-- Count records
SELECT 'users' as table_name, COUNT(*) FROM user_account
UNION ALL
SELECT 'applications', COUNT(*) FROM application
UNION ALL
SELECT 'documents', COUNT(*) FROM document;
```

---

## Troubleshooting

### Problem: Containers won't start
```powershell
# Check logs
docker-compose logs

# Port conflict?
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Full reset
docker-compose down -v
docker-compose up -d --build
```

### Problem: Database connection errors
```powershell
# Check PostgreSQL is healthy
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

### Problem: Backend import errors
```powershell
# Rebuild without cache
docker-compose build --no-cache backend
docker-compose restart backend
```

### Problem: Migrations fail
```powershell
# Check current version
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Downgrade if needed
docker-compose exec backend alembic downgrade -1
```

### Problem: Port already in use
```powershell
# Find process using port
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID 1234 /F

# Or change port in docker-compose.yml
# ports: - "8001:8000"
```

---

## Frontend Setup (React + TypeScript)

### 1. Create React Project
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. Install Dependencies
```bash
npm install axios
npm install react-router-dom
npm install @tanstack/react-query
```

### 3. Create API Client

**`src/api/client.ts`:**
```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { username: email, password });
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },
  
  me: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

export const applicationsAPI = {
  create: async (data: { student_profile_id: string; course_offering_id: string }) => {
    const response = await apiClient.post('/applications', data);
    return response.data;
  },
  
  updateStep: async (appId: string, step: number, stepName: string, data: any) => {
    const response = await apiClient.patch(
      `/applications/${appId}/steps/${step}/${stepName}`,
      data
    );
    return response.data;
  },
};
```

### 4. Environment Variables

**`.env`:**
```env
VITE_API_URL=http://localhost:8000/api/v1
```

**`.env.production`:**
```env
VITE_API_URL=https://api.yourdomain.com/api/v1
```

### 5. Run Development Server
```bash
npm run dev
```

Open http://localhost:5173

---

## VS Code Integration

### Recommended Extensions
- **Docker** (ms-azuretools.vscode-docker)
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **PostgreSQL** (ckolkman.vscode-postgres)
- **Thunder Client** (rangav.vscode-thunder-client) - API testing

### Connect to Database in VS Code
1. Install PostgreSQL extension
2. Add connection:
   - Host: `localhost`
   - Port: `5432`
   - User: `churchill_user`
   - Password: `churchill_password`
   - Database: `churchill_portal`

---

## What's Running

### Services
- **churchill_backend** - FastAPI (port 8000)
- **churchill_postgres** - PostgreSQL 16 (port 5432)
- **churchill_redis** - Redis 7 (port 6379)
- **churchill_celery_worker** - Background tasks
- **churchill_celery_beat** - Scheduled tasks
- **churchill_pgadmin** - Database UI (port 5050)

### Volumes (Persistent Data)
- **postgres_data** - Database files
- **redis_data** - Redis persistence
- **pgadmin_data** - pgAdmin config
- **backend_uploads** - Uploaded documents

### Network
- **churchill_network** - Internal Docker network

---

## Next Steps

1. ✅ **Services running** - All containers healthy
2. 🧪 **Test API** - Create user, test endpoints in Swagger
3. 💾 **Create test data** - Student profiles, applications
4. 📄 **Test document upload** - Upload with OCR
5. 🎨 **Build frontend** - Connect to API

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Database UI**: http://localhost:5050
- **Architecture Guide**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **API Reference**: [API_GUIDE.md](./API_GUIDE.md)
- **Database Schema**: [DATABASE.md](./DATABASE.md)

---

**Need help?** Check logs: `docker-compose logs -f`
