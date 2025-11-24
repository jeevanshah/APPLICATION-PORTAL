#!/bin/bash

###############################################################################
# Churchill Application Portal - Database Backup Script
# Creates timestamped PostgreSQL database backups
# Usage: bash backup-database.sh
# Can be added to crontab for automated backups
###############################################################################

set -e

BACKUP_DIR="/opt/churchill-portal/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="churchill_portal_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30  # Keep backups for 30 days

echo "============================================================================"
echo "Database Backup - $(date)"
echo "============================================================================"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Perform backup
echo "📦 Creating database backup..."
docker compose -f /opt/churchill-portal/deployment/docker-compose.production.yml exec -T postgres \
    pg_dump -U churchill_user churchill_portal > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
echo "🗜️  Compressing backup..."
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
echo "✅ Backup created: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"

# Remove old backups
echo "🧹 Removing backups older than ${RETENTION_DAYS} days..."
find $BACKUP_DIR -name "churchill_portal_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Count remaining backups
BACKUP_COUNT=$(ls -1 $BACKUP_DIR/churchill_portal_backup_*.sql.gz 2>/dev/null | wc -l)
echo "📊 Total backups: $BACKUP_COUNT"

echo ""
echo "Backup complete: ${BACKUP_DIR}/${BACKUP_FILE}.gz"
echo ""

# Optional: Upload to cloud storage (uncomment and configure)
# echo "☁️  Uploading to cloud storage..."
# aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" s3://your-backup-bucket/churchill-portal/
# Or use Azure:
# az storage blob upload --account-name youraccount --container-name backups --name "${BACKUP_FILE}.gz" --file "${BACKUP_DIR}/${BACKUP_FILE}.gz"
