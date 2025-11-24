#!/bin/bash

###############################################################################
# Churchill Application Portal - Database Restore Script
# Restores database from a backup file
# Usage: bash restore-database.sh backup_file.sql.gz
###############################################################################

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: Please specify backup file"
    echo "Usage: bash restore-database.sh /path/to/backup.sql.gz"
    echo ""
    echo "Available backups:"
    ls -lh /opt/churchill-portal/backups/churchill_portal_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "============================================================================"
echo "Database Restore"
echo "============================================================================"
echo ""
echo "⚠️  WARNING: This will OVERWRITE the current database!"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
echo

if [ "$REPLY" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

# Create a safety backup of current database
SAFETY_BACKUP="/opt/churchill-portal/backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
echo "🔒 Creating safety backup of current database..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml exec -T postgres \
    pg_dump -U churchill_user churchill_portal > "$SAFETY_BACKUP"
gzip "$SAFETY_BACKUP"
echo "✅ Safety backup created: ${SAFETY_BACKUP}.gz"

# Stop backend services
echo "🛑 Stopping backend services..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml stop backend celery_worker celery_beat

# Decompress if needed
RESTORE_FILE=$BACKUP_FILE
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "🗜️  Decompressing backup..."
    RESTORE_FILE="/tmp/restore_temp.sql"
    gunzip -c "$BACKUP_FILE" > "$RESTORE_FILE"
fi

# Drop and recreate database
echo "🗑️  Dropping existing database..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml exec -T postgres \
    psql -U churchill_user -c "DROP DATABASE IF EXISTS churchill_portal;"

echo "🏗️  Creating fresh database..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml exec -T postgres \
    psql -U churchill_user -c "CREATE DATABASE churchill_portal;"

# Restore from backup
echo "📥 Restoring database from backup..."
cat "$RESTORE_FILE" | docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml exec -T postgres \
    psql -U churchill_user churchill_portal

# Clean up temp file
if [[ $BACKUP_FILE == *.gz ]]; then
    rm -f "$RESTORE_FILE"
fi

# Restart services
echo "🚀 Restarting backend services..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml start backend celery_worker celery_beat

echo ""
echo "============================================================================"
echo "✅ Database Restore Complete!"
echo "============================================================================"
echo ""
echo "Restored from: $BACKUP_FILE"
echo "Safety backup: ${SAFETY_BACKUP}.gz"
echo ""
echo "Testing connection..."
sleep 3
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed. Check logs:"
    echo "   docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml logs backend"
fi
