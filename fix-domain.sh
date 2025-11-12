#!/bin/bash

###################################
# Fix domain configuration
###################################

set -e

echo "🔧 Fixing domain configuration..."
echo "================================="
echo ""

# Update domain to privra.xyz
sed -i 's|DOMAIN=privra\.com|DOMAIN=privra.xyz|g' .env
sed -i 's|HOSTNAMES=mail\.privra\.com|HOSTNAMES=mail.privra.xyz|g' .env

echo "✅ Domain updated to privra.xyz"
echo ""

# Restart containers
echo "🔄 Restarting containers..."
docker compose down
docker compose up -d

echo ""
echo "⏳ Waiting for containers to start..."
sleep 15

echo ""
echo "📊 Container status:"
docker compose ps

echo ""
echo "✅ Done! Check if all containers are healthy."
echo ""
echo "If front container is still failing, check logs with:"
echo "  docker compose logs front"
