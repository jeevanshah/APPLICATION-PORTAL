# 🚀 Churchill Application Portal - Production Deployment Guide

## VPS Information
- **Provider:** Hostinger VPS
- **Server:** srv1142915.hstgr.cloud
- **IP Address:** 72.61.225.229
- **OS:** Ubuntu 24.04 LTS (KVM 8)
- **Expires:** 2027-11-21

---

## 📋 Prerequisites

### Required Services & Accounts
1. **Azure Account** (for OCR and storage)
   - Azure Storage Account
   - Azure Form Recognizer
   - Azure Communication Services (email)

2. **DocuSeal Account** (for offer letter signatures)
   - API Key
   - Webhook secret

3. **Domain Name** (recommended)
   - portal.churchilleducation.edu.au
   - Configure DNS A record to point to 72.61.225.229

4. **Email Service** (if not using Azure Communication Services)
   - SMTP credentials (Gmail, SendGrid, etc.)

---

## 🛠️ Deployment Steps

### Step 1: Connect to VPS

```bash
# SSH into your VPS
ssh root@72.61.225.229

# Or use SSH key
ssh -i /path/to/your-key.pem root@72.61.225.229
```

### Step 2: Initial Server Setup

```bash
# Download and run initial setup script
wget https://raw.githubusercontent.com/jeevanshah/APPLICATION-PORTAL/main/deployment/scripts/initial-setup.sh
chmod +x initial-setup.sh
sudo bash initial-setup.sh
```

**This script will:**
- ✅ Update Ubuntu packages
- ✅ Install Docker & Docker Compose
- ✅ Configure firewall (UFW)
- ✅ Setup fail2ban for security
- ✅ Create deployment directories
- ✅ Create 'churchill' user for deployment

### Step 3: Clone Repository

```bash
# Navigate to deployment directory
cd /opt/churchill-portal

# Clone the repository
git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git .

# Or if you prefer to clone to a subdirectory
git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git repo
cd repo
```

### Step 4: Configure Environment Variables

```bash
# Copy production environment template
cp deployment/.env.production deployment/.env.production.bak
nano deployment/.env.production
```

**Required Configuration:**

#### 1. Database Credentials
```env
POSTGRES_USER=churchill_user
POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>  # Use: openssl rand -hex 32
POSTGRES_DB=churchill_portal
```

#### 2. Security Secrets
```env
SECRET_KEY=<GENERATE_SECRET>  # Use: openssl rand -hex 32
```

#### 3. Azure Services
```env
# Get from Azure Portal > Storage Account
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=YOUR_ACCOUNT;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=documents

# Get from Azure Portal > Form Recognizer
AZURE_FORM_RECOGNIZER_ENDPOINT=https://YOUR_RESOURCE.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=YOUR_KEY

# Get from Azure Portal > Communication Services
AZURE_COMMUNICATION_CONNECTION_STRING=endpoint=https://YOUR_ACS.communication.azure.com/;accesskey=YOUR_KEY
```

#### 4. DocuSeal Integration
```env
DOCUSEAL_API_KEY=YOUR_DOCUSEAL_API_KEY
DOCUSEAL_API_URL=https://api.docuseal.co
DOCUSEAL_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
```

#### 5. CORS Origins (Update with your domain)
```env
BACKEND_CORS_ORIGINS=["https://portal.churchilleducation.edu.au","https://api.churchilleducation.edu.au","http://72.61.225.229"]
```

### Step 5: Deploy Application

```bash
# Make deployment script executable
chmod +x deployment/scripts/deploy.sh

# Run deployment
bash deployment/scripts/deploy.sh
```

**This script will:**
- ✅ Build Docker images
- ✅ Start all services (PostgreSQL, Redis, Backend, Celery, Nginx)
- ✅ Run database migrations
- ✅ Verify health checks

### Step 6: Verify Deployment

```bash
# Check running containers
docker compose -f deployment/docker-compose.production.yml ps

# Test health endpoint
curl http://72.61.225.229/health

# View logs
docker compose -f deployment/docker-compose.production.yml logs -f backend
```

**Access Points:**
- Backend API: `http://72.61.225.229/api/v1/`
- API Documentation: `http://72.61.225.229/api/v1/docs`
- Admin Panel: `http://72.61.225.229/api/v1/admin-panel/`
- Health Check: `http://72.61.225.229/health`

### Step 7: Setup SSL Certificate (Recommended)

```bash
# First, ensure your domain DNS points to 72.61.225.229
# Then run SSL setup
chmod +x deployment/scripts/setup-ssl.sh
bash deployment/scripts/setup-ssl.sh portal.churchilleducation.edu.au admin@churchilleducation.edu.au
```

**After SSL setup:**
- HTTPS: `https://portal.churchilleducation.edu.au/api/v1/`
- Auto-renewal: Certbot container handles renewal

### Step 8: Create Admin User

```bash
# Access backend container
docker compose -f deployment/docker-compose.production.yml exec backend bash

# Run admin setup script
python scripts/admin_setup.py

# Follow prompts to create admin user
# Email: admin@churchill.edu.au
# Password: <STRONG_PASSWORD>
```

### Step 9: Setup Automated Backups

```bash
# Make backup script executable
chmod +x deployment/scripts/backup-database.sh

# Test manual backup
bash deployment/scripts/backup-database.sh

# Add to crontab for daily backups at 2 AM
crontab -e

# Add this line:
0 2 * * * /opt/churchill-portal/deployment/scripts/backup-database.sh >> /opt/churchill-portal/logs/backup.log 2>&1
```

---

## 🔧 Maintenance & Operations

