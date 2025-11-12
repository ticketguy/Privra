#!/bin/bash

echo "🧹 Cleaning up repository and fixing nginx..."
echo "=============================================="
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

# Step 4: Verify docker-compose.yml has entrypoint
echo ""
echo "✅ Verifying docker-compose.yml..."
if grep -q 'entrypoint: \["/overrides/start"\]' docker-compose.yml; then
    echo "✅ Entrypoint override found in docker-compose.yml"
else
    echo "❌ Entrypoint not found. Adding it now..."
    # Add it after the env_file line
    sed -i '/services:/,/front:/ {
        /front:/,/depends_on:/ {
            /env_file: \.env/ a\    entrypoint: ["/overrides/start"]
        }
    }' docker-compose.yml
fi

# Step 5: Create override directory and script
echo ""
echo "📝 Creating nginx override..."
sudo mkdir -p overrides/nginx

sudo tee overrides/nginx/start > /dev/null <<'OVERRIDE_SCRIPT'
#!/bin/bash
# Custom start script that fixes the nginx config bug

# Run the original start script to generate nginx.conf
python3 /start.py

# Fix the malformed location directive by deleting the broken lines
sed -i '182,188d' /etc/nginx/nginx.conf

# Start nginx
exec nginx -g "daemon off;"
OVERRIDE_SCRIPT

sudo chmod +x overrides/nginx/start

echo "✅ Override created"

# Step 6: Validate docker-compose.yml
echo ""
echo "🔍 Validating docker-compose.yml..."
if docker compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors!"
    docker compose config
    exit 1
fi

# Step 7: Start containers
echo ""
echo "🚀 Starting containers..."
docker compose up -d

# Step 8: Wait and check
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
if docker compose ps front | grep -q "Up"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 Access your mail server:"
    echo "   https://mail.privra.xyz/admin"
else
    echo "❌ Front container still failing"
    echo ""
    echo "Let's check if the override is being used..."
    docker compose run --rm --entrypoint /bin/sh front -c "ls -lh /overrides/ && cat /overrides/start 2>/dev/null || echo 'Override not found in container'"
fi
