#!/bin/bash

###################################
# Update .env with latest fixes
###################################

set -e

echo "🔄 Updating .env configuration..."
echo "================================="
echo ""

# Backup existing .env if it exists
if [ -f .env ]; then
    echo "📦 Backing up current .env to .env.backup..."
    cp .env .env.backup
fi

# Create fresh .env from .env.example
echo "📋 Creating new .env from .env.example..."
cp .env.example .env

# Generate SECRET_KEY
echo "🔐 Generating new SECRET_KEY..."
SECRET_KEY=$(openssl rand -hex 16)
sed -i "s|CHANGE_ME_TO_RANDOM_STRING|${SECRET_KEY}|" .env
echo "✅ SECRET_KEY generated"

# Update domain settings if old backup exists
if [ -f .env.backup ]; then
    OLD_DOMAIN=$(grep "^DOMAIN=" .env.backup | cut -d'=' -f2)
    OLD_HOSTNAMES=$(grep "^HOSTNAMES=" .env.backup | cut -d'=' -f2)

    if [ ! -z "$OLD_DOMAIN" ] && [ "$OLD_DOMAIN" != "privra.com" ]; then
        echo "🌐 Restoring your domain: $OLD_DOMAIN"
        sed -i "s|DOMAIN=.*|DOMAIN=${OLD_DOMAIN}|" .env
    fi

    if [ ! -z "$OLD_HOSTNAMES" ] && [ "$OLD_HOSTNAMES" != "mail.privra.com" ]; then
        echo "🌐 Restoring your hostnames: $OLD_HOSTNAMES"
        sed -i "s|HOSTNAMES=.*|HOSTNAMES=${OLD_HOSTNAMES}|" .env
    fi
fi

echo ""
echo "✅ .env updated successfully!"
echo ""
echo "📝 Changes applied:"
echo "   - Updated to ghcr.io/mailu registry"
echo "   - Updated to Mailu version 2024.06"
echo "   - Added DNSSEC validation fixes"
echo "   - Generated new SECRET_KEY"
echo "   - Preserved your domain settings"
echo ""
echo "🚀 Next steps:"
echo "   1. Review .env file: nano .env"
echo "   2. Stop containers: docker compose down"
echo "   3. Pull new images: docker compose pull"
echo "   4. Start services: docker compose up -d"
echo ""
