#!/bin/bash
# Script to expand SSL certificate to include both mail.privra.xyz and admin.privra.xyz

set -e

echo "=================================="
echo "SSL Certificate Expansion Script"
echo "=================================="
echo ""
echo "This script will:"
echo "  1. Stop nginx container"
echo "  2. Use certbot to expand the certificate"
echo "  3. Copy new certificates to ~/privra-mail/certs/"
echo "  4. Restart nginx"
echo ""

# Change to the mail directory
cd ~/privra-mail

echo "[1/4] Stopping nginx container..."
docker compose stop nginx

echo "[2/4] Expanding SSL certificate with certbot..."
echo "This will add admin.privra.xyz to the existing mail.privra.xyz certificate"

sudo certbot certonly --standalone --expand \
  -d mail.privra.xyz \
  -d admin.privra.xyz \
  --non-interactive --agree-tos \
  -m admin@privra.xyz

echo "[3/4] Copying new certificates..."
sudo cp /etc/letsencrypt/live/mail.privra.xyz/fullchain.pem ~/privra-mail/certs/
sudo cp /etc/letsencrypt/live/mail.privra.xyz/privkey.pem ~/privra-mail/certs/
sudo chown $USER:$USER ~/privra-mail/certs/*.pem

echo "[4/4] Starting nginx..."
docker compose up -d nginx

echo ""
echo "=================================="
echo "Certificate Expansion Complete!"
echo "=================================="
echo ""
echo "Verifying the new certificate..."
sleep 3

# Test both domains
echo "Testing mail.privra.xyz..."
curl -I https://mail.privra.xyz/ 2>&1 | grep -E "HTTP|SSL" || true

echo ""
echo "Testing admin.privra.xyz..."
curl -I https://admin.privra.xyz/warofbest/ 2>&1 | grep -E "HTTP|SSL" || true

echo ""
echo "If both show 'HTTP/2 200' or similar, the certificate is working!"
echo "You can also check the certificate details in your browser."
echo ""
echo "To view certificate info:"
echo "  openssl s_client -connect admin.privra.xyz:443 -servername admin.privra.xyz < /dev/null 2>/dev/null | openssl x509 -text -noout | grep -A 2 'Subject Alternative Name'"
