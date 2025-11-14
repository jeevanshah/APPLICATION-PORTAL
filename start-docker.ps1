# Churchill Application Portal - Docker Quick Start
# This script sets up and starts the Docker development environment

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Churchill Portal - Docker Development Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker not found!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://docker.com" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
Write-Host "`nChecking environment configuration..." -ForegroundColor Yellow
if (Test-Path "backend\.env") {
    Write-Host "✓ Environment file exists" -ForegroundColor Green
} else {
    Write-Host "⚠ Creating .env from template..." -ForegroundColor Yellow
    Copy-Item "backend\.env.example" "backend\.env"
    
    # Generate a random secret key
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    
    # Update .env with generated secret
    $envContent = Get-Content "backend\.env" -Raw
    $envContent = $envContent -replace "SECRET_KEY=your_secret_key_here.*", "SECRET_KEY=$secretKey"
    $envContent = $envContent -replace "DEBUG=False", "DEBUG=True"
    Set-Content "backend\.env" $envContent
    
    Write-Host "✓ Created .env with random SECRET_KEY" -ForegroundColor Green
    Write-Host "⚠ Review backend\.env for other settings" -ForegroundColor Yellow
}

# Ask to proceed
Write-Host "`n--------------------------------------------------" -ForegroundColor Cyan
Write-Host "Ready to start Docker services:" -ForegroundColor White
Write-Host "  • PostgreSQL 16 (port 5432)" -ForegroundColor White
Write-Host "  • Redis 7 (port 6379)" -ForegroundColor White
Write-Host "  • FastAPI Backend (port 8000)" -ForegroundColor White
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

$response = Read-Host "`nStart services now? (Y/n)"
if ($response -ne "" -and $response -ne "Y" -and $response -ne "y") {
    Write-Host "Setup cancelled." -ForegroundColor Yellow
    exit 0
}

# Start Docker services
Write-Host "`nStarting Docker services..." -ForegroundColor Yellow
Write-Host "(This may take 2-3 minutes on first run)" -ForegroundColor Gray

# Use simplified dev compose file
docker-compose -f docker-compose.dev.yml up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Services started successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose -f docker-compose.dev.yml logs" -ForegroundColor Yellow
    exit 1
}

# Wait for services to be healthy
Write-Host "`nWaiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service health
$backendHealthy = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $backendHealthy = $true
            break
        }
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }
}

Write-Host ""

if ($backendHealthy) {
    Write-Host "✓ Backend is healthy!" -ForegroundColor Green
} else {
    Write-Host "⚠ Backend might still be starting..." -ForegroundColor Yellow
    Write-Host "Check logs: docker-compose -f docker-compose.dev.yml logs -f backend" -ForegroundColor Gray
}

# Run migrations
Write-Host "`nRunning database migrations..." -ForegroundColor Yellow
docker exec churchill_backend alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Migrations completed!" -ForegroundColor Green
} else {
    Write-Host "⚠ No migrations to run (first time setup)" -ForegroundColor Yellow
    Write-Host "Generate initial migration with:" -ForegroundColor Gray
    Write-Host "  docker exec churchill_backend alembic revision --autogenerate -m 'Initial schema'" -ForegroundColor Gray
}

# Success summary
Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "🚀 Churchill Portal is running!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor Yellow
Write-Host "  • API Documentation:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • API ReDoc:          http://localhost:8000/redoc" -ForegroundColor White
Write-Host "  • Health Check:       http://localhost:8000/health" -ForegroundColor White
Write-Host "  • PostgreSQL:         localhost:5432" -ForegroundColor White
Write-Host "  • Redis:              localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  • View logs:          docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor White
Write-Host "  • Stop services:      docker-compose -f docker-compose.dev.yml down" -ForegroundColor White
Write-Host "  • Restart backend:    docker-compose -f docker-compose.dev.yml restart backend" -ForegroundColor White
Write-Host "  • Database shell:     docker exec -it churchill_postgres psql -U churchill_user -d churchill_portal" -ForegroundColor White
Write-Host "  • Backend shell:      docker exec -it churchill_backend /bin/bash" -ForegroundColor White
Write-Host ""
Write-Host "First steps:" -ForegroundColor Yellow
Write-Host "1. Open API docs: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "2. Try POST /api/v1/auth/register to create your first user" -ForegroundColor White
Write-Host "3. View logs: " -NoNewline -ForegroundColor White
Write-Host "docker-compose -f docker-compose.dev.yml logs -f backend" -ForegroundColor Cyan
Write-Host ""
Write-Host "Happy coding! 🎉" -ForegroundColor Green
Write-Host ""

# Ask if user wants to open browser
$openBrowser = Read-Host "Open API documentation in browser? (Y/n)"
if ($openBrowser -eq "" -or $openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "http://localhost:8000/docs"
}
