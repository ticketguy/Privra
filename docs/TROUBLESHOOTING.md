# Troubleshooting Guide

Common issues and solutions for Privra Mail Server.

---

## OpenDKIM Issues

### OpenDKIM Crashes on Startup

**Error**: `opendkim: /etc/opendkim.conf: /etc/opendkim/keys/privra.xyz/mail.private is in group 106 which has multiple users`

**Solution**: Permission issue with DKIM private key.

```bash
# Rebuild postfix with fixed permissions
docker compose down postfix
docker compose build --no-cache postfix
docker compose up -d postfix

# Verify OpenDKIM is running
docker compose exec postfix ps aux | grep opendkim
```

### DKIM Not Signing Emails

**Symptoms**: mail-tester.com shows "not signed with DKIM"

**Checks**:

```bash
# 1. Verify OpenDKIM is running
docker compose exec postfix ps aux | grep opendkim

# 2. Check DKIM configuration
docker compose exec postfix cat /etc/opendkim.conf | grep Domain
# Should show your domain, not hardcoded value

# 3. Check milter configuration
docker compose exec postfix postconf | grep milter
# Should show: smtpd_milters = inet:localhost:8891

# 4. Check DNS record
host -t TXT mail._domainkey.yourdomain.com
# Should return DKIM public key
```

**Solution**:

```bash
# If DNS record missing, get it from logs
docker compose logs postfix | grep "DKIM DNS Record" -A 10

# Add to DNS, wait for propagation (up to 24 hours)
# Then test again
```

---

## SSL/TLS Issues

### Certificate Not Found

**Error**: `nginx: [emerg] cannot load certificate "/etc/ssl/mail/fullchain.pem"`

**Solution**: SSL certificates not copied to `./certs/`

```bash
# Get certificates first
sudo certbot certonly --standalone \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Copy to project directory
sudo mkdir -p ./certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/
sudo chmod 644 ./certs/fullchain.pem
sudo chmod 600 ./certs/privkey.pem

# Restart nginx
docker compose up -d nginx
```

### Certificate Doesn't Include Admin Domain

**Error**: Browser shows "certificate doesn't match admin.yourdomain.com"

**Solution**: Expand certificate to include both domains

```bash
# Stop nginx
docker compose down nginx

# Expand certificate
sudo certbot certonly --standalone \
  --cert-name mail.yourdomain.com \
  --expand \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Copy new certificate
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/

# Start nginx
docker compose up -d nginx
```

---

## Email Delivery Issues

### Cannot Send to External Domains (Gmail, Outlook)

**Symptoms**: Emails to Gmail/Outlook not delivered, stuck in queue

**Cause**: Port 25 blocked by hosting provider

**Check**:

```bash
# Test if port 25 is open
telnet gmail-smtp-in.l.google.com 25
# If connection fails, port 25 is blocked
```

**Solution**:

1. **DigitalOcean**: Submit support ticket requesting port 25 access
2. **AWS**: Request via AWS Support
3. **Vultr/Linode/Hetzner**: Usually not blocked by default

**Alternative**: Use SMTP relay (SendGrid, Mailgun, etc.) - see [Configuration Guide](CONFIGURATION.md).

### Emails Going to Spam

**Symptoms**: Emails delivered but go to spam folder

**Causes & Solutions**:

```bash
# 1. Check DKIM, SPF, DMARC
# Go to https://www.mail-tester.com/
# Send test email and check score

# 2. Verify DNS records
dig yourdomain.com TXT | grep spf
dig mail._domainkey.yourdomain.com TXT
dig _dmarc.yourdomain.com TXT

# 3. Check if IP is blacklisted
# Go to https://mxtoolbox.com/blacklists.aspx
# Enter your server IP

# 4. Set up reverse DNS (PTR record)
# Contact your hosting provider to set PTR record
# Should point to mail.yourdomain.com
```

### Cannot Receive External Emails

**Symptoms**: Cannot receive emails from Gmail/Outlook

**Checks**:

```bash
# 1. Verify MX record
dig yourdomain.com MX
# Should return: yourdomain.com. IN MX 10 mail.yourdomain.com.

# 2. Check A record
dig mail.yourdomain.com
# Should return your server IP

# 3. Test SMTP port
telnet yourdomain.com 25
# Should connect

# 4. Check Postfix logs
docker compose logs postfix | tail -50
```

---

## Admin Panel Issues

### Cannot Access Admin Panel

**Error**: 404 Not Found

**Solution**: Admin panel is at hidden URL

```
Correct URL: https://admin.yourdomain.com/warofbest/
Wrong URL: https://admin.yourdomain.com/ (returns 404)
```

### Admin Panel Shows 500 Error

**Symptoms**: Internal Server Error when accessing admin

**Checks**:

```bash
# 1. Check admin logs
docker compose logs admin | tail -50

# 2. Check database connection
docker compose exec admin python -c "import psycopg2; psycopg2.connect(host='db', database='privramail', user='privramail', password='your-password')"

# 3. Check if database is initialized
docker compose exec admin python init_db.py

# 4. Restart admin service
docker compose restart admin
```

---

## Webmail Issues

### Webmail Shows 504 Gateway Timeout

**Symptoms**: Webmail loads slowly or times out

