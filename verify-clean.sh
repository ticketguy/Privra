#!/bin/bash

echo "🔍 Verifying Server Cleanup"
echo "============================"
echo ""

# Check Docker containers
echo "📦 Docker Containers:"
CONTAINERS=$(docker ps -a 2>/dev/null | wc -l)
if [ "$CONTAINERS" -le 1 ]; then
    echo "   ✅ No containers running ($((CONTAINERS - 1)) found)"
else
    echo "   ⚠️  Found $((CONTAINERS - 1)) containers:"
    docker ps -a
fi
echo ""

# Check Docker volumes
echo "💾 Docker Volumes:"
VOLUMES=$(docker volume ls 2>/dev/null | wc -l)
if [ "$VOLUMES" -le 1 ]; then
    echo "   ✅ No volumes ($((VOLUMES - 1)) found)"
else
    echo "   ⚠️  Found $((VOLUMES - 1)) volumes:"
    docker volume ls
fi
echo ""

# Check Docker images
echo "🖼️  Docker Images:"
IMAGES=$(docker images 2>/dev/null | wc -l)
if [ "$IMAGES" -le 1 ]; then
    echo "   ✅ No images cached ($((IMAGES - 1)) found)"
else
    echo "   ℹ️  Found $((IMAGES - 1)) images (this is OK)"
fi
echo ""

# Check for old directories
echo "📁 Old Directories:"
OLD_DIRS=("/opt/Privra" "/opt/mailserver" "/root/Privra" "/home/*/Privra")
FOUND_OLD=0
for dir in "${OLD_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "   ⚠️  Found: $dir"
        FOUND_OLD=1
    fi
done
if [ $FOUND_OLD -eq 0 ]; then
    echo "   ✅ No old directories found"
fi
echo ""

# Check disk space
echo "💽 Disk Space:"
df -h / | tail -1 | awk '{print "   Available: "$4" ("$5" used)"}'
echo ""

# Check ports
echo "🔌 Port Check (should be free):"
PORTS=(80 443 25 587 993)
for port in "${PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "   ⚠️  Port $port is in use"
    else
        echo "   ✅ Port $port is free"
    fi
done
echo ""

echo "============================"
echo "✅ Cleanup verification complete!"
