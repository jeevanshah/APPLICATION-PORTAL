# 🗄️ Database Guide - Churchill Application Portal

Complete database schema reference and management guide.

---

## Schema Overview

**PostgreSQL 16** with **16 tables** using JSONB-first architecture (53% reduction from v1.0)

### Core Identity & Multi-tenancy (5 tables)
1. `rto_profile` - Organization/RTO metadata
2. `user_account` - Unified authentication (all roles)
3. `agent_profile` - Agent-specific data
4. `staff_profile` - Staff-specific data
5. `student_profile` - Student-specific data

### Application Workflow (3 tables)
6. `course_offering` - Course catalog
7. `application` - Central record with **10 JSONB fields**
8. `application_stage_history` - Workflow state transitions

### History (Normalized for Performance - 3 tables)
9. `schooling_history` - Educational background
10. `qualification_history` - Certifications
11. `employment_history` - Work experience

### Document Management (3 tables)
12. `document_type` - Document type definitions
13. `document` - Document records
14. `document_version` - File versions with OCR data

### Activity & Compliance (2 tables)
15. `timeline_entry` - Activity feed
16. `audit_log` - System audit trail

---

## JSONB Consolidation

**19 former tables → 10 JSONB fields** in `application` table:

| JSONB Field | Purpose | Example Data |
|-------------|---------|--------------|
| `enrollment_data` | Course enrollment details | Start date, mode, campus |
| `emergency_contacts` | Emergency contact list | [{name, phone, relationship}] |
| `health_cover_policy` | OSHC insurance details | Provider, policy #, dates |
| `disability_support` | Support requirements | Type, accommodations needed |
| `language_cultural_data` | Language & cultural info | First language, proficiency |
| `survey_responses` | Pre-enrollment survey | [{question, answer}] |
| `additional_services` | Selected services | Airport pickup, accommodation |
| `gs_assessment` | GS workflow data | Documents, interview notes |
| `signature_data` | E-signature records | Timestamp, IP, signed document |
| `form_metadata` | Progress tracking | Completed steps, last saved |

**Benefits:**
- Fewer JOIN operations (better performance)
- Easier API responses (nested JSON)
- Flexible schema evolution
- Reduced table count

---

## Key Tables

### application
```sql
CREATE TABLE application (
    id UUID PRIMARY KEY,
    student_profile_id UUID REFERENCES student_profile,
    course_offering_id UUID REFERENCES course_offering,
    agent_profile_id UUID REFERENCES agent_profile,
    staff_profile_id UUID REFERENCES staff_profile,
    current_stage VARCHAR(50),
    usi VARCHAR(10),
    
    -- 10 JSONB fields
    enrollment_data JSONB,
    emergency_contacts JSONB,
    health_cover_policy JSONB,
    disability_support JSONB,
    language_cultural_data JSONB,
    survey_responses JSONB,
    additional_services JSONB,
    gs_assessment JSONB,
    signature_data JSONB,
    form_metadata JSONB,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### document
```sql
CREATE TABLE document (
    id UUID PRIMARY KEY,
    application_id UUID REFERENCES application,
    document_type_id UUID REFERENCES document_type,
    status VARCHAR(50), -- PENDING, APPROVED, REJECTED
    uploaded_by UUID REFERENCES user_account,
    uploaded_at TIMESTAMP,
    ocr_status VARCHAR(50), -- PENDING, PROCESSING, COMPLETED, FAILED
    ocr_completed_at TIMESTAMP,
    gs_document_requests JSONB
);
```

### document_version
```sql
CREATE TABLE document_version (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES document,
    blob_url VARCHAR(1000),
    checksum VARCHAR(64),  -- SHA256
    file_size_bytes INTEGER,
    version_number INTEGER,
    ocr_json JSONB,  -- Raw OCR extraction results
    preview_url VARCHAR(1000),
    created_at TIMESTAMP
);
```

---

## pgAdmin Setup

**Access:** http://localhost:5050

### Login Credentials
- **Email:** `admin@admin.com`
- **Password:** `admin123`

### Add Server Connection

1. Right-click **Servers** → **Register** → **Server**

2. **General Tab:**
   - Name: `Churchill Portal`

3. **Connection Tab:**
   - Host: `postgres`
   - Port: `5432`
   - Database: `churchill_portal`
   - Username: `churchill_user`
   - Password: `churchill_password`
   - ✅ Save password

4. Click **Save**

### View Data

**Tables:**
Expand: **Servers** → **Churchill Portal** → **Databases** → **churchill_portal** → **Schemas** → **public** → **Tables**

Right-click table → **View/Edit Data** → **All Rows**

**Run Queries:**
Click database → **Tools** → **Query Tool** (or `Alt+Shift+Q`)

---

## Common Queries

### View All Users
```sql
SELECT id, email, role, status, created_at 
FROM user_account 
ORDER BY created_at DESC;
```

### View Document Types
```sql
SELECT 
    name,
    code,
    is_mandatory,
    ocr_enabled,
    display_order
FROM document_type 
ORDER BY display_order;
```

### Count Records by Table
```sql
SELECT 'users' as table_name, COUNT(*) as count FROM user_account
UNION ALL
SELECT 'applications', COUNT(*) FROM application
UNION ALL
SELECT 'documents', COUNT(*) FROM document
UNION ALL
SELECT 'document_types', COUNT(*) FROM document_type;
```

### View Application Progress
```sql
SELECT 
    a.id,
    s.given_name || ' ' || s.family_name as student_name,
    a.current_stage,
    a.form_metadata->>'completed_sections' as completed_steps,
    a.created_at