### View Logs
```bash
# All services
docker compose -f deployment/docker-compose.production.yml logs -f

# Specific service
docker compose -f deployment/docker-compose.production.yml logs -f backend
docker compose -f deployment/docker-compose.production.yml logs -f celery_worker
docker compose -f deployment/docker-compose.production.yml logs -f nginx
```

### Restart Services
```bash
# Restart all
docker compose -f deployment/docker-compose.production.yml restart

# Restart specific service
docker compose -f deployment/docker-compose.production.yml restart backend
```

### Update Application
```bash
# Pull latest code
cd /opt/churchill-portal
git pull origin main

# Rebuild and restart
bash deployment/scripts/deploy.sh
```

### Database Operations

#### Backup Database
```bash
bash deployment/scripts/backup-database.sh
```

#### Restore Database
```bash
# List backups
ls -lh /opt/churchill-portal/backups/

# Restore from backup
bash deployment/scripts/restore-database.sh /opt/churchill-portal/backups/churchill_portal_backup_20251124_120000.sql.gz
```

#### Access Database Directly
```bash
# Via psql
docker compose -f deployment/docker-compose.production.yml exec postgres psql -U churchill_user churchill_portal

# Via pgAdmin (if running)
# Access at http://72.61.225.229:5050
```

### Run Database Migrations
```bash
# Upgrade to latest
docker compose -f deployment/docker-compose.production.yml exec backend alembic upgrade head

# Rollback one migration
docker compose -f deployment/docker-compose.production.yml exec backend alembic downgrade -1

# View current version
docker compose -f deployment/docker-compose.production.yml exec backend alembic current
```

---

## 🔒 Security Checklist

- ✅ Change default SSH port (optional but recommended)
- ✅ Use SSH keys instead of passwords
- ✅ Enable UFW firewall (done by setup script)
- ✅ Enable fail2ban (done by setup script)
- ✅ Use strong passwords for all services
- ✅ Setup SSL/HTTPS
- ✅ Keep system packages updated: `apt update && apt upgrade`
- ✅ Regular database backups
- ✅ Restrict database access (only via Docker network)
- ✅ Monitor logs for suspicious activity

---

## 📊 Monitoring

### Check Resource Usage
```bash
# Server resources
htop

# Docker stats
docker stats

# Disk usage
df -h
```

### Health Checks
```bash
# Backend health
curl http://localhost/health

# Database connection
docker compose -f deployment/docker-compose.production.yml exec postgres pg_isready

# Redis health
docker compose -f deployment/docker-compose.production.yml exec redis redis-cli ping
```

---

## 🐛 Troubleshooting

### Backend Not Starting
```bash
# Check logs
docker compose -f deployment/docker-compose.production.yml logs backend

# Common issues:
# - Database connection failed: Check POSTGRES_* vars in .env
# - Migration errors: Check alembic version compatibility
# - Port conflicts: Ensure ports 80, 443, 5432 are available
```

### Database Connection Issues
```bash
# Verify PostgreSQL is running
docker compose -f deployment/docker-compose.production.yml ps postgres

# Test connection
docker compose -f deployment/docker-compose.production.yml exec postgres pg_isready -U churchill_user

# Check credentials
docker compose -f deployment/docker-compose.production.yml exec backend env | grep POSTGRES
```

### SSL Certificate Issues
```bash
# Check certificate status
docker compose -f deployment/docker-compose.production.yml exec certbot certbot certificates

# Manually renew
docker compose -f deployment/docker-compose.production.yml exec certbot certbot renew

# Check nginx error logs
docker compose -f deployment/docker-compose.production.yml logs nginx
```

### Out of Disk Space
```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old backups
find /opt/churchill-portal/backups -name "*.sql.gz" -mtime +60 -delete

# Check disk usage
du -sh /opt/churchill-portal/*
```

---

## 📱 Post-Deployment Checklist

- [ ] Backend accessible via HTTP/HTTPS
- [ ] Admin panel login working
- [ ] Database migrations applied
- [ ] Admin user created
- [ ] SSL certificate installed
- [ ] Automated backups configured
- [ ] Azure services connected (OCR working)
- [ ] Email sending configured
- [ ] Firewall rules verified
- [ ] Monitoring setup (optional)
- [ ] DNS configured for domain
- [ ] DocuSeal integration tested
- [ ] Document upload tested
- [ ] Test creating an application end-to-end

---

## 🔄 Rollback Procedure

If deployment fails:

```bash
# 1. Stop new deployment
docker compose -f deployment/docker-compose.production.yml down

# 2. Restore from backup
bash deployment/scripts/restore-database.sh /opt/churchill-portal/backups/pre_deploy_backup.sql.gz

# 3. Checkout previous version
git checkout <previous-commit-hash>

# 4. Redeploy
bash deployment/scripts/deploy.sh
```

---

## 📞 Support & Resources

- **GitHub Repository:** https://github.com/jeevanshah/APPLICATION-PORTAL
- **Documentation:** `/docs` folder in repository
- **API Documentation:** `https://your-domain.com/api/v1/docs`
- **Logs Location:** `/opt/churchill-portal/logs/`
- **Backups Location:** `/opt/churchill-portal/backups/`

---

## 🎉 Success!

Your Churchill Application Portal is now deployed and running!

**Next Steps:**
1. Login to admin panel
2. Configure RTO profile
3. Add course offerings
4. Setup document types
5. Create staff accounts
6. Test application workflow

**Important URLs:**
- Production API: `https://portal.churchilleducation.edu.au/api/v1/`
- Admin Panel: `https://portal.churchilleducation.edu.au/api/v1/admin-panel/`
- API Docs: `https://portal.churchilleducation.edu.au/api/v1/docs`
