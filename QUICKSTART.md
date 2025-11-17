# 🚀 Quick Start - Churchill Application Portal

**For Frontend Developers**: Get the backend API running in under 2 minutes.

---

## Prerequisites

- ✅ **Docker Desktop** installed and running ([Download](https://www.docker.com/products/docker-desktop))
- ✅ **Git** (to clone the repo)

That's it! No Python or PostgreSQL installation needed.

---

## 🎯 Option 1: One Command (Recommended)

```powershell
.\quick-setup.ps1
```

**Done!** The script automatically:
1. ✅ Checks Docker is running
2. ✅ Creates `backend/.env` with secure keys
3. ✅ Starts all Docker services
4. ✅ Runs database migrations
5. ✅ Tests the API

**API ready at:** http://localhost:8000/docs

---

## 🎯 Option 2: Manual (3 Steps)

### 1. Clone & Navigate
```powershell
git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git
cd APPLICATION-PORTAL
```

### 2. Create Environment File
```powershell
# Copy the example file
Copy-Item backend\.env.example backend\.env

# Generate a secure random key and update .env (run this whole block)
$secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
(Get-Content backend\.env) -replace 'SECRET_KEY=.*', "SECRET_KEY=$secretKey" | Set-Content backend\.env
(Get-Content backend\.env) -replace 'DEBUG=False', 'DEBUG=True' | Set-Content backend\.env
(Get-Content backend\.env) -replace 'POSTGRES_HOST=localhost', 'POSTGRES_HOST=postgres' | Set-Content backend\.env
(Get-Content backend\.env) -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=churchill_password' | Set-Content backend\.env
```

### 3. Start Everything
```powershell
# Build and start all services (first time: ~2-3 minutes)
docker-compose up -d --build

# Wait 15 seconds for services to start
Start-Sleep -Seconds 15

# Run database migrations
docker exec churchill_backend alembic upgrade head
```

**Done!** 🎉

---

## ✅ Verify It's Working

Open in browser: **http://localhost:8000/docs**

You should see the interactive API documentation (Swagger UI).

---

## 📡 API Endpoints

| Endpoint | URL | Purpose |
|----------|-----|---------|
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **API Root** | http://localhost:8000 | API info |
| **Health Check** | http://localhost:8000/health | Server health status |
| **Database UI** | http://localhost:5050 | pgAdmin (admin@admin.com / admin123) |

**Base API URL for your frontend:**
```
http://localhost:8000/api/v1
```

---

## 🧪 Test the API (Optional)

### 1. Create a Test User
In Swagger UI (http://localhost:8000/docs):
- Find **POST /api/v1/auth/register**
- Click "Try it out"
- Use this JSON:
```json
{
  "email": "test@example.com",
  "password": "Test123!@#",
  "full_name": "Test User",
  "role": "student"
}
```
- Click "Execute"

### 2. Login to Get Access Token
- Find **POST /api/v1/auth/login**
- Click "Try it out"
- Enter:
  - username: `test@example.com`
  - password: `Test123!@#`
- Click "Execute"
- Copy the `access_token` from the response

### 3. Authorize (to test protected endpoints)
- Click the 🔒 **Authorize** button at the top
- Enter: `Bearer YOUR_ACCESS_TOKEN_HERE`
- Click "Authorize"

Now you can test all protected endpoints!

---

## 🛠️ Useful Commands

```powershell
# View live logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Restart backend (after code changes)
docker-compose restart backend

# Check service status
docker-compose ps

# Fresh start (deletes database!)
docker-compose down -v
docker-compose up -d --build
docker exec churchill_backend alembic upgrade head
```

---

## 🔌 Connecting Your Frontend

### Example: React with Axios

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

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

// Example: Login
export const login = async (email: string, password: string) => {
  const response = await apiClient.post('/auth/login', {
    username: email,
    password
  });
  localStorage.setItem('access_token', response.data.access_token);
  return response.data;
};

// Example: Get current user
export const getCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};
```

### CORS is already configured for:
- `http://localhost:3000` (Create React App, Next.js)
- `http://localhost:5173` (Vite)

---

## 📚 API Documentation

After starting the backend, explore the full API:
- **Swagger UI**: http://localhost:8000/docs (interactive)
- **ReDoc**: http://localhost:8000/redoc (readable)

**Available endpoints:**
- `/api/v1/auth/*` - Authentication & authorization
- `/api/v1/applications/*` - Application management
- `/api/v1/students/*` - Student profiles
- `/api/v1/documents/*` - Document upload & management

---

## 🐛 Troubleshooting

### "Docker is not running"
```powershell
# Start Docker Desktop, wait for it to start, then retry
docker --version
```

### "Port already in use"
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Stop that process or change the port in docker-compose.yml
```

### "Cannot connect to http://localhost:8000"
```powershell
# Check if backend is running
docker-compose ps

# View logs for errors
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### "Database errors"
```powershell
# Reset everything (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d --build
Start-Sleep -Seconds 15
docker exec churchill_backend alembic upgrade head
```

---

## 🎯 Next Time (Already Set Up)

If you already ran the setup before:

```powershell
# Just start the services
docker-compose up -d

# That's it! API is ready at http://localhost:8000
```

---

## 💡 Pro Tips

1. **Keep Docker Desktop running** while developing
2. **API docs are your friend** - http://localhost:8000/docs shows all endpoints with examples
3. **Check logs often** - `docker-compose logs -f backend` helps debug issues
4. **Hot reload enabled** - Backend auto-reloads when code changes (if you mount the volume)

---

## � More Documentation

Need more details?

- **`docs/SETUP.md`** - Comprehensive guide with troubleshooting, pgAdmin setup, development workflows
- **`docs/API_GUIDE.md`** - Complete API reference
- **`docs/DATABASE.md`** - Database schema details
- **`README.md`** - Project overview

---

**Ready to build your frontend!** 🚀

**API Base URL:** `http://localhost:8000/api/v1`
