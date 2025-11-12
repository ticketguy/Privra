#!/bin/bash

###################################
# Privra Mail Server Setup Script
###################################

set -e

echo "🚀 Privra Mail Server Setup"
echo "============================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use: sudo ./setup.sh)"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker is already installed"
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose plugin."
    exit 1
else
    echo "✅ Docker Compose is available"
fi

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📋 Creating .env from .env.example..."
        cp .env.example .env
        echo "✅ .env file created"
    else
        echo "❌ .env.example not found. Please ensure you're in the correct directory."
        exit 1
    fi
fi

# Generate SECRET_KEY if not set
if grep -q "CHANGE_ME_TO_RANDOM_STRING" .env; then
    echo "🔐 Generating SECRET_KEY..."
    SECRET_KEY=$(openssl rand -hex 16)
    sed -i "s|CHANGE_ME_TO_RANDOM_STRING|${SECRET_KEY}|" .env
    echo "✅ SECRET_KEY generated"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data dkim mail webmail filter certs overrides/nginx overrides/postfix overrides/dovecot overrides/rspamd overrides/webmail mailqueue
chmod -R 755 data dkim mail webmail filter certs overrides mailqueue
echo "✅ Directories created"

# Check DNS configuration
echo ""
echo "⚠️  IMPORTANT DNS CONFIGURATION"
echo "================================"
echo "Before starting, make sure you have these DNS records:"
echo ""
echo "A     mail.privra.com     -> YOUR_SERVER_IP"
echo "MX    privra.com          -> mail.privra.com (priority 10)"
echo "TXT   privra.com          -> 'v=spf1 mx ~all'"
echo "TXT   _dmarc.privra.com   -> 'v=DMARC1; p=quarantine; rua=mailto:admin@privra.com'"
echo ""
read -p "Have you configured DNS records? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⏸️  Please configure DNS first, then run this script again."
    exit 0
fi

# Ask for domain configuration
echo ""
echo "🌐 Domain Configuration"
echo "======================="
read -p "Enter your main domain (default: privra.com): " DOMAIN
DOMAIN=${DOMAIN:-privra.com}

read -p "Enter your mail hostname (default: mail.privra.com): " HOSTNAME
HOSTNAME=${HOSTNAME:-mail.$DOMAIN}

echo "Updating .env file with your domain..."
sed -i "s/DOMAIN=.*/DOMAIN=${DOMAIN}/" .env
sed -i "s/HOSTNAMES=.*/HOSTNAMES=${HOSTNAME}/" .env

echo "✅ Configuration updated"

# Pull Docker images
echo ""
echo "📥 Pulling Docker images (this may take a few minutes)..."
docker compose pull

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Review and customize .env file if needed"
echo "2. Start the mail server: docker compose up -d"
echo "3. Create your first admin user:"
echo "   docker compose exec admin flask mailu admin admin ${DOMAIN} PASSWORD"
echo "4. Access web interface at: https://${HOSTNAME}/admin"
echo "5. Access webmail at: https://${HOSTNAME}/webmail"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:    docker compose logs -f"
echo "   Stop server:  docker compose down"
echo "   Restart:      docker compose restart"
echo ""
