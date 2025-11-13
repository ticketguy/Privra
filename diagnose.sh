#!/bin/bash
# Comprehensive Dovecot diagnostic

echo "======================================"
echo "DOVECOT DIAGNOSTICS"
echo "======================================"

echo -e "\n[1] SSL Certificates Check"
echo "-----------------------------------"
if [ -d "./certs" ]; then
    echo "✅ certs directory exists"
    ls -lah ./certs/
    echo ""
    echo "Certificate details:"
    if [ -f "./certs/fullchain.pem" ]; then
        openssl x509 -in ./certs/fullchain.pem -noout -subject -dates
    else
        echo "❌ fullchain.pem not found"
    fi
    if [ ! -f "./certs/privkey.pem" ]; then
        echo "❌ privkey.pem not found"
    fi
else
    echo "❌ certs directory does not exist"
    echo "Run: sudo mkdir -p certs && sudo certbot certonly --standalone -d mail.privra.xyz"
fi

echo -e "\n[2] SSL Certificates in Container"
echo "-----------------------------------"
docker compose exec dovecot ls -lah /etc/ssl/mail/ 2>/dev/null || echo "❌ Cannot access container SSL directory"

echo -e "\n[3] Dovecot Process Status"
echo "-----------------------------------"
docker compose exec dovecot ps aux | grep -E "dovecot|PID"

echo -e "\n[4] All Listening Ports in Container"
echo "-----------------------------------"
docker compose exec dovecot netstat -tlnp

echo -e "\n[5] Dovecot Active Configuration"
echo "-----------------------------------"
docker compose exec dovecot doveconf -n 2>&1 | head -50

echo -e "\n[6] Check conf.d Directory"
echo "-----------------------------------"
docker compose exec dovecot ls -la /etc/dovecot/conf.d/

echo -e "\n[7] Test Dovecot Config Syntax"
echo "-----------------------------------"
docker compose exec dovecot doveconf > /dev/null 2>&1 && echo "✅ Configuration syntax OK" || echo "❌ Configuration has errors"

echo -e "\n[8] Dovecot Logs (Last 30 lines)"
echo "-----------------------------------"
docker compose logs dovecot --tail=30

echo -e "\n[9] Check if IMAP Login Service is Defined"
echo "-----------------------------------"
docker compose exec dovecot doveconf service imap-login 2>&1 | head -20

echo -e "\n[10] Manual Dovecot Test"
echo "-----------------------------------"
echo "Testing Dovecot startup manually..."
docker compose exec dovecot dovecot -F & sleep 5 && pkill -f "dovecot -F"

echo -e "\n======================================"
echo "DIAGNOSTIC COMPLETE"
echo "======================================"
