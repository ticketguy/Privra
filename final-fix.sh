#!/bin/bash

###################################
# Final fix for nginx configuration
###################################

set -e

echo "🔧 Applying final nginx fix..."
echo "================================"
echo ""

# Comment out WEBMAIL instead of setting it to none
echo "📝 Commenting out WEBMAIL variable..."
sed -i 's/^WEBMAIL=.*$/# WEBMAIL=roundcube/' .env

# Also comment out WEBDAV
sed -i 's/^WEBDAV=.*$/# WEBDAV=none/' .env

echo "✅ Configuration updated"
echo ""

# Stop all containers
echo "🛑 Stopping all containers..."
docker compose down

echo ""
echo "🚀 Starting containers..."
docker compose up -d

echo ""
echo "⏳ Waiting 15 seconds for containers to start..."
sleep 15

echo ""
echo "📊 Container status:"
docker compose ps

echo ""
echo "🔍 Checking front container logs:"
docker compose logs --tail=10 front

echo ""
if docker compose ps | grep front | grep -q "Up"; then
    echo "✅ SUCCESS! All containers are running!"
    echo ""
    echo "🌐 Access your mail server at:"
    echo "   Admin: https://mail.privra.xyz/admin"
    echo ""
    echo "📧 Next steps:"
    echo "   1. Create your first admin user"
    echo "   2. Create a domain (privra.xyz)"
    echo "   3. Create mailboxes"
else
    echo "❌ Front container still having issues"
    echo "Let me check the generated nginx config again..."
    docker compose run --rm --entrypoint /bin/bash front -c "
        python3 /start.py 2>&1 | head -20
        echo ''
        echo 'Line 183 of nginx.conf:'
        cat -n /etc/nginx/nginx.conf | sed -n '180,186p'
    "
fi
