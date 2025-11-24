#!/bin/bash

###############################################################################
# Churchill Application Portal - Production Deployment Script
# Run from /opt/churchill-portal directory
# Usage: bash deploy.sh
###############################################################################

set -e  # Exit on any error

echo "============================================================================"
echo "Churchill Application Portal - Production Deployment"
echo "============================================================================"
echo ""

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please copy deployment/.env.production and configure it with your secrets"
    exit 1
fi

# Check if required secrets are set
if grep -q "CHANGE_ME" .env.production; then
    echo "❌ Error: Please update all CHANGE_ME values in .env.production"
    exit 1
fi

echo "📋 Checking prerequisites..."

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Pull latest code (if in git repo)
if [ -d ".git" ]; then
    echo "📥 Pulling latest code from GitHub..."
    git pull origin main
    echo "✅ Code updated"
fi

# Build Docker images
echo "🔨 Building Docker images..."
docker compose -f deployment/docker-compose.production.yml build --no-cache

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose -f deployment/docker-compose.production.yml down

# Start services
echo "🚀 Starting production services..."
docker compose -f deployment/docker-compose.production.yml up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🗄️  Running database migrations..."
docker compose -f deployment/docker-compose.production.yml exec -T backend alembic upgrade head

# Check service health
echo "🏥 Checking service health..."
sleep 5

if docker compose -f deployment/docker-compose.production.yml ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker compose -f deployment/docker-compose.production.yml logs"
    exit 1
fi

# Test backend health endpoint
echo "🔍 Testing backend health..."
max_attempts=10
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Backend health check failed after $max_attempts attempts"
        echo "Check logs with: docker compose -f deployment/docker-compose.production.yml logs backend"
        exit 1
    fi
    
    echo "⏳ Waiting for backend... (attempt $attempt/$max_attempts)"
    sleep 3
    ((attempt++))
done

echo ""
echo "============================================================================"
echo "✅ Deployment Complete!"
echo "============================================================================"
echo ""
echo "Services Status:"
docker compose -f deployment/docker-compose.production.yml ps
echo ""
echo "Access Points:"
echo "  - Backend API: http://72.61.225.229/api/v1/"
echo "  - Admin Panel: http://72.61.225.229/api/v1/admin-panel/"
echo "  - API Docs: http://72.61.225.229/api/v1/docs"
echo "  - Health Check: http://72.61.225.229/health"
echo ""
echo "Next Steps:"
echo "  1. Setup SSL certificate (run setup-ssl.sh)"
echo "  2. Configure domain DNS to point to 72.61.225.229"
echo "  3. Setup automated backups (backup-database.sh)"
echo "  4. Monitor logs: docker compose -f deployment/docker-compose.production.yml logs -f"
echo ""
