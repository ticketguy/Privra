#!/bin/bash

echo "🔍 Verifying SSL Certificate Fix for IMAP/SMTP"
echo "=============================================="
echo ""

# Check container status
echo "📦 Container Status:"
docker compose ps imap smtp
echo ""

# Check if certificates are mounted in IMAP container
echo "🔐 Checking IMAP certificate mount:"
docker compose exec imap ls -lh /certs/
echo ""

# Check if certificates are mounted in SMTP container
echo "🔐 Checking SMTP certificate mount:"
docker compose exec smtp ls -lh /certs/
echo ""

# Check IMAP logs for SSL errors
echo "📋 Recent IMAP logs (checking for SSL errors):"
docker compose logs imap --tail=30 | tail -20
echo ""

# Check SMTP logs for SSL errors
echo "📋 Recent SMTP logs (checking for SSL errors):"
docker compose logs smtp --tail=30 | tail -20
echo ""

# Test SSL connection to IMAP
echo "🔌 Testing SSL connection to IMAP (port 993):"
timeout 5 openssl s_client -connect mail.privra.xyz:993 -servername mail.privra.xyz -brief 2>&1 | head -10
echo ""

# Test STARTTLS connection to SMTP
echo "🔌 Testing STARTTLS connection to SMTP (port 587):"
timeout 5 openssl s_client -connect mail.privra.xyz:587 -starttls smtp -brief 2>&1 | head -10
echo ""

echo "✅ Verification complete!"
echo ""
echo "📱 If you see 'Verification: OK' above, your iPhone should now connect!"
echo ""
echo "iPhone Mail Settings:"
echo "  Incoming Mail Server (IMAP):"
echo "    - Server: mail.privra.xyz"
echo "    - Port: 993"
echo "    - Use SSL: Yes"
echo "    - Username: sammie@privra.xyz"
echo "    - Password: @Homa"
echo ""
echo "  Outgoing Mail Server (SMTP):"
echo "    - Server: mail.privra.xyz"
echo "    - Port: 587"
echo "    - Use SSL/TLS: Yes (STARTTLS)"
echo "    - Username: sammie@privra.xyz"
echo "    - Password: @Homa"
