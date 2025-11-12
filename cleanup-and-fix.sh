#!/bin/bash

echo "🧹 Cleaning up and deploying custom nginx..."
echo "============================================="
echo ""

# Step 1: Stop all containers
echo "🛑 Stopping all containers..."
docker compose down

# Step 2: Clean up repo
echo ""
echo "🧹 Cleaning up local changes..."
git reset --hard HEAD
git clean -fd

# Step 3: Pull latest
echo ""
echo "📥 Pulling latest changes..."
git pull

# Step 4: Validate docker-compose.yml
echo ""
echo "🔍 Validating docker-compose.yml..."
if docker compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors!"
    docker compose config
    exit 1
fi

# Step 5: Check custom nginx config exists
echo ""
echo "📝 Verifying custom nginx configuration..."
if [ -f "custom-nginx.conf" ]; then
    echo "✅ custom-nginx.conf found"
else
    echo "❌ custom-nginx.conf not found!"
    exit 1
fi

# Step 5.5: Generate certificates if they don't exist
echo ""
echo "🔐 Checking TLS certificates..."
if [ ! -f "certs/cert.pem" ] || [ ! -f "certs/key.pem" ]; then
    echo "⚠️  TLS certificates not found. Generating self-signed certificates..."
    ./generate-certs.sh
    if [ $? -ne 0 ]; then
        echo "❌ Failed to generate certificates"
        exit 1
    fi
else
    echo "✅ TLS certificates found"
fi

# Step 6: Start containers
echo ""
echo "🚀 Starting containers with custom nginx..."
docker compose up -d

# Step 7: Wait and check
echo ""
echo "⏳ Waiting 20 seconds for startup..."
sleep 20

echo ""
echo "📊 Final Status:"
docker compose ps

echo ""
echo "🔍 Front container logs:"
docker compose logs --tail=15 front

echo ""
if docker compose ps front | grep -q "Up" && ! docker compose logs front 2>&1 | grep -q "emerg"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 Access your mail server:"
    echo "   https://mail.privra.xyz/admin"
    echo ""
    echo "📝 Note: Using custom nginx:alpine (bypassed broken Mailu template)"
else
    echo "❌ Front container has issues. Check logs above."
    echo ""
    echo "Testing nginx config..."
    docker compose exec front nginx -t 2>&1 || echo "Nginx test failed"
fi
