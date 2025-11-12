#!/bin/bash

echo "🔐 Generating self-signed TLS certificates..."
echo "=============================================="
echo ""

# Check if certs directory exists and is owned by root
if [ -d "certs" ] && [ "$(stat -c '%U' certs)" = "root" ]; then
    echo "⚠️  Certs directory is owned by root, fixing permissions..."
    sudo chown -R $USER:$USER certs
fi

# Create certs directory if it doesn't exist
mkdir -p certs

# Check if certificates already exist
if [ -f "certs/cert.pem" ] && [ -f "certs/key.pem" ]; then
    echo "⚠️  Certificates already exist in certs/"
    echo ""
    echo "Do you want to regenerate them? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Keeping existing certificates."
        exit 0
    fi
fi

echo "📝 Generating self-signed certificate for mail.privra.xyz..."
echo ""

# Generate self-signed certificate valid for 365 days
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout certs/key.pem \
    -out certs/cert.pem \
    -days 365 \
    -subj "/C=US/ST=State/L=City/O=Privra/CN=mail.privra.xyz" \
    -addext "subjectAltName=DNS:mail.privra.xyz,DNS:privra.xyz"

# Make sure permissions are correct
chmod 644 certs/cert.pem
chmod 600 certs/key.pem

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Self-signed certificates generated successfully!"
    echo ""
    echo "📁 Certificate files:"
    ls -lh certs/cert.pem certs/key.pem
    echo ""
    echo "⚠️  IMPORTANT: These are self-signed certificates"
    echo "   Your browser will show a security warning"
    echo "   For production, use Let's Encrypt certificates"
    echo ""
    echo "🚀 Now restart the containers:"
    echo "   docker compose restart front"
else
    echo ""
    echo "❌ Failed to generate certificates"
    exit 1
fi
