#!/bin/bash

echo "🔌 Testing SSL/TLS Connections to Mail Server"
echo "=============================================="
echo ""

echo "Testing IMAP SSL (port 993)..."
echo "---"
timeout 5 openssl s_client -connect mail.privra.xyz:993 -servername mail.privra.xyz 2>&1 | grep -E "(Verification|subject|issuer|^CONNECTED)"
echo ""

echo "Testing SMTP STARTTLS (port 587)..."
echo "---"
timeout 5 openssl s_client -connect mail.privra.xyz:587 -starttls smtp -servername mail.privra.xyz 2>&1 | grep -E "(Verification|subject|issuer|^CONNECTED|250)"
echo ""

echo "Testing SMTPS SSL (port 465)..."
echo "---"
timeout 5 openssl s_client -connect mail.privra.xyz:465 -servername mail.privra.xyz 2>&1 | grep -E "(Verification|subject|issuer|^CONNECTED)"
echo ""

echo "✅ If you see 'Verification: OK' above, SSL is working!"
echo ""
echo "📱 Try connecting from your iPhone now:"
echo "  - Server: mail.privra.xyz"
echo "  - Email: sammie@privra.xyz"
echo "  - Password: @Homa"
echo "  - IMAP Port: 993 (SSL)"
echo "  - SMTP Port: 587 (STARTTLS)"
