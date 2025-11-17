# Configuration Guide

Complete reference for all Privra Mail Server configuration options.

---

## Environment Variables (`.env`)

### Required Settings

```bash
# Mail domain and hostname
MAIL_DOMAIN=yourdomain.com
MAIL_HOSTNAME=mail.yourdomain.com

# Database credentials
DB_NAME=privramail
DB_USER=privramail
DB_PASSWORD=your-secure-database-password

# Secret key for admin interface (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here
```

### Optional Settings

```bash
# Web interface hostnames (defaults to mail/admin.MAIL_DOMAIN)
WEBMAIL_HOSTNAME=mail.yourdomain.com
ADMIN_HOSTNAME=admin.yourdomain.com

# Admin email for Let's Encrypt notifications
ADMIN_EMAIL=admin@yourdomain.com

# PortID Authentication (optional - leave empty to disable)
PORTID_APP_ID=privra-mail-v1
PORTID_API_URL=http://localhost:5001
```

---

## DNS Configuration

### Required DNS Records

```dns
# Mail server A records
A     mail.yourdomain.com        →  YOUR_SERVER_IP
A     admin.yourdomain.com       →  YOUR_SERVER_IP

# MX record for email routing
MX    yourdomain.com             →  mail.yourdomain.com (priority 10)

# SPF record (anti-spoofing)
TXT   yourdomain.com             →  "v=spf1 mx ~all"

# DMARC record (email authentication policy)
TXT   _dmarc.yourdomain.com      →  "v=DMARC1; p=quarantine; rua=mailto:admin@yourdomain.com"

# DKIM record (generated automatically - see deployment logs)
TXT   mail._domainkey.yourdomain.com  →  "v=DKIM1; k=rsa; p=MIIBIjAN..."
```

### DNS Propagation

- **Propagation time**: 1-24 hours typically
- **Check propagation**: Use `dig` or online DNS checkers
- **Verify before deployment**: Ensure DNS is resolving correctly

```bash
# Check A records
dig mail.yourdomain.com
dig admin.yourdomain.com

# Check MX record
dig yourdomain.com MX

# Check SPF
dig yourdomain.com TXT | grep spf

# Check DKIM (after deployment)
dig mail._domainkey.yourdomain.com TXT
```

---

## SSL/TLS Certificates

### Let's Encrypt (Recommended)

```bash
# Get certificate for both domains
sudo certbot certonly --standalone \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --non-interactive

# Copy to project directory
sudo mkdir -p ./certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/
sudo chmod 644 ./certs/fullchain.pem
sudo chmod 600 ./certs/privkey.pem
```

### Certificate Renewal

```bash
# Certbot auto-renews via cron, but to manually renew:
sudo certbot renew

# Copy renewed certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/

# Restart nginx
docker compose restart nginx
```

---

## Docker Configuration

### Resource Limits

Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  postfix:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Port Mapping

Default ports (modify in `docker-compose.yml`):

```yaml
nginx:
  ports:
    - "80:80"      # HTTP (redirects to HTTPS)
    - "443:443"    # HTTPS (webmail + admin)
    - "25:25"      # SMTP (server-to-server)
    - "587:587"    # SMTP Submission (client-to-server)
    - "993:993"    # IMAPS (secure IMAP)
```

---

## Email Client Configuration

### IMAP (Incoming Mail)

```
Server: mail.yourdomain.com
Port: 993
Security: SSL/TLS
Username: your-email@yourdomain.com
Password: your-password
```

### SMTP (Outgoing Mail)

```
Server: mail.yourdomain.com
Port: 587
Security: STARTTLS
Authentication: Required
Username: your-email@yourdomain.com
Password: your-password
```

### Tested Clients

- ✅ iPhone/iPad Mail
- ✅ macOS Mail
- ✅ Mozilla Thunderbird
- ✅ Microsoft Outlook
- ✅ Gmail app (Android/iOS)

---

## Admin Panel Configuration

### URL Structure

```
https://admin.yourdomain.com/warofbest/
```

**Security Note**: The admin panel is hidden at the `/warofbest/` path. All other paths return 404.

### Changing Admin URL

Edit `nginx/nginx.conf.template`:

```nginx
# Change this path
location /warofbest/ {
    # to your custom path
    proxy_pass http://admin:5000/;
    ...
}
```

Then rebuild nginx:

```bash
docker compose build nginx
docker compose up -d nginx
```

---

## Firewall Configuration

### UFW (Ubuntu)

