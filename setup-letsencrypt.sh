#!/bin/bash

echo "🔐 Setting up Let's Encrypt certificates for Privra Mail..."
echo "============================================================"
echo ""

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    sudo apt update
    sudo apt install -y certbot
fi

# Stop nginx temporarily to allow certbot to bind to port 80
echo ""
echo "🛑 Temporarily stopping front container..."
docker compose stop front

# Get Let's Encrypt certificate
echo ""
echo "🔐 Requesting Let's Encrypt certificate..."
echo "⚠️  You'll need to enter your email address for renewal notifications"
echo ""

sudo certbot certonly --standalone \
    -d mail.privra.xyz \
    --non-interactive \
    --agree-tos \
    --email admin@privra.xyz \
    --preferred-challenges http

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Let's Encrypt certificate obtained successfully!"

    # Create Mailu's expected certificate structure
    echo ""
    echo "📋 Creating Mailu certificate structure..."
    mkdir -p certs/letsencrypt/live/mail.privra.xyz

    # Copy certificates to Mailu's expected location
    sudo cp /etc/letsencrypt/live/mail.privra.xyz/fullchain.pem certs/letsencrypt/live/mail.privra.xyz/
    sudo cp /etc/letsencrypt/live/mail.privra.xyz/privkey.pem certs/letsencrypt/live/mail.privra.xyz/
    sudo cp /etc/letsencrypt/live/mail.privra.xyz/chain.pem certs/letsencrypt/live/mail.privra.xyz/ 2>/dev/null || true
    sudo cp /etc/letsencrypt/live/mail.privra.xyz/cert.pem certs/letsencrypt/live/mail.privra.xyz/ 2>/dev/null || true

    # Fix permissions
    sudo chown -R $USER:$USER certs/letsencrypt
    chmod 644 certs/letsencrypt/live/mail.privra.xyz/*.pem
    chmod 600 certs/letsencrypt/live/mail.privra.xyz/privkey.pem

    echo "✅ Certificates installed in Mailu structure"

    # Start front container
    echo ""
    echo "🚀 Starting front container..."
    docker compose start front

    echo ""
    echo "✅ SUCCESS! Let's Encrypt certificates installed!"
    echo ""
    echo "📁 Certificate files:"
    ls -lh certs/letsencrypt/live/mail.privra.xyz/
    echo ""
    echo "🔄 Certificates will auto-renew every 90 days"
    echo ""
    echo "🌐 Your mail server now has a trusted certificate!"
    echo "📧 Test your mail server at: https://mail.privra.xyz/admin"
else
    echo ""
    echo "❌ Failed to obtain Let's Encrypt certificate"
    echo ""
    echo "Common issues:"
    echo "1. Make sure port 80 is accessible from the internet"
    echo "2. Verify DNS A record for mail.privra.xyz points to your server IP"
    echo "3. Check firewall settings"
    echo ""
    echo "🔄 Starting front container with old certificates..."
    docker compose start front
    exit 1
fi

# Set up auto-renewal
echo ""
echo "⏰ Setting up automatic certificate renewal..."
echo ""

# Create renewal hook script
sudo tee /etc/letsencrypt/renewal-hooks/deploy/copy-to-mailu.sh > /dev/null <<'RENEWAL_HOOK'
#!/bin/bash
# Copy renewed certificates to Mailu
cp /etc/letsencrypt/live/mail.privra.xyz/fullchain.pem /home/privra/privra-mail/certs/letsencrypt/live/mail.privra.xyz/
cp /etc/letsencrypt/live/mail.privra.xyz/privkey.pem /home/privra/privra-mail/certs/letsencrypt/live/mail.privra.xyz/
chown -R privra:privra /home/privra/privra-mail/certs/letsencrypt
cd /home/privra/privra-mail && docker compose restart front imap smtp
RENEWAL_HOOK

sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/copy-to-mailu.sh

echo "✅ Auto-renewal configured!"
echo ""
echo "🎉 All done! Your mail server now has a trusted SSL certificate."
echo "   Try connecting from your iPhone - it should work without any warnings!"
