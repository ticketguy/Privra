# Privra Mail Server - Deployment Guide

## 🚀 What We Built

### Features Implemented
1. **Verification Badge System** - NFT, domain, and reputation verification in inbox
2. **RPC Configuration UI** - User and admin blockchain RPC management
3. **AI-Powered Email Labeling** - Automatic categorization (Socials, Updates, Spam, etc.)
4. **Mobile Optimization** - Responsive design with hamburger menu
5. **Liquid Glassmorphism UI** - Modern animated gradient background with glass effects

### Tech Stack
- **Backend**: Python Flask + Postfix + Dovecot
- **Database**: PostgreSQL
- **Frontend**: Jinja2 templates + Vanilla JavaScript
- **Styling**: CSS3 with glassmorphism and animations
- **Blockchain**: Solana + EVM chains (Ethereum, Base, Polygon, Arbitrum, Optimism)

---

## 📋 Prerequisites

### System Requirements
- Ubuntu 20.04+ or Debian 11+
- 2GB+ RAM
- 20GB+ disk space
- Root or sudo access
- Domain name with DNS access

### Required Software
- Python 3.8+
- PostgreSQL 12+
- Postfix (MTA)
- Dovecot (IMAP)
- Nginx (web server)
- Certbot (SSL certificates)

---

## 🔧 Installation Steps

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Dependencies
```bash
# Install Python and PostgreSQL
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib

# Install mail servers
sudo apt install -y postfix dovecot-core dovecot-imapd dovecot-lmtpd

# Install web server
sudo apt install -y nginx certbot python3-certbot-nginx

# Install additional tools
sudo apt install -y git curl build-essential libpq-dev
```

### 3. Clone Repository
```bash
cd /opt
sudo git clone <your-repo-url> privra
cd privra
sudo chown -R $USER:$USER /opt/privra
```

### 4. Set Up Python Environment
```bash
cd /opt/privra
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure PostgreSQL
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE privra;
CREATE USER privra_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE privra TO privra_user;
\q
```

### 6. Initialize Database
```bash
cd /opt/privra/admin
source ../venv/bin/activate
python init_db.py
```

### 7. Configure Environment Variables
```bash
cd /opt/privra
cp .env.example .env
nano .env
```

**Edit `.env` with your settings:**
```env
# Database
DB_HOST=localhost
DB_NAME=privra
DB_USER=privra_user
DB_PASSWORD=CHANGE_THIS_PASSWORD

# Flask
SECRET_KEY=GENERATE_RANDOM_SECRET_KEY_HERE
FLASK_ENV=production

# Mail Server
MAIL_DOMAIN=yourdomain.com
MAIL_SERVER=mail.yourdomain.com

# DKIM
DKIM_SELECTOR=default
DKIM_PRIVATE_KEY_PATH=/etc/postfix/dkim/private.key

# Blockchain RPC (defaults)
SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY
ETHEREUM_RPC=https://eth.llamarpc.com
```

### 8. Configure Postfix
```bash
sudo nano /etc/postfix/main.cf
```

**Add/modify these settings:**
```
# Basic settings
myhostname = mail.yourdomain.com
mydomain = yourdomain.com
myorigin = $mydomain
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain

# Network settings
inet_interfaces = all
inet_protocols = ipv4

# TLS settings
smtpd_tls_cert_file=/etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem
smtpd_tls_key_file=/etc/letsencrypt/live/mail.yourdomain.com/privkey.pem
smtpd_use_tls=yes
smtpd_tls_security_level=may
smtp_tls_security_level=may

# SASL authentication
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

# Virtual mailbox settings
virtual_mailbox_domains = pgsql:/etc/postfix/pgsql-virtual-mailbox-domains.cf
virtual_mailbox_maps = pgsql:/etc/postfix/pgsql-virtual-mailbox-maps.cf
virtual_alias_maps = pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf
virtual_transport = lmtp:unix:private/dovecot-lmtp

# DKIM
milter_default_action = accept
milter_protocol = 6
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
```

### 9. Configure Dovecot
```bash
sudo nano /etc/dovecot/conf.d/10-auth.conf
```

**Modify:**
```
disable_plaintext_auth = yes
auth_mechanisms = plain login
```

```bash
sudo nano /etc/dovecot/conf.d/10-mail.conf
```

**Set:**
```
mail_location = maildir:/var/mail/vmail/%d/%n
```