```bash
# Allow required ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 25/tcp    # SMTP
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 587/tcp   # Submission
sudo ufw allow 993/tcp   # IMAPS
sudo ufw enable
```

### iptables

```bash
# Allow required ports
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 25 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 587 -j ACCEPT
iptables -A INPUT -p tcp --dport 993 -j ACCEPT
```

---

## Performance Tuning

### PostgreSQL

Edit `docker-compose.yml`:

```yaml
db:
  environment:
    POSTGRES_SHARED_BUFFERS: 256MB
    POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
    POSTGRES_MAX_CONNECTIONS: 100
```

### Postfix Queue Size

Edit `postfix/main.cf`:

```
# Increase queue size
message_size_limit = 52428800    # 50MB
mailbox_size_limit = 0           # Unlimited
```

### Nginx Worker Processes

Edit `nginx/nginx.conf.template`:

```nginx
# Match number of CPU cores
worker_processes 4;
worker_connections 2048;
```

---

## Backup Configuration

### What to Backup

```bash
# 1. Database (user accounts, encryption keys)
docker compose exec db pg_dump -U privramail privramail > backup-db.sql

# 2. Mail storage (actual emails)
sudo tar -czf backup-mail.tar.gz docker-volumes/mail-storage/

# 3. DKIM keys
sudo tar -czf backup-dkim.tar.gz docker-volumes/dkim-keys/

# 4. Configuration
tar -czf backup-config.tar.gz .env docker-compose.yml certs/
```

### Automated Backups

Create `/etc/cron.daily/privra-backup`:

```bash
#!/bin/bash
BACKUP_DIR=/backup/privra/$(date +%Y-%m-%d)
mkdir -p $BACKUP_DIR

cd /path/to/Privra
docker compose exec -T db pg_dump -U privramail privramail > $BACKUP_DIR/db.sql
sudo cp -r docker-volumes/mail-storage $BACKUP_DIR/
sudo cp -r docker-volumes/dkim-keys $BACKUP_DIR/
tar -czf $BACKUP_DIR/config.tar.gz .env certs/

# Compress everything
tar -czf /backup/privra-$(date +%Y-%m-%d).tar.gz -C $BACKUP_DIR .
rm -rf $BACKUP_DIR

# Keep last 30 days
find /backup/privra-*.tar.gz -mtime +30 -delete
```

---

## Security Hardening

### Rate Limiting

Edit `postfix/main.cf`:

```
# Limit connections per client
anvil_rate_time_unit = 60s
smtpd_client_connection_count_limit = 10
smtpd_client_connection_rate_limit = 30
smtpd_client_message_rate_limit = 100
```

### Fail2ban Integration

Create `/etc/fail2ban/jail.local`:

```ini
[postfix-sasl]
enabled = true
port = smtp,submission,smtps
logpath = /var/log/mail.log
maxretry = 3
bantime = 3600

[dovecot]
enabled = true
port = imap,imaps,pop3,pop3s
logpath = /var/log/mail.log
maxretry = 3
bantime = 3600
```

### Admin Panel IP Whitelist

Edit `nginx/nginx.conf.template`:

```nginx
location /warofbest/ {
    # Only allow specific IPs
    allow 1.2.3.4;
    deny all;

    proxy_pass http://admin:5000/;
    ...
}
```

---

## Monitoring

### Check Service Status

```bash
# All services
docker compose ps

# Specific service
docker compose logs -f postfix
docker compose logs -f dovecot
docker compose logs -f admin
```

### Mail Queue

```bash
# View queue
docker compose exec postfix mailq

# Flush queue
docker compose exec postfix postqueue -f
```

### Disk Usage

```bash
# Check mail storage
sudo du -sh docker-volumes/mail-storage/

# Check database
sudo du -sh docker-volumes/db-data/
```

---

## Updating

```bash
# Pull latest code
git pull origin claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM

# Rebuild containers
docker compose build

# Restart with new images
docker compose up -d

# Check logs
docker compose logs -f
```

---

## Advanced Configuration

### Custom SMTP Relay

Edit `.env`:

```bash
# Use external SMTP relay (e.g., SendGrid, Mailgun)
SMTP_RELAY=smtp.sendgrid.net:587
SMTP_RELAY_USERNAME=apikey
SMTP_RELAY_PASSWORD=your-api-key
```

### Multiple Domains

Edit `postfix/main.cf`:

```
# Add additional domains
virtual_mailbox_domains = yourdomain.com, seconddomain.com, thirddomain.com
```

Then create users with both domains in admin panel.

---

For more help, see [Troubleshooting](TROUBLESHOOTING.md).
