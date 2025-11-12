#!/bin/bash

###################################
# Debug nginx configuration
###################################

set -e

echo "🔍 Debugging nginx configuration..."
echo "===================================="
echo ""

# Run the front container but override the entrypoint to prevent it from crashing
echo "📦 Starting front container with bash to inspect config..."
docker compose run --rm --entrypoint /bin/bash front -c "
    echo '🔧 Generating nginx config...'
    python3 /start.py || true
    echo ''
    echo '📄 Showing lines 175-190 of nginx.conf:'
    cat -n /etc/nginx/nginx.conf | sed -n '175,190p'
    echo ''
    echo '🔍 Showing all location directives:'
    grep -n 'location' /etc/nginx/nginx.conf || true
"

echo ""
echo "✅ Debug complete!"
