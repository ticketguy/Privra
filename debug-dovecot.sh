#!/bin/bash
# Dovecot diagnostic script

echo "=== Dovecot Process Status ==="
docker compose exec dovecot ps aux | grep dovecot

echo -e "\n=== Port Listeners ==="
docker compose exec dovecot netstat -tlnp

echo -e "\n=== Dovecot Configuration (doveconf -n) ==="
docker compose exec dovecot doveconf -n

echo -e "\n=== Check conf.d directory ==="
docker compose exec dovecot ls -la /etc/dovecot/conf.d/

echo -e "\n=== Check if default configs exist ==="
docker compose exec dovecot find /etc/dovecot -name "*.conf" -type f

echo -e "\n=== Test configuration syntax ==="
docker compose exec dovecot doveconf > /dev/null && echo "✅ Config syntax OK" || echo "❌ Config syntax error"

echo -e "\n=== Recent logs ==="
docker compose logs dovecot --tail=50
