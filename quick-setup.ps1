# Churchill Application Portal - One-Command Setup
# Run this once to set up everything

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Churchill Portal - Quick Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

# Create .env if missing
Write-Host "`nSetting up environment..." -ForegroundColor Yellow
if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    
    # Generate secret key
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    
    # Update .env
    (Get-Content "backend\.env") -replace 'SECRET_KEY=.*', "SECRET_KEY=$secretKey" | Set-Content "backend\.env"
    (Get-Content "backend\.env") -replace 'DEBUG=False', 'DEBUG=True' | Set-Content "backend\.env"
    (Get-Content "backend\.env") -replace 'POSTGRES_HOST=localhost', 'POSTGRES_HOST=postgres' | Set-Content "backend\.env"
    (Get-Content "backend\.env") -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=churchill_password' | Set-Content "backend\.env"
    
    Write-Host "✓ Created backend\.env" -ForegroundColor Green
} else {
    Write-Host "✓ backend\.env exists" -ForegroundColor Green
}

# Start Docker services
Write-Host "`nStarting services (first time may take 2-3 minutes)..." -ForegroundColor Yellow
docker-compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    exit 1
}

# Wait for services
Write-Host "`nWaiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Run migrations
Write-Host "`nRunning database migrations..." -ForegroundColor Yellow
docker exec churchill_backend alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Migrations completed" -ForegroundColor Green
} else {
    Write-Host "⚠ Migrations may have already run" -ForegroundColor Yellow
}

# Test health
Write-Host "`nTesting API..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ API is healthy!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ API not responding yet (may need a few more seconds)" -ForegroundColor Yellow
}

# Success
Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your API is running at:" -ForegroundColor Yellow
Write-Host "  📚 API Docs:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  🔧 API Root:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "  ❤️  Health:    " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  🗄️  Database:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5050" -ForegroundColor Cyan
Write-Host ""
Write-Host "Base URL for frontend: " -NoNewline -ForegroundColor Yellow
Write-Host "http://localhost:8000/api/v1" -ForegroundColor Green
Write-Host ""
Write-Host "Common commands:" -ForegroundColor Yellow
Write-Host "  View logs:    docker-compose logs -f backend" -ForegroundColor Gray
Write-Host "  Stop all:     docker-compose down" -ForegroundColor Gray
Write-Host "  Restart:      docker-compose restart backend" -ForegroundColor Gray
Write-Host ""

# Ask to open browser
$openBrowser = Read-Host "Open API docs in browser? (Y/n)"
if ($openBrowser -eq "" -or $openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "http://localhost:8000/docs"
}
