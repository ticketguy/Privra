#!/bin/bash

###################################
# Alternative nginx fix using .env
###################################

set -e

echo "🔧 Alternative fix: Modifying .env configuration..."
echo "===================================================="
echo ""

# Backup current .env
cp .env .env.backup-$(date +%s)

# Make sure WEBMAIL and WEBDAV are not just commented, but completely removed
# This prevents the template from generating ANY webmail/webdav blocks
echo "📝 Removing WEBMAIL and WEBDAV from .env..."
sed -i '/^WEBMAIL=/d' .env
sed -i '/^# WEBMAIL=/d' .env
sed -i '/^WEBDAV=/d' .env
sed -i '/^# WEBDAV=/d' .env

# Also comment out the webmail service in docker-compose.yml
echo "📝 Disabling webmail service in docker-compose.yml..."
sed -i '/^  webmail:/,/^  [a-z]/ s/^/# /' docker-compose.yml || true

echo "✅ Configuration updated"
echo ""

# Restart containers
echo "🔄 Restarting all containers..."
docker compose down
docker compose up -d

echo ""
echo "⏳ Waiting 15 seconds for containers to start..."
sleep 15

echo ""
echo "📊 Container status:"
docker compose ps

echo ""
echo "🔍 Checking front container:"
if docker compose ps front | grep -q "Up"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 Access admin at: https://mail.privra.xyz/admin"
else
    echo "❌ Still having issues. Check logs:"
    docker compose logs --tail=20 front
fi
