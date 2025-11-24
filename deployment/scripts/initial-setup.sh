#!/bin/bash

###############################################################################
# Churchill Application Portal - Initial VPS Setup Script
# Ubuntu 24.04 LTS on Hostinger VPS
# Run as root: sudo bash initial-setup.sh
###############################################################################

set -e  # Exit on any error

echo "============================================================================"
echo "Churchill Application Portal - VPS Initial Setup"
echo "============================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root: sudo bash initial-setup.sh"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essentials
echo "📦 Installing essential packages..."
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    ufw \
    fail2ban \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
echo "🐋 Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Verify Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose plugin not found"
    exit 1
else
    echo "✅ Docker Compose version: $(docker compose version)"
fi

# Setup firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
echo "✅ Firewall configured"

# Setup fail2ban
echo "🛡️  Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban
echo "✅ Fail2ban enabled"

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/churchill-portal
cd /opt/churchill-portal

# Create deployment user (optional, for security)
echo "👤 Creating deployment user..."
if ! id "churchill" &>/dev/null; then
    useradd -m -s /bin/bash churchill
    usermod -aG docker churchill
    echo "✅ User 'churchill' created and added to docker group"
else
    echo "✅ User 'churchill' already exists"
fi

# Create directories for backups and logs
mkdir -p /opt/churchill-portal/backups
mkdir -p /opt/churchill-portal/logs
chown -R churchill:churchill /opt/churchill-portal

echo ""
echo "============================================================================"
echo "✅ VPS Initial Setup Complete!"
echo "============================================================================"
echo ""
echo "Next steps:"
echo "1. Clone repository: git clone https://github.com/jeevanshah/APPLICATION-PORTAL.git"
echo "2. Copy deployment files to /opt/churchill-portal/"
echo "3. Configure .env.production with your secrets"
echo "4. Run deploy.sh to start the application"
echo ""
echo "Important:"
echo "- Default SSH port is still 22. Consider changing it for security."
echo "- Setup automatic backups for database"
echo "- Configure monitoring (optional but recommended)"
echo ""
