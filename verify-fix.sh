#!/bin/bash

###################################
# Verify mail server status
###################################

echo "🔍 Privra Mail Server Status Check"
echo "==================================="
echo ""

echo "📊 Container Status:"
docker compose ps
echo ""

echo "🏥 Health Status:"
docker compose ps | grep -E "(Up|healthy|unhealthy)" | awk '{print $1, $NF}'
echo ""

echo "🔍 Front Container Details:"
if docker compose ps front | grep -q "Up"; then
    echo "✅ Front container is running!"
    echo ""
    echo "📋 Last 10 log lines:"
    docker compose logs --tail=10 front
else
    echo "❌ Front container is not running"
    echo ""
    echo "📋 Last 20 log lines:"
    docker compose logs --tail=20 front
fi

echo ""
echo "🌐 Access Points:"
echo "   Admin Interface: https://mail.privra.xyz/admin"
echo "   Domain: privra.xyz"
echo "   Mail Host: mail.privra.xyz"
echo ""

echo "🔧 Override Status:"
if [ -f "overrides/nginx/start" ]; then
    echo "✅ Nginx override exists"
    ls -lh overrides/nginx/start
else
    echo "⚠️  Nginx override not found"
fi

echo ""
echo "📝 Environment Check:"
grep -E "^(DOMAIN|HOSTNAMES|WEBMAIL|WEBDAV)" .env | head -5
