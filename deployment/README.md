# 📦 Churchill Application Portal - Deployment Package

Complete production deployment package for Hostinger VPS deployment.

## 📁 Package Contents

```
deployment/
├── .env.production                    # Production environment template
├── docker-compose.production.yml      # Production Docker Compose config
├── DEPLOYMENT_GUIDE.md                # Complete deployment guide
├── README.md                          # This file
├── nginx/
│   ├── nginx.conf                     # Nginx main configuration
│   └── conf.d/
│       └── backend.conf               # Backend API proxy config
└── scripts/
    ├── initial-setup.sh               # Initial VPS setup
    ├── deploy.sh                      # Main deployment script
    ├── setup-ssl.sh                   # SSL certificate setup
    ├── backup-database.sh             # Database backup
    └── restore-database.sh            # Database restore
```

## 🚀 Quick Start

### 1. Connect to VPS
```bash
ssh root@72.61.225.229
```

### 2. Initial Setup (One-time)
```bash
cd /opt
git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git churchill-portal
cd churchill-portal
chmod +x deployment/scripts/*.sh
sudo bash deployment/scripts/initial-setup.sh
```

### 3. Configure Environment
```bash
cd deployment
cp .env.production .env.production.configured
nano .env.production.configured
```

**Update these values:**
- `POSTGRES_PASSWORD` - Generate with: `openssl rand -hex 32`
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `AZURE_*` - Your Azure credentials
- `DOCUSEAL_API_KEY` - Your DocuSeal API key
- `BACKEND_CORS_ORIGINS` - Your domain(s)

### 4. Deploy
```bash
bash deployment/scripts/deploy.sh
```

### 5. Setup SSL (Optional)
```bash
bash deployment/scripts/setup-ssl.sh portal.churchilleducation.edu.au
```

## 📋 System Requirements

- **OS:** Ubuntu 24.04 LTS
- **RAM:** 2GB minimum (4GB recommended)
- **Disk:** 20GB minimum (50GB recommended)
- **CPU:** 2 cores minimum
- **Ports:** 80, 443, 22 (SSH)

## 🔧 Common Commands

### Service Management
```bash
# View status
docker compose -f deployment/docker-compose.production.yml ps

# View logs
docker compose -f deployment/docker-compose.production.yml logs -f backend

# Restart services
docker compose -f deployment/docker-compose.production.yml restart

# Stop all
docker compose -f deployment/docker-compose.production.yml down

# Start all
docker compose -f deployment/docker-compose.production.yml up -d
```

### Database Operations
```bash
# Backup
bash deployment/scripts/backup-database.sh

# Restore
bash deployment/scripts/restore-database.sh /path/to/backup.sql.gz

# Run migrations
docker compose -f deployment/docker-compose.production.yml exec backend alembic upgrade head
```

### Updates
```bash
git pull origin main
bash deployment/scripts/deploy.sh
```

## 🔐 Security Notes

1. **Change Default Passwords**
   - Database password in `.env.production`
   - PgAdmin password in `.env.production`
   - Generate with: `openssl rand -hex 32`

2. **Firewall Configuration**
   - UFW is automatically configured by setup script
   - Only ports 22, 80, 443 are exposed
   - Database (5432) only accessible from Docker network

3. **SSL Certificate**
   - Use Let's Encrypt (free)
   - Run `setup-ssl.sh` after DNS configuration
   - Auto-renewal via certbot container

4. **Backups**
   - Setup automated daily backups
   - Add to crontab: `0 2 * * * /opt/churchill-portal/deployment/scripts/backup-database.sh`
   - Test restore procedure regularly

## 📞 Access Points

After deployment:

- **Backend API:** `http://72.61.225.229/api/v1/`
- **API Docs:** `http://72.61.225.229/api/v1/docs`
- **Admin Panel:** `http://72.61.225.229/api/v1/admin-panel/`
- **Health Check:** `http://72.61.225.229/health`

After SSL setup:
- **HTTPS API:** `https://portal.churchilleducation.edu.au/api/v1/`
- **HTTPS Admin:** `https://portal.churchilleducation.edu.au/api/v1/admin-panel/`

## 🐛 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker compose -f deployment/docker-compose.production.yml logs backend

# Check environment
docker compose -f deployment/docker-compose.production.yml exec backend env

# Restart specific service
docker compose -f deployment/docker-compose.production.yml restart backend
```

### Can't Connect to Database
```bash
# Test connection
docker compose -f deployment/docker-compose.production.yml exec postgres pg_isready

# Check credentials
cat deployment/.env.production | grep POSTGRES
```

### SSL Issues
```bash
# Check certificate
docker compose -f deployment/docker-compose.production.yml exec certbot certbot certificates

# Renew manually
docker compose -f deployment/docker-compose.production.yml exec certbot certbot renew --force-renewal
```

## 📚 Full Documentation

See `DEPLOYMENT_GUIDE.md` for complete step-by-step instructions.

## 🎯 Post-Deployment

After successful deployment:

1. ✅ Create admin user: `docker compose -f deployment/docker-compose.production.yml exec backend python scripts/admin_setup.py`
2. ✅ Configure RTO profile in admin panel
3. ✅ Add course offerings
4. ✅ Setup document types
5. ✅ Test document upload with OCR
6. ✅ Test offer letter generation
7. ✅ Configure automated backups

## 📊 Monitoring

```bash
# Server resources
htop

# Docker stats
docker stats

# Disk usage
df -h

# View all logs
docker compose -f deployment/docker-compose.production.yml logs -f
```

## 🔄 Updates & Maintenance

### Update Application
```bash
cd /opt/churchill-portal
git pull origin main
bash deployment/scripts/deploy.sh
```

### Clean Up Docker
```bash
docker system prune -a --volumes
```

### View Backup History
```bash
ls -lh /opt/churchill-portal/backups/
```

---

## ✅ Deployment Checklist

- [ ] VPS accessible via SSH
- [ ] Initial setup script completed
- [ ] Environment variables configured
- [ ] Application deployed successfully
- [ ] Health check passing
- [ ] Admin user created
- [ ] SSL certificate installed (optional)
- [ ] Domain DNS configured (optional)
- [ ] Automated backups setup
- [ ] Firewall configured
- [ ] All services running

---

**Support:** See `DEPLOYMENT_GUIDE.md` for detailed troubleshooting and operations guide.
