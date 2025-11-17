#!/bin/bash
# Plug-and-play script to fix webmail container issues
# This script automatically rebuilds the webmail container and verifies it's working

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Privra Mail - Webmail Container Fix"
echo "=========================================="
echo ""

cd "$PROJECT_DIR"

echo "Step 1/5: Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not available"
    echo "Try: docker --version and docker compose version"
    exit 1
fi
echo "✅ Docker is available"
echo ""

echo "Step 2/5: Stopping webmail container..."
docker compose stop webmail || true
echo "✅ Webmail container stopped"
echo ""

echo "Step 3/5: Removing old webmail container..."
docker compose rm -f webmail || true
echo "✅ Old container removed"
echo ""

echo "Step 4/5: Rebuilding webmail with latest code (this may take a minute)..."
docker compose build --no-cache webmail
echo "✅ Webmail container rebuilt"
echo ""

echo "Step 5/5: Starting webmail container..."
docker compose up -d webmail
echo "✅ Webmail container started"
echo ""

echo "Waiting 5 seconds for container to initialize..."
sleep 5
echo ""

echo "Checking webmail container status..."
if docker compose ps webmail | grep -q "Up"; then
    echo "✅ Webmail container is RUNNING"
    echo ""
    echo "Checking logs for errors..."
    if docker compose logs --tail=20 webmail | grep -i "error\|exception\|traceback" | grep -v "INFO\|DEBUG" > /dev/null 2>&1; then
        echo "⚠️  Some errors detected in logs. Full logs:"
        echo ""
        docker compose logs --tail=50 webmail
        echo ""
        echo "If you see 'ImportError' or 'ModuleNotFoundError', you may need to check dependencies."
    else
        echo "✅ No errors detected in recent logs"
        echo ""
        echo "=========================================="
        echo "✅ SUCCESS! Webmail is running properly"
        echo "=========================================="
        echo ""
        echo "You can now access webmail at your configured URL."
        echo ""
        echo "To view live logs: docker compose logs -f webmail"
    fi
else
    echo "❌ Webmail container failed to start"
    echo ""
    echo "Container status:"
    docker compose ps webmail
    echo ""
    echo "Recent logs:"
    docker compose logs --tail=50 webmail
    echo ""
    echo "Please review the error logs above."
    exit 1
fi

echo ""
echo "This script has completed. If issues persist, check:"
echo "  - docs/troubleshooting/ for more help"
echo "  - docker compose logs webmail for full logs"
