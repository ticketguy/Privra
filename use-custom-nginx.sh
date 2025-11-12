#!/bin/bash

echo "🔧 Replacing front container with custom nginx..."
echo "================================================="
echo ""

# Stop containers
echo "🛑 Stopping containers..."
docker compose down

# Backup current docker-compose.yml
echo "💾 Backing up docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup-custom

# Create custom nginx override with our full config
echo "📝 Creating custom nginx configuration..."
sudo mkdir -p overrides/nginx

# Copy our custom nginx.conf
sudo cp custom-nginx.conf overrides/nginx/nginx.conf

# Create a start script that uses our custom config
sudo tee overrides/nginx/start > /dev/null <<'EOF'
#!/bin/bash
# Use completely custom nginx configuration

# Copy our custom config to the nginx location
cp /overrides/nginx.conf /etc/nginx/nginx.conf

# Start nginx
exec nginx -g "daemon off;"
EOF

sudo chmod +x overrides/nginx/start

# Update docker-compose.yml to use our custom entrypoint
echo "📝 Updating docker-compose.yml..."
cat > docker-compose-front-custom.yml <<'COMPOSE'
services:
  # Front - Custom Nginx (bypassing broken Mailu template)
  front:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
      - "25:25"
      - "465:465"
      - "587:587"
      - "110:110"
      - "995:995"
      - "143:143"
      - "993:993"
    volumes:
      - "./certs:/certs:ro"
      - "./custom-nginx.conf:/etc/nginx/nginx.conf:ro"
    networks:
      - mailnet
    depends_on:
      - admin
      - imap
      - smtp

networks:
  mailnet:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 192.168.203.0/24
COMPOSE

echo ""
echo "Would you like to use:"
echo "  1) Custom nginx configuration (clean, simple)"
echo "  2) Keep trying with Mailu nginx + override"
echo ""
echo "Recommendation: Option 1 - it's cleaner and avoids the Mailu bug entirely"
