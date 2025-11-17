#!/bin/bash
# Script to rebuild and restart the webmail Docker container

set -e

echo "Stopping webmail container..."
docker compose stop webmail

echo "Removing old webmail container..."
docker compose rm -f webmail

echo "Rebuilding webmail container with latest code..."
docker compose build --no-cache webmail

echo "Starting webmail container..."
docker compose up -d webmail

echo "Waiting for container to start..."
sleep 5

echo "Checking webmail container status..."
docker compose ps webmail

echo "Checking webmail logs..."
docker compose logs --tail=50 webmail

echo ""
echo "Webmail container has been rebuilt and restarted!"
echo "If you see any errors above, please review them."
