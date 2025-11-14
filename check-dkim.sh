#!/bin/bash
# Script to diagnose DKIM signing issues

echo "=================================="
echo "DKIM Diagnostic Script"
echo "=================================="
echo ""

cd ~/privra-mail

echo "[1] Checking if OpenDKIM is running in Postfix container..."
docker compose exec postfix ps aux | grep opendkim | grep -v grep

echo ""
echo "[2] Checking OpenDKIM logs for recent activity..."
docker compose logs postfix --tail 50 | grep -i dkim

echo ""
echo "[3] Checking if DKIM keys exist..."
docker compose exec postfix ls -la /etc/opendkim/keys/privra.xyz/

echo ""
echo "[4] Checking DKIM key permissions..."
docker compose exec postfix stat /etc/opendkim/keys/privra.xyz/mail.private

echo ""
echo "[5] Checking Postfix main.cf for DKIM milter configuration..."
docker compose exec postfix postconf | grep milter

echo ""
echo "[6] Testing DKIM socket connection..."
docker compose exec postfix nc -zv localhost 8891

echo ""
echo "[7] Checking recent mail logs for DKIM signing..."
docker compose exec postfix tail -100 /var/log/mail.log | grep -i "dkim"

echo ""
echo "[8] Verifying DNS DKIM record..."
host -t TXT mail._domainkey.privra.xyz

echo ""
echo "=================================="
echo "Diagnostic Complete"
echo "=================================="
