#!/bin/bash
set -e

echo "=========================================="
echo "  Privra Mail Server Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    echo "   Run as regular user with sudo access"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo ""
    echo "Steps to configure:"
    echo "1. cp .env.example .env"
    echo "2. Edit .env with your settings"
    echo "3. Run this script again"
    exit 1
fi

# Load environment variables
source .env

# Validate required variables
if [ -z "$MAIL_DOMAIN" ] || [ -z "$MAIL_HOSTNAME" ] || [ -z "$DB_PASSWORD" ] || [ -z "$SECRET_KEY" ]; then
    echo "❌ Missing required variables in .env"
    echo "   Please configure MAIL_DOMAIN, MAIL_HOSTNAME, DB_PASSWORD, and SECRET_KEY"
    exit 1
fi

echo "✓ Configuration loaded"
echo "  Domain: $MAIL_DOMAIN"
echo "  Hostname: $MAIL_HOSTNAME"
echo ""

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✓ Docker installed"
    echo "⚠️  Please logout and login again to use Docker without sudo"
    exit 0
fi

# Install Docker Compose if not installed
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    echo "✓ Docker Compose installed"
fi

# Setup Let's Encrypt certificates
echo ""
echo "🔐 Setting up SSL certificates..."
echo ""

# Install certbot if not installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot
fi

# Create certs directory
mkdir -p certs

# Check if certificates already exist
if [ -d "/etc/letsencrypt/live/$MAIL_HOSTNAME" ]; then
    echo "✓ Certificates already exist, copying..."
    sudo cp /etc/letsencrypt/live/$MAIL_HOSTNAME/fullchain.pem certs/
    sudo cp /etc/letsencrypt/live/$MAIL_HOSTNAME/privkey.pem certs/
    sudo chown $USER:$USER certs/*.pem
else
    echo "Obtaining Let's Encrypt certificates..."
    echo "⚠️  Make sure:"
    echo "   - Port 80 is open"
    echo "   - DNS A record for $MAIL_HOSTNAME points to this server"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 1
    fi

    sudo certbot certonly --standalone \
        -d $MAIL_HOSTNAME \
        --non-interactive \
        --agree-tos \
        --email ${ADMIN_EMAIL:-admin@$MAIL_DOMAIN} \
        --preferred-challenges http

    if [ $? -eq 0 ]; then
        echo "✓ Certificates obtained!"
        sudo cp /etc/letsencrypt/live/$MAIL_HOSTNAME/fullchain.pem certs/
        sudo cp /etc/letsencrypt/live/$MAIL_HOSTNAME/privkey.pem certs/
        sudo chown $USER:$USER certs/*.pem
    else
        echo "❌ Failed to obtain certificates"
        echo "   Please check:"
        echo "   - Port 80 is accessible from internet"
        echo "   - DNS is configured correctly"
        exit 1
    fi
fi

# Set proper permissions
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem

echo "✓ SSL certificates configured"
echo ""

# Start services
echo "🚀 Starting mail server..."
echo ""

docker compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "=========================================="
echo "  ✅ Privra Mail Server Setup Complete!"
echo "=========================================="
echo ""
echo "📧 Admin Interface:"
echo "   https://$MAIL_HOSTNAME/admin"
echo "   Default login: admin / admin"
echo "   ⚠️  CHANGE THE DEFAULT PASSWORD!"
echo ""
echo "📱 Email Client Settings:"
echo "   IMAP Server: $MAIL_HOSTNAME"
echo "   IMAP Port: 993 (SSL/TLS)"
echo ""
echo "   SMTP Server: $MAIL_HOSTNAME"
echo "   SMTP Port: 587 (STARTTLS)"
echo ""
echo "🔧 Management Commands:"
echo "   Add user:    docker compose exec admin python manage.py adduser user@$MAIL_DOMAIN password"
echo "   Delete user: docker compose exec admin python manage.py deluser user@$MAIL_DOMAIN"
echo "   List users:  docker compose exec admin python manage.py listusers"
echo ""
echo "📋 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🔄 Certificate auto-renewal:"
echo "   Certificates will auto-renew via certbot"
echo ""
