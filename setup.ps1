# Churchill Application Portal - Setup Script (PowerShell)
# Run this script to set up the development environment

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Churchill Application Portal - Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.1[2-9]") {
    Write-Host "✓ $pythonVersion found" -ForegroundColor Green
} else {
    Write-Host "✗ Python 3.12+ required. Current: $pythonVersion" -ForegroundColor Red
    exit 1
}

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} else {
    Write-Host "⚠ Docker not found. Install from https://docker.com" -ForegroundColor Yellow
}

# Navigate to backend
Set-Location backend

# Create virtual environment
Write-Host "`nCreating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create .env file
Write-Host "`nConfiguring environment..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env from template" -ForegroundColor Green
    Write-Host "⚠ Please edit backend/.env with your settings" -ForegroundColor Yellow
}

# Return to root
Set-Location ..

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit backend/.env with your database credentials and secret key" -ForegroundColor White
Write-Host "2. Start services: docker-compose up -d" -ForegroundColor White
Write-Host "3. Run migrations: docker exec -it churchill_backend alembic upgrade head" -ForegroundColor White
Write-Host "4. Access API docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "For local development without Docker:" -ForegroundColor Yellow
Write-Host "1. Ensure PostgreSQL 16 and Redis are running" -ForegroundColor White
Write-Host "2. cd backend" -ForegroundColor White
Write-Host "3. .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "4. alembic upgrade head" -ForegroundColor White
Write-Host "5. uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
