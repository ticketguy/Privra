# Privra Mail Server - Deployment Guide

## What Was Fixed

### 1. DKIM Signing Issue ✅
**Problem:** DKIM wasn't signing outgoing emails (mail-tester showed "not signed with DKIM")

**Root Cause:** The `opendkim.conf` file had a hardcoded domain (`privra.xyz`) instead of using the `$MAIL_DOMAIN` environment variable. This meant DKIM keys were generated for the correct domain, but OpenDKIM was configured to sign for a different hardcoded domain.

**Solution:**
- Made `opendkim.conf` dynamically generated in `postfix/entrypoint.sh`
- Now uses `$MAIL_DOMAIN` from environment variables
- DKIM configuration is automatically created with the correct domain on container startup

**Files Changed:**
- `postfix/entrypoint.sh` - Added dynamic OpenDKIM config generation
- `postfix/Dockerfile` - Removed static opendkim.conf copy
- Deleted `postfix/opendkim.conf` (now generated dynamically)

---

### 2. Admin Panel Security (Hardcoded Domains) ✅
**Problem:** Nginx configuration had hardcoded domains (`mail.privra.xyz`, `admin.privra.xyz`) making it non-portable and difficult to set up SSL for multiple domains.

**Root Cause:** The `nginx/nginx.conf` file had hardcoded server names that couldn't adapt to different deployments.

**Solution:**
- Created `nginx/nginx.conf.template` with environment variable placeholders
- Created custom nginx Dockerfile with `envsubst` support
- Created `nginx/entrypoint.sh` to generate config from template on startup
- Updated `docker-compose.yml` to build custom nginx image and pass environment variables

**Files Changed:**
- `nginx/nginx.conf.template` - New template file with `${WEBMAIL_HOSTNAME}` and `${ADMIN_HOSTNAME}` placeholders
- `nginx/Dockerfile` - New custom nginx image
- `nginx/entrypoint.sh` - New entrypoint to generate config from template
- `docker-compose.yml` - Updated nginx service to build custom image
- `.env.example` - Added `WEBMAIL_HOSTNAME` and `ADMIN_HOSTNAME` variables

---

### 3. Scattered Scripts Removed ✅
**Problem:** User had to run separate scripts like `check-dkim.sh`, `fix-ssl-cert.sh`, etc., which made the setup fragmented.

**Solution:**
- Removed all diagnostic scripts (`check-dkim.sh`, `fix-ssl-cert.sh`)
- Integrated DKIM diagnostics into container logs
- SSL certificate management now handled via standard certbot/letsencrypt
- Everything is now configured via `.env` file and docker-compose

**Files Removed:**
- `check-dkim.sh`
- `fix-ssl-cert.sh`
- `DKIM-FIX-README.md`
- `SSL-CERT-FIX-README.md`

---

## Fresh Deployment Instructions

### 1. Configure DNS Records

Before deploying, set up these DNS records:

```dns
# Mail server
A     mail.yourdomain.com        →  YOUR_SERVER_IP
A     admin.yourdomain.com       →  YOUR_SERVER_IP

# MX record for email
MX    yourdomain.com             →  mail.yourdomain.com (priority 10)

# SPF record
TXT   yourdomain.com             →  "v=spf1 mx ~all"

# DMARC record
TXT   _dmarc.yourdomain.com      →  "v=DMARC1; p=quarantine; rua=mailto:admin@yourdomain.com"
```

**DKIM record will be shown in logs after first startup - add it then!**

---

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/ticketguy/Privra.git
cd Privra

# Checkout the fixed branch
git checkout claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Edit `.env` with your values:

```bash
# Your domain configuration
MAIL_DOMAIN=yourdomain.com
MAIL_HOSTNAME=mail.yourdomain.com
WEBMAIL_HOSTNAME=mail.yourdomain.com
ADMIN_HOSTNAME=admin.yourdomain.com

# Database password (generate strong password!)
DB_PASSWORD=$(openssl rand -base64 32)

# Secret key (generate random key!)
SECRET_KEY=$(openssl rand -hex 32)

# Admin email for Let's Encrypt notifications
ADMIN_EMAIL=admin@yourdomain.com
```

---

### 3. Get SSL Certificates

Before starting the mail server, obtain Let's Encrypt certificates for BOTH domains:

```bash
# Install certbot if not already installed
sudo apt update && sudo apt install -y certbot

# Stop nginx if running
docker compose down nginx 2>/dev/null || true

# Get certificate for both mail and admin hostnames
sudo certbot certonly --standalone \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --non-interactive

# Copy certificates to project directory
sudo mkdir -p ./certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/
sudo chmod 644 ./certs/fullchain.pem
sudo chmod 600 ./certs/privkey.pem
```

---

