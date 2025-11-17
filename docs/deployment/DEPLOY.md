# Deployment & Testing Guide

## What Was Fixed

Recent commits addressed Dovecot configuration issues:

1. **Removed LMTP protocol** - We only need IMAP for receiving mail
2. **Removed postfix user references** - Dovecot doesn't need to interact with Postfix via unix sockets
3. **Cleaned default configs** - Dockerfile now removes Ubuntu's default Dovecot configs that were overriding our custom settings

## Deploy Updates

On your server, run these commands:

```bash
cd ~/Privra
git pull origin claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM
docker compose build dovecot
docker compose up -d dovecot
```

Wait 10 seconds for Dovecot to start, then verify:

```bash
docker compose logs dovecot --tail=30
```

You should see:
- No error messages
- "Dovecot configured. Starting services..."
- "master: Dovecot v2.3.x starting up"

## Testing Checklist

### 1. Verify Port 993 is Listening

```bash
docker compose exec dovecot netstat -tlnp | grep 993
```

Expected output:
```
tcp  0  0.0.0.0:993  0.0.0.0:*  LISTEN  123/dovecot
```

### 2. Check Dovecot Configuration

```bash
docker compose exec dovecot doveconf -n | grep -E "(protocols|mail_location|ssl_cert|ssl_key)"
```

Expected output:
```
protocols = imap
mail_location = maildir:/var/mail/%d/%n
ssl_cert = </etc/ssl/mail/fullchain.pem
ssl_key = </etc/ssl/mail/privkey.pem
```

### 3. Test IMAP Connection from Server

```bash
openssl s_client -connect localhost:993 -quiet
```

Expected: You should see SSL certificate details and an IMAP greeting like:
```
* OK [CAPABILITY IMAP4rev1...] Dovecot ready.
```

Type `a1 LOGOUT` to exit.

### 4. Test External IMAP Connection

From your Windows machine or any external machine:

```bash
openssl s_client -connect mail.privra.xyz:993 -quiet
```

Expected: Same IMAP greeting as above.

### 5. Test IMAP Authentication

On the server:

```bash
docker compose exec dovecot doveadm auth test ticket@privra.xyz YOUR_PASSWORD
```

Expected output:
```
passdb: ticket@privra.xyz auth succeeded
userdb: ticket@privra.xyz
  user      : ticket@privra.xyz
  uid       : 5000
  gid       : 8
  home      : /var/mail/privra.xyz/ticket
  mail      : maildir:/var/mail/privra.xyz/ticket
```

### 6. Test Full IMAP Login

```bash
openssl s_client -connect localhost:993 -quiet
```

Once connected, type these commands:
```
a1 LOGIN ticket@privra.xyz YOUR_PASSWORD
a2 LIST "" "*"
a3 SELECT INBOX
a4 LOGOUT
```

Expected responses:
- `a1 OK Logged in`
- `a2 OK List completed`
- `a3 OK [READ-WRITE] Select completed`

## Configure Email Client

Once all tests pass, configure your email client:

### IMAP Settings (Receiving Mail)
- Server: mail.privra.xyz
- Port: 993
- Security: SSL/TLS
- Username: ticket@privra.xyz (or sammie@privra.xyz)
- Password: (the password you set in admin interface)

### SMTP Settings (Sending Mail)
- Server: mail.privra.xyz
- Port: 587
- Security: STARTTLS
- Username: ticket@privra.xyz
- Password: (same as above)
- Authentication: Required

## Troubleshooting

### Dovecot Not Listening on 993

Check logs:
```bash
docker compose logs dovecot --tail=50
```

Check if process is running:
```bash
docker compose exec dovecot ps aux | grep dovecot
```

Verify config syntax:
```bash
docker compose exec dovecot doveconf -n
```

### Authentication Failures

Check database connection:
```bash
docker compose exec dovecot doveconf -n | grep connect
```

Test database query manually:
```bash
docker compose exec db psql -U privramail -d privramail -c "SELECT email, active FROM users;"
```

List users:
```bash
docker compose exec admin python manage.py listusers
```

### Certificate Issues

Verify certificates are mounted:
```bash
docker compose exec dovecot ls -la /etc/ssl/mail/
```

Check certificate validity:
```bash
openssl x509 -in certs/fullchain.pem -text -noout | grep -E "(Subject:|Not Before|Not After)"
```

## Next Steps

Once all tests pass:
1. Configure your iPhone/Gmail email client
2. Send a test email to ticket@privra.xyz
3. Check if it appears in the mailbox
4. Send an email from ticket@privra.xyz
5. Verify external delivery

## Management Commands

Add user:
```bash
docker compose exec admin python manage.py adduser user@privra.xyz password123
```

Delete user:
```bash
docker compose exec admin python manage.py deluser user@privra.xyz
```

Change password:
```bash
docker compose exec admin python manage.py passwd user@privra.xyz newpassword
```

List all users:
```bash
docker compose exec admin python manage.py listusers
```