FROM application a
JOIN student_profile s ON a.student_profile_id = s.id
ORDER BY a.created_at DESC
LIMIT 10;
```

### View Documents with OCR Status
```sql
SELECT 
    d.id,
    dt.name as document_type,
    d.status,
    d.ocr_status,
    d.uploaded_at,
    u.email as uploaded_by
FROM document d
JOIN document_type dt ON d.document_type_id = dt.id
JOIN user_account u ON d.uploaded_by = u.id
ORDER BY d.uploaded_at DESC;
```

### Query JSONB Fields
```sql
-- Get applications with completed personal details
SELECT 
    id,
    form_metadata->'completed_sections' as completed_sections
FROM application
WHERE form_metadata->'completed_sections' @> '["personal_details"]';

-- Get emergency contacts
SELECT 
    id,
    emergency_contacts
FROM application
WHERE emergency_contacts IS NOT NULL;
```

---

## Migration History

### Migrations Applied

1. **Initial v3.1 schema (1205e3db7232)**
   - Created 16 core tables
   - Set up JSONB fields
   - Added indexes and constraints

2. **Seed Churchill RTO profile (98fd831bc63e)**
   - Created Churchill Education RTO
   - CRICOS: 03089G
   - Set as active

3. **Seed document types (5ec10257251b)**
   - Created 13 document types
   - Set mandatory flags
   - Configured OCR models

### Running Migrations

```powershell
# View current version
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Apply all migrations
docker-compose exec backend alembic upgrade head

# Rollback last migration
docker-compose exec backend alembic downgrade -1

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

---

## Database Access

### via Docker Compose

```powershell
# Access PostgreSQL shell
docker-compose exec postgres psql -U churchill_user -d churchill_portal

# Quick query
docker-compose exec postgres psql -U churchill_user -d churchill_portal -c "SELECT COUNT(*) FROM user_account;"
```

### via psql Commands

```sql
-- List all tables
\dt

-- Describe table structure
\d application

-- List indexes
\di

-- List schemas
\dn

-- Quit
\q
```

### via Python Script

```python
from app.db.database import SessionLocal
from app.models import UserAccount, Application

db = SessionLocal()

# Query users
users = db.query(UserAccount).all()
for user in users:
    print(f"{user.email} - {user.role}")

# Query applications
apps = db.query(Application).all()
print(f"Total applications: {len(apps)}")

db.close()
```

---

## Backup & Restore

### Backup Database

```powershell
# Full backup
docker-compose exec postgres pg_dump -U churchill_user churchill_portal > backup.sql

# Backup with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker-compose exec postgres pg_dump -U churchill_user churchill_portal > "backup_$timestamp.sql"
```

### Restore Database

```powershell
# Restore from backup
cat backup.sql | docker-compose exec -T postgres psql -U churchill_user -d churchill_portal
```

### Export Specific Table

```powershell
# Export as CSV
docker-compose exec postgres psql -U churchill_user -d churchill_portal -c "\COPY user_account TO '/tmp/users.csv' CSV HEADER"
```

---

## Performance Tips

### Index Usage

```sql
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### JSONB Indexing

```sql
-- Create GIN index on JSONB field for faster queries
CREATE INDEX idx_form_metadata 
ON application USING GIN (form_metadata);

-- Query using index
SELECT * FROM application 
WHERE form_metadata @> '{"completed_sections": ["personal_details"]}';
```

### Query Analysis

```sql
-- Explain query plan
EXPLAIN ANALYZE 
SELECT * FROM application WHERE current_stage = 'DRAFT';
```

---

## Connection Details

### Local Development

| Setting | Value |
|---------|-------|
| Host (external) | `localhost` |
| Host (Docker) | `postgres` |
| Port | `5432` |
| Database | `churchill_portal` |
| Username | `churchill_user` |
| Password | `churchill_password` |

### Connection String

```
postgresql://churchill_user:churchill_password@localhost:5432/churchill_portal
```

---

## Alternative Database Tools

### 1. DBeaver (Desktop App)

Download: https://dbeaver.io/download/

**Connection:**
- Host: `localhost`
- Port: `5432`
- Database: `churchill_portal`
- Username: `churchill_user`
- Password: `churchill_password`

### 2. VS Code Extension

**PostgreSQL by Chris Kolkman**

1. Install extension
2. Press `Ctrl+Shift+P`
3. "PostgreSQL: New Connection"
4. Enter same credentials

### 3. Command Line (psql)

```powershell
# Already working if Docker is running
docker-compose exec postgres psql -U churchill_user -d churchill_portal
```

---

## Troubleshooting

### Cannot Connect to Database

```powershell
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Password Authentication Failed

```powershell
# Check environment variables
docker-compose exec postgres env | findstr POSTGRES

# Verify backend .env file matches docker-compose.yml
# Should be: churchill_password (not churchill_dev_password_123)
```

### Database Reset (Fresh Start)

```powershell
# Stop all services
docker-compose down

# Remove database volume
docker volume rm application-portal_postgres_data

# Start and run migrations
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

---

## Schema Diagram

```
rto_profile
    ↓
user_account → agent_profile
             → staff_profile  
             → student_profile
                    ↓
course_offering → application ← document_type
                      ↓              ↓
              timeline_entry      document
              audit_log              ↓
              schooling_history   document_version
              qualification_history
              employment_history
              application_stage_history
```

---

## Next Steps

1. **Explore Data**: Use pgAdmin to view tables
2. **Run Queries**: Try the example queries above
3. **Backup**: Set up regular backup schedule
4. **Monitor**: Watch for slow queries
5. **Optimize**: Add indexes as needed

For API usage, see [API_GUIDE.md](./API_GUIDE.md)  
For setup instructions, see [SETUP.md](./SETUP.md)
