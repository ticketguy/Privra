#!/bin/bash

###################################
# Nginx fix using custom override
###################################

set -e

echo "🔧 Fixing nginx with custom override..."
echo "========================================"
echo ""

# Stop the front container
echo "🛑 Stopping front container..."
docker compose stop front

# Create nginx override directory (may need sudo for permissions)
echo "📁 Creating override directory..."
sudo mkdir -p overrides/nginx

# Create a script that will fix the nginx.conf after it's generated
echo "📝 Creating custom start script..."
sudo tee overrides/nginx/start > /dev/null <<'EOF'
#!/bin/bash
# Run the original start script to generate nginx.conf
python3 /start.py

# Fix the malformed location directive at line 182-183
sed -i '182,188d' /etc/nginx/nginx.conf

# Start nginx
exec nginx -g "daemon off;"
EOF

sudo chmod +x overrides/nginx/start

echo "✅ Custom override created"
echo ""

# Start front container
echo "🚀 Starting front container with override..."
docker compose up -d front

echo ""
echo "⏳ Waiting 10 seconds..."
sleep 10

echo ""
echo "📊 Front container status:"
docker compose ps front

echo ""
if docker compose ps front | grep -q "Up"; then
    echo "✅ SUCCESS! Front container is running!"
    echo ""
    echo "🌐 Access your mail server:"
    echo "   https://mail.privra.xyz/admin"
    echo ""
    echo "📧 Default login:"
    echo "   Create your first admin user at the admin interface"
else
    echo "❌ Still failing. Let me check the logs..."
    docker compose logs --tail=20 front
fi
