#!/bin/bash

###################################
# Comprehensive nginx fix
###################################

set -e

echo "🔧 Comprehensive Privra Mail Server Fix"
echo "========================================"
echo ""

# Step 1: Restore docker-compose.yml if it was corrupted
echo "📝 Step 1: Ensuring docker-compose.yml is correct..."
if docker compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "⚠️  docker-compose.yml has errors, pulling fresh copy..."
    git checkout docker-compose.yml
fi

# Step 2: Create the override directory and script
echo ""
echo "📝 Step 2: Creating nginx override..."
sudo mkdir -p overrides/nginx

sudo tee overrides/nginx/start > /dev/null <<'EOF'
#!/bin/bash
# Custom start script that fixes the nginx config bug
# Run the original start script to generate nginx.conf
python3 /start.py

# Fix the malformed location directive at line 182-183
# This removes the broken empty location block
sed -i '182,188d' /etc/nginx/nginx.conf

# Start nginx
exec nginx -g "daemon off;"
EOF

sudo chmod +x overrides/nginx/start

echo "✅ Override created at: overrides/nginx/start"

# Step 3: Verify docker-compose.yml has the entrypoint override
echo ""
echo "📝 Step 3: Checking docker-compose.yml for entrypoint override..."
if grep -q 'entrypoint: \["/overrides/start"\]' docker-compose.yml; then
    echo "✅ Entrypoint override is configured"
else
    echo "⚠️  Adding entrypoint override to docker-compose.yml..."
    # Backup first
    cp docker-compose.yml docker-compose.yml.backup
    # Add entrypoint after env_file line in front service
    sed -i '/front:/,/depends_on:/ {
        /env_file: .env/ a\    entrypoint: ["/overrides/start"]
    }' docker-compose.yml
    echo "✅ Entrypoint override added"
fi

# Step 4: Stop all containers
echo ""
echo "🛑 Step 4: Stopping all containers..."
docker compose down

# Step 5: Start containers
echo ""
echo "🚀 Step 5: Starting containers with fix..."
docker compose up -d

# Step 6: Wait and check status
echo ""
echo "⏳ Waiting 20 seconds for containers to start..."
sleep 20

echo ""
echo "📊 Container Status:"
docker compose ps

echo ""
echo "🔍 Front Container Logs (last 10 lines):"
docker compose logs --tail=10 front

echo ""
if docker compose ps front | grep -q "Up"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 Access your mail server at:"
    echo "   https://mail.privra.xyz/admin"
    echo ""
    echo "📧 Next Steps:"
    echo "   1. Create your first admin user"
    echo "   2. Add domain: privra.xyz"
    echo "   3. Create mailboxes"
else
    echo "❌ Front container still having issues"
    echo ""
    echo "📋 Full front container logs:"
    docker compose logs front
    echo ""
    echo "🔍 Debugging info:"
    echo "Override file exists:"
    ls -lh overrides/nginx/start
    echo ""
    echo "Checking if override is executable inside container:"
    docker compose run --rm --entrypoint /bin/bash front -c "ls -lh /overrides/start && cat /overrides/start"
fi
