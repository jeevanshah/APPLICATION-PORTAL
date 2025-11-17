# pgAdmin Setup Guide

## Access pgAdmin Web UI

**URL**: http://localhost:5050

**Default Credentials**:
- Email: `admin@churchill.local`
- Password: `admin123`

## First Time Setup - Connect to Database

After logging in to pgAdmin, you need to add your PostgreSQL server:

### Step 1: Add New Server
1. Right-click on "Servers" in the left sidebar
2. Select **Register** → **Server**

### Step 2: General Tab
- **Name**: `Churchill Portal` (or any name you like)

### Step 3: Connection Tab
- **Host name/address**: `postgres` (this is the Docker service name)
- **Port**: `5432`
- **Maintenance database**: `churchill_portal`
- **Username**: `churchill_user`
- **Password**: `churchill_password`
- ✅ Check **Save password**

### Step 4: Click Save

Your database will now appear in the sidebar!

## Using pgAdmin

### View Tables
1. Expand: **Servers** → **Churchill Portal** → **Databases** → **churchill_portal** → **Schemas** → **public** → **Tables**
2. Right-click any table → **View/Edit Data** → **All Rows**

### Run SQL Queries
1. Click on `churchill_portal` database
2. Click **Tools** → **Query Tool** (or press `Alt+Shift+Q`)
3. Type your SQL and press **F5** to execute

### Example Queries to Try

```sql
-- View all users
SELECT id, email, role, status FROM user_account;

-- View all document types
SELECT id, name, code, is_mandatory, ocr_enabled FROM document_type ORDER BY display_order;

-- View RTO profile
SELECT * FROM rto_profile;

-- Count records in each table
SELECT 'users' as table_name, COUNT(*) as count FROM user_account
UNION ALL
SELECT 'document_types', COUNT(*) FROM document_type
UNION ALL
SELECT 'applications', COUNT(*) FROM application
UNION ALL
SELECT 'documents', COUNT(*) FROM document;
```

## Other Database UI Options

### Option 2: DBeaver (Desktop App)
- Download: https://dbeaver.io/download/
- Connection:
  - Host: `localhost`
  - Port: `5432`
  - Database: `churchill_portal`
  - Username: `churchill_user`
  - Password: `churchill_password`

### Option 3: VS Code Extension
Install: **PostgreSQL** by Chris Kolkman
- Press `Ctrl+Shift+P`
- Type: "PostgreSQL: New Connection"
- Enter same credentials as above

### Option 4: Command Line (psql)
```powershell
# Already working in your terminal
docker-compose exec postgres psql -U churchill_user -d churchill_portal

# List all tables
\dt

# Describe table structure
\d table_name

# Run queries
SELECT * FROM user_account;
```

## Useful pgAdmin Features

### 1. View Table Structure
- Right-click table → **Properties** → **Columns** tab

### 2. Visual Query Builder
- Right-click table → **Query Tool**
- Click **View** → **Geometry Visualiser**

### 3. Export Data
- View data → Click **Download as CSV** icon
- Or right-click table → **Backup**

### 4. Monitor Connections
- Click **Dashboard** tab to see active connections and queries

### 5. Database Diagrams
- Right-click **Databases** → **ERD For Database**
- Visualize table relationships!

## Tips

- **Refresh**: Press `F5` to refresh the tree view
- **Dark Mode**: File → Preferences → Miscellaneous → Theme
- **Font Size**: File → Preferences → Browser → Display
- **Auto-commit**: Make sure it's ON for testing (usually default)

## Database Credentials Reference

| Setting | Value |
|---------|-------|
| Host (external) | `localhost` |
| Host (Docker) | `postgres` |
| Port | `5432` |
| Database | `churchill_portal` |
| Username | `churchill_user` |
| Password | `churchill_password` |

## Next Steps

Now that you can see the database:

1. **Explore existing data**: Check users, document types, RTO profile
2. **Create test data**: Add student profile, course offering, application
3. **Monitor uploads**: Watch documents table as you upload files
4. **View OCR results**: Check the `extracted_data` JSONB field after upload

Enjoy exploring your database! 🚀