**Cause**: Dovecot IMAP connection issues

**Solution**:

```bash
# 1. Check Dovecot is running
docker compose ps dovecot

# 2. Check Dovecot logs
docker compose logs dovecot | tail -50

# 3. Test IMAP connection
docker compose exec webmail nc -zv dovecot 993

# 4. Restart Dovecot
docker compose restart dovecot
```

### Cannot Login to Webmail

**Error**: Invalid credentials

**Checks**:

```bash
# 1. Verify user exists
docker compose exec admin python manage.py listusers

# 2. Reset password
docker compose exec admin python manage.py passwd user@yourdomain.com newpassword

# 3. Check IMAP authentication
docker compose logs dovecot | grep -i auth
```

---

## Docker Issues

### Containers Keep Restarting

**Symptoms**: `docker compose ps` shows containers constantly restarting

**Solution**:

```bash
# Check which service is failing
docker compose ps

# View logs of failing service
docker compose logs <service-name>

# Common causes:
# - Missing .env variables
# - Database not initialized
# - Port conflicts
```

### Environment Variable Not Set Warning

**Error**: `WARN[0000] The "MAIL_HOSTNAME" variable is not set. Defaulting to a blank string.`

**Solution**:

```bash
# 1. Check .env file exists
ls -la .env

# 2. Verify variables are set
cat .env | grep MAIL_HOSTNAME

# 3. Source .env file
set -a; source .env; set +a

# 4. Restart services
docker compose down
docker compose up -d
```

### Port Already in Use

**Error**: `Error starting userland proxy: listen tcp 0.0.0.0:25: bind: address already in use`

**Solution**:

```bash
# Find what's using the port
sudo lsof -i :25

# If it's Postfix installed on host
sudo systemctl stop postfix
sudo systemctl disable postfix

# Restart docker compose
docker compose up -d
```

---

## Database Issues

### Database Connection Failed

**Error**: `could not connect to server: Connection refused`

**Solution**:

```bash
# 1. Check database is running
docker compose ps db

# 2. Check database logs
docker compose logs db | tail -50

# 3. Verify database password
docker compose exec db psql -U privramail -d privramail -c "SELECT 1"

# 4. Restart database
docker compose restart db
```

### Database Not Initialized

**Error**: `relation "users" does not exist`

**Solution**:

```bash
# Initialize database
docker compose exec admin python init_db.py

# Verify tables exist
docker compose exec db psql -U privramail -d privramail -c "\dt"
```

---

## DNS Issues

### DNS Not Propagating

**Symptoms**: DNS records added but not resolving

**Check**:

```bash
# Check from different DNS servers
dig @8.8.8.8 mail.yourdomain.com
dig @1.1.1.1 mail.yourdomain.com

# Check SOA record to see last update
dig yourdomain.com SOA
```

**Solution**: Wait 1-24 hours for propagation, or flush DNS caches.

### DKIM Record Format Invalid

**Error**: "DKIM record format invalid" on mail-tester

**Solution**:

```bash
# Get correct format from logs
docker compose logs postfix | grep -A 20 "DKIM DNS Record"

# DNS record should be:
# Host: mail._domainkey
# Type: TXT
# Value: "v=DKIM1; k=rsa; p=MIIBIjAN..."

# Make sure to:
# 1. Remove line breaks from public key
# 2. Include quotes around entire value
# 3. Use correct selector (mail)
```

---

## Performance Issues

### High CPU Usage

**Symptoms**: Server slow, high CPU usage

**Check**:

```bash
# Check which container is using CPU
docker stats

# Check logs for errors
docker compose logs | grep -i error | tail -50
```

**Solutions**:

```bash
# 1. Limit container resources (see Configuration Guide)

# 2. Check for mail loops
docker compose exec postfix mailq | grep -c "Connection timed out"

# 3. Increase server resources
# Upgrade to server with more CPU/RAM
```

### High Disk Usage

**Symptoms**: Disk space filling up

**Check**:

```bash
# Check disk usage
df -h

# Check mail storage
sudo du -sh docker-volumes/mail-storage/

# Check database
sudo du -sh docker-volumes/db-data/

# Check logs
sudo du -sh /var/lib/docker/containers/
```

**Solution**:

```bash
# 1. Clean old emails (implement retention policy)

# 2. Rotate Docker logs
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
sudo systemctl restart docker

# 3. Clean Docker system
docker system prune -a
```

---

## Getting Help

### Log Collection

When reporting issues, include:

```bash
# System info
uname -a
docker --version
docker compose version

# Service status
docker compose ps

# Logs (last 100 lines of each service)
docker compose logs --tail=100 > privra-logs.txt

# Configuration (remove passwords!)
cat .env | grep -v PASSWORD > privra-config.txt
```

### Useful Commands

```bash
# Full restart
docker compose down && docker compose up -d

# Rebuild everything
docker compose build --no-cache && docker compose up -d

# Reset everything (DANGER: deletes data!)
docker compose down -v
rm -rf docker-volumes/
docker compose up -d
```

---

For more help:
- [GitHub Issues](https://github.com/ticketguy/Privra/issues)
- [Configuration Guide](CONFIGURATION.md)
- [Deployment Guide](DEPLOYMENT.md)
