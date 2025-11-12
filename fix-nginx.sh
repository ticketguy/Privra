#!/bin/bash

###################################
# Fix nginx configuration issue
###################################

set -e

echo "🔧 Fixing nginx configuration..."
echo "================================="
echo ""

# Temporarily disable webmail routing to isolate the issue
echo "📝 Updating .env to disable webmail routing..."
sed -i 's|WEBMAIL=roundcube|WEBMAIL=none|g' .env
sed -i 's|WEBROOT_REDIRECT=/webmail|WEBROOT_REDIRECT=/admin|g' .env

echo "✅ Configuration updated"
echo ""

# Restart only the front container
echo "🔄 Restarting front container..."
docker compose up -d front

echo ""
echo "⏳ Waiting for front container to start..."
sleep 10

echo ""
echo "📊 Front container status:"
docker compose ps front

echo ""
echo "📋 Front container logs (last 20 lines):"
docker compose logs --tail=20 front

echo ""
if docker compose ps front | grep -q "Up"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 You can now access the admin interface at:"
    echo "   https://mail.privra.xyz/admin"
    echo ""
    echo "Note: Webmail is temporarily disabled. We can re-enable it once"
    echo "the front container is stable."
else
    echo "❌ Front container still failing. Checking for errors..."
    docker compose logs front | tail -50
fi