### 10. Set Up DKIM
```bash
# Generate DKIM keys
sudo mkdir -p /etc/postfix/dkim
cd /etc/postfix/dkim
sudo opendkim-genkey -t -s default -d yourdomain.com
sudo chown -R opendkim:opendkim /etc/postfix/dkim
```

**Add DNS TXT record:**
```
default._domainkey.yourdomain.com TXT "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY"
```

### 11. Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/privra
```

**Add configuration:**
```nginx
server {
    listen 80;
    server_name mail.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mail.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Static files
    location /static {
        alias /opt/privra/webmail/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Flask application
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/privra /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 12. Get SSL Certificate
```bash
sudo certbot --nginx -d mail.yourdomain.com
```

### 13. Create Systemd Service
```bash
sudo nano /etc/systemd/system/privra-webmail.service
```

**Add:**
```ini
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
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable privra-webmail
sudo systemctl start privra-webmail
sudo systemctl status privra-webmail
```

### 14. Configure Firewall
```bash
# Allow web traffic
sudo ufw allow 'Nginx Full'

# Allow mail ports
sudo ufw allow 25/tcp    # SMTP
sudo ufw allow 587/tcp   # Submission
sudo ufw allow 993/tcp   # IMAPS
sudo ufw allow 143/tcp   # IMAP

# Enable firewall
sudo ufw enable
```

---

## 🔐 DNS Configuration

Add these DNS records:

### MX Record
```
@ MX 10 mail.yourdomain.com.
```

### A Record
```
mail.yourdomain.com A YOUR_SERVER_IP
```

### SPF Record
```
@ TXT "v=spf1 mx ~all"
```

### DMARC Record
```
_dmarc.yourdomain.com TXT "v=DMARC1; p=quarantine; rua=mailto:admin@yourdomain.com"
```

### DKIM Record
```
default._domainkey.yourdomain.com TXT "v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY"
```

---

## ✅ Testing

### 1. Test Webmail Access
```bash
curl https://mail.yourdomain.com
```

### 2. Create First User
Visit: `https://mail.yourdomain.com/register`

### 3. Test Email Sending
```bash
# From server
echo "Test email" | mail -s "Test Subject" user@yourdomain.com
```

### 4. Check Logs
```bash
# Webmail logs
sudo journalctl -u privra-webmail -f

# Postfix logs
sudo tail -f /var/log/mail.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 5. Test Features
- ✅ Register new account
- ✅ Send encrypted email to another Privra user
- ✅ Click "Auto-Label" button in inbox
- ✅ Configure custom RPC endpoints
- ✅ Test mobile responsive menu
- ✅ Verify glassmorphism UI appears correctly

---

## 🔄 Maintenance

### Update Application
```bash
cd /opt/privra
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart privra-webmail
```

### Database Backup
```bash
# Backup
sudo -u postgres pg_dump privra > privra_backup_$(date +%Y%m%d).sql

# Restore
sudo -u postgres psql privra < privra_backup_20240101.sql
```

### Monitor Services
```bash
# Check all services
sudo systemctl status privra-webmail postfix dovecot nginx postgresql

# Resource usage
htop
df -h
```

---

## 🐛 Troubleshooting

### Webmail not loading
```bash
sudo systemctl status privra-webmail
sudo journalctl -u privra-webmail -n 50
```

### Emails not sending
```bash
sudo tail -n 100 /var/log/mail.log
sudo postfix check
sudo systemctl restart postfix
```

### Database connection issues
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT 1;"
```

### SSL certificate issues
```bash
sudo certbot renew --dry-run
sudo certbot certificates
```

---

## 📞 Support

If you encounter issues:
1. Check logs: `sudo journalctl -u privra-webmail -f`
2. Verify DNS records: `dig mail.yourdomain.com`
3. Test mail delivery: `telnet mail.yourdomain.com 25`
4. Check port accessibility: `nmap -p 25,587,993,443 mail.yourdomain.com`

---

## 🎉 Features Overview

### User Features
- 📧 Send/receive encrypted emails
- 🤖 AI-powered auto-labeling
- 🎨 Beautiful glassmorphism UI
- 📱 Mobile-responsive design
- 🔐 NFT & domain verification badges
- ⚙️ Custom blockchain RPC configuration
- 🌓 7-level dark/light mode system
- 💼 Multi-chain wallet generation
- 🛡️ Privacy controls with consent system

### Admin Features
- 🔧 Global RPC endpoint management
- 👥 User management dashboard
- 📊 Email statistics
- 🔑 DKIM configuration

Enjoy your new Privra Mail Server! 🚀