### 4. Start the Mail Server

```bash
# Start all services
docker compose up -d

# Check logs for DKIM DNS record
docker compose logs postfix | grep "DKIM DNS Record"

# The output will show something like:
# ========================================
# DKIM DNS Record (add this to your DNS):
# ========================================
# mail._domainkey IN TXT "v=DKIM1; k=rsa; p=MIIBIjANBgkq..."
```

**Copy the DKIM record and add it to your DNS!**

---

### 5. Initialize Database

```bash
# Wait for database to be healthy
docker compose exec -T admin python init_db.py

# Create admin user
docker compose exec -T admin python manage.py adduser admin@yourdomain.com your-strong-password
```

---

### 6. Test DKIM Signing

After DNS propagates (can take up to 24 hours), test DKIM:

```bash
# Check if DKIM DNS record is visible
host -t TXT mail._domainkey.yourdomain.com

# Send test email to mail-tester.com
# 1. Go to https://www.mail-tester.com/
# 2. Get test email address (test-XXXXX@srv1.mail-tester.com)
# 3. Login to https://mail.yourdomain.com/
# 4. Send email to that address
# 5. Check score on mail-tester.com

# Expected results:
# ✅ SPF: Pass
# ✅ DKIM: Signed
# ✅ DMARC: Pass
# Score: 8-10/10
```

---

### 7. Access Your Mail Server

- **Webmail:** `https://mail.yourdomain.com/`
- **Admin Panel:** `https://admin.yourdomain.com/warofbest/`

**Security Note:** The admin panel is hidden at `/warofbest/` path. All other paths on admin.yourdomain.com return 404.

---

## Troubleshooting

### DKIM Still Not Signing

```bash
# Check if OpenDKIM is running
docker compose exec postfix ps aux | grep opendkim

# Check DKIM logs
docker compose logs postfix | grep -i dkim

# Verify DKIM keys exist
docker compose exec postfix ls -la /etc/opendkim/keys/

# Check milter configuration
docker compose exec postfix postconf | grep milter

# Should show:
# milter_default_action = accept
# milter_protocol = 6
# smtpd_milters = inet:localhost:8891
# non_smtpd_milters = inet:localhost:8891
```

### SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in ./certs/fullchain.pem -text -noout | grep -A 2 "Subject Alternative Name"

# Should list both domains:
# DNS:mail.yourdomain.com, DNS:admin.yourdomain.com

# If certificate doesn't include admin domain, expand it:
sudo certbot certonly --standalone \
  --cert-name mail.yourdomain.com \
  --expand \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Then copy new certs:
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/
docker compose restart nginx
```

### Admin Panel Not Accessible

```bash
# Check nginx logs
docker compose logs nginx | tail -50

# Verify nginx generated correct config
docker compose exec nginx cat /etc/nginx/nginx.conf | grep server_name

# Should show your actual domains:
# server_name mail.yourdomain.com admin.yourdomain.com;
```

### Port 25 Blocked (Can't Send External Email)

```bash
# Test if port 25 is accessible
telnet gmail-smtp-in.l.google.com 25

# If connection fails, contact your hosting provider:
# - DigitalOcean: Submit support ticket
# - AWS: Request via AWS Support
# - Vultr/Linode/Hetzner: Usually not blocked by default
```

---

## What's Different Now?

### Before (Broken)
❌ Hardcoded domain in DKIM config → DKIM not signing
❌ Hardcoded domains in nginx → Had to run SSL fix scripts
❌ Scattered shell scripts → Confusing deployment
❌ Manual certificate expansion → Error-prone

### After (Fixed)
✅ Dynamic DKIM config → Works with any domain
✅ Dynamic nginx config → SSL works out of the box
✅ Single docker-compose deployment → Plug and play
✅ Integrated SSL setup → One certbot command

---

## Maintenance

### Renewing SSL Certificates

```bash
# Certbot auto-renews, but to manually renew:
sudo certbot renew

# Copy new certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/

# Restart nginx to load new certs
docker compose restart nginx
```

### Checking DKIM Key

```bash
# View current DKIM public key
docker compose exec postfix cat /etc/opendkim/keys/$(docker compose exec postfix printenv MAIL_DOMAIN)/mail.txt

# Verify it matches DNS
host -t TXT mail._domainkey.yourdomain.com
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f postfix
docker compose logs -f dovecot
docker compose logs -f admin
docker compose logs -f nginx
```

---

## Summary

This deployment is now **truly plug and play**:

1. Configure DNS
2. Edit `.env` file
3. Run certbot once for SSL
4. Run `docker compose up -d`
5. Add DKIM DNS record from logs

**No scattered scripts, no manual fixes, no hardcoded values.**

Everything is configured via environment variables and runs automatically!
