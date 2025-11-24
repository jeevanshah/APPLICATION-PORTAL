#!/bin/bash

###############################################################################
# Churchill Application Portal - SSL Certificate Setup
# Uses Let's Encrypt with Certbot
# Usage: bash setup-ssl.sh yourdomain.com
###############################################################################

set -e

DOMAIN=${1:-portal.churchilleducation.edu.au}
EMAIL=${2:-admin@churchilleducation.edu.au}

echo "============================================================================"
echo "SSL Certificate Setup for: $DOMAIN"
echo "============================================================================"
echo ""

# Verify domain points to this server
echo "🔍 Verifying DNS configuration..."
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

echo "Server IP: $SERVER_IP"
echo "Domain IP: $DOMAIN_IP"

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo "⚠️  Warning: Domain $DOMAIN does not point to this server ($SERVER_IP)"
    echo "Please update DNS records first:"
    echo "  Type: A"
    echo "  Host: @ (or subdomain)"
    echo "  Value: $SERVER_IP"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop nginx temporarily
echo "🛑 Stopping nginx..."
docker compose -f deployment/docker-compose.production.yml stop nginx

# Obtain certificate
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
docker compose -f deployment/docker-compose.production.yml run --rm certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate obtained successfully"
    
    # Update nginx configuration to enable HTTPS
    echo "📝 Updating nginx configuration..."
    
    # Uncomment HTTPS server block in nginx config
    sed -i 's/# server {/server {/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     listen/    listen/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     server_name/    server_name/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     ssl_/    ssl_/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     add_header/    add_header/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     location/    location/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/#     proxy_/    proxy_/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/# }/}/g' deployment/nginx/conf.d/backend.conf
    
    # Enable HTTP to HTTPS redirect
    sed -i 's/    # location \/ {/    location \/ {/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/    #     return 301/        return 301/g' deployment/nginx/conf.d/backend.conf
    sed -i 's/    # }/    }/g' deployment/nginx/conf.d/backend.conf
    
    # Restart nginx
    echo "🔄 Restarting nginx with SSL..."
    docker compose -f deployment/docker-compose.production.yml up -d nginx
    
    echo ""
    echo "============================================================================"
    echo "✅ SSL Setup Complete!"
    echo "============================================================================"
    echo ""
    echo "Your site is now accessible via HTTPS:"
    echo "  https://$DOMAIN/api/v1/"
    echo "  https://$DOMAIN/api/v1/admin-panel/"
    echo ""
    echo "Certificate will auto-renew via certbot container"
    echo ""
else
    echo "❌ Failed to obtain SSL certificate"
    echo "Starting nginx again..."
    docker compose -f deployment/docker-compose.production.yml start nginx
    exit 1
fi
