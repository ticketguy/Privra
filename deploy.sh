#!/bin/bash
# Privra Mail Server - Automated Deployment Script
# Run with: sudo bash deploy.sh

set -e  # Exit on error

echo "================================================"
echo "  Privra Mail Server - Deployment Script"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (use sudo)${NC}"
    exit 1
fi

# Get domain name
echo -e "${YELLOW}Enter your domain name (e.g., example.com):${NC}"
read -r DOMAIN
echo ""

echo -e "${YELLOW}Enter your mail subdomain (e.g., mail):${NC}"
read -r MAIL_SUBDOMAIN
MAIL_DOMAIN="${MAIL_SUBDOMAIN}.${DOMAIN}"
echo ""

echo -e "${YELLOW}Enter PostgreSQL password for privra_user:${NC}"
read -s DB_PASSWORD
echo ""

echo -e "${YELLOW}Enter Flask secret key (leave empty to generate):${NC}"
read -r SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
fi
echo ""

# Update system
echo -e "${GREEN}[1/12] Updating system...${NC}"
apt update && apt upgrade -y

# Install dependencies
echo -e "${GREEN}[2/12] Installing dependencies...${NC}"
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib \
    postfix dovecot-core dovecot-imapd dovecot-lmtpd \
    nginx certbot python3-certbot-nginx \
    git curl build-essential libpq-dev opendkim opendkim-tools \
    ufw htop

# Set up Python environment
echo -e "${GREEN}[3/12] Setting up Python environment...${NC}"
python3 -m venv /opt/privra/venv
source /opt/privra/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/privra/requirements.txt

# Configure PostgreSQL
echo -e "${GREEN}[4/12] Configuring PostgreSQL...${NC}"
sudo -u postgres psql -c "CREATE DATABASE privra;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER privra_user WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE privra TO privra_user;"
sudo -u postgres psql -c "ALTER DATABASE privra OWNER TO privra_user;"

# Initialize database
echo -e "${GREEN}[5/12] Initializing database...${NC}"
cd /opt/privra/admin
source /opt/privra/venv/bin/activate
python init_db.py

# Create .env file
echo -e "${GREEN}[6/12] Creating environment configuration...${NC}"
cat > /opt/privra/.env << EOF
# Database
DB_HOST=localhost
DB_NAME=privra
DB_USER=privra_user
DB_PASSWORD=$DB_PASSWORD

# Flask
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production

# Mail Server
MAIL_DOMAIN=$DOMAIN
MAIL_SERVER=$MAIL_DOMAIN

# DKIM
DKIM_SELECTOR=default
DKIM_PRIVATE_KEY_PATH=/etc/postfix/dkim/private.key

# Blockchain RPC
SOLANA_RPC=https://api.mainnet-beta.solana.com
ETHEREUM_RPC=https://eth.llamarpc.com
BASE_RPC=https://mainnet.base.org
POLYGON_RPC=https://polygon-rpc.com
ARBITRUM_RPC=https://arb1.arbitrum.io/rpc
OPTIMISM_RPC=https://mainnet.optimism.io
EOF

# Set up DKIM
echo -e "${GREEN}[7/12] Setting up DKIM...${NC}"
mkdir -p /etc/postfix/dkim
cd /etc/postfix/dkim
opendkim-genkey -t -s default -d $DOMAIN
chown -R opendkim:opendkim /etc/postfix/dkim
chmod 600 /etc/postfix/dkim/default.private

# Display DKIM public key
echo -e "${YELLOW}Add this DKIM DNS TXT record:${NC}"
echo "default._domainkey.$DOMAIN TXT \"$(cat /etc/postfix/dkim/default.txt | grep -oP 'p=\K[^"]+' | tr -d '\n')\""
echo ""

# Configure Postfix (basic setup - user should review)
echo -e "${GREEN}[8/12] Configuring Postfix...${NC}"
cat >> /etc/postfix/main.cf << EOF

# Privra Configuration
myhostname = $MAIL_DOMAIN
mydomain = $DOMAIN
myorigin = \$mydomain
mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain
inet_interfaces = all
inet_protocols = ipv4

# SASL
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
EOF

# Create Nginx configuration
echo -e "${GREEN}[9/12] Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/privra << EOF
server {
    listen 80;
    server_name $MAIL_DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $MAIL_DOMAIN;

    # SSL will be configured by certbot

    location /static {
        alias /opt/privra/webmail/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/privra /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Create systemd service
echo -e "${GREEN}[10/12] Creating systemd service...${NC}"
cat > /etc/systemd/system/privra-webmail.service << EOF
[Unit]
Description=Privra Webmail Application
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/privra/webmail
Environment="PATH=/opt/privra/venv/bin"
ExecStart=/opt/privra/venv/bin/python /opt/privra/webmail/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable privra-webmail
systemctl start privra-webmail

# Configure firewall
echo -e "${GREEN}[11/12] Configuring firewall...${NC}"
ufw allow 'Nginx Full'
ufw allow 22/tcp   # SSH
ufw allow 25/tcp   # SMTP
ufw allow 587/tcp  # Submission
ufw allow 993/tcp  # IMAPS
ufw allow 143/tcp  # IMAP
echo "y" | ufw enable

# Get SSL certificate
echo -e "${GREEN}[12/12] Getting SSL certificate...${NC}"
echo -e "${YELLOW}Running certbot (follow the prompts)...${NC}"
certbot --nginx -d $MAIL_DOMAIN

# Final status
echo ""
echo "================================================"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Add these DNS records:"
echo "   - A record: $MAIL_DOMAIN → YOUR_SERVER_IP"
echo "   - MX record: $DOMAIN → $MAIL_DOMAIN (priority 10)"
echo "   - TXT SPF: v=spf1 mx ~all"
echo "   - TXT DKIM: (shown above)"
echo "   - TXT DMARC: v=DMARC1; p=quarantine; rua=mailto:admin@$DOMAIN"
echo ""
echo "2. Access webmail at: https://$MAIL_DOMAIN"
echo "3. Register your first user"
echo "4. Test sending/receiving emails"
echo ""
echo "Service status:"
systemctl status privra-webmail --no-pager
echo ""
echo "View logs: sudo journalctl -u privra-webmail -f"
echo ""
