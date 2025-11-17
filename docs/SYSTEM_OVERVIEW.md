# Privra Mail - System Overview

Complete technical overview of the Privra secure mail server system.

## Table of Contents

1. [Architecture](#architecture)
2. [Components](#components)
3. [Data Flow](#data-flow)
4. [Security Features](#security-features)
5. [Configuration](#configuration)
6. [Maintenance](#maintenance)

## Architecture

Privra Mail is built as a microservices architecture using Docker containers:

```
Internet
    ↓
[Nginx] ← SSL Termination & Reverse Proxy
    ↓
    ├─→ [Postfix:25,587] ← SMTP (Email In/Out)
    ├─→ [Dovecot:993] ← IMAP (Email Storage)
    ├─→ [Webmail:5001] ← Web Email Client
    └─→ [Admin:5000] ← Admin Panel
         ↓
    [PostgreSQL] ← User Database
    [Redis] ← Session Storage
```

## Components

### 1. Postfix (SMTP Server)
**Purpose**: Handles incoming and outgoing email

**Features**:
- SMTP submission on port 587
- TLS encryption for transit
- Virtual domain support
- PostgreSQL backend for users
- Content filtering (encryption/decryption)
- DKIM email signing
- Consent-based filtering

**Configuration**: `postfix/`
- `main.cf` - Main Postfix configuration
- `master.cf` - Service definitions
- `consent_policy.py` - Consent checking policy
- `encrypt_filter.py` - Gateway encryption filter
- `decrypt_filter.py` - Gateway decryption filter

### 2. Dovecot (IMAP Server)
**Purpose**: Stores and serves email to clients

**Features**:
- IMAP over SSL (port 993)
- PostgreSQL authentication
- Maildir storage format
- Virtual domain support

**Configuration**: `dovecot/`
- `dovecot.conf` - Main configuration
- `dovecot-sql.conf.ext` - Database queries

### 3. PostgreSQL (Database)
**Purpose**: Stores users, domains, settings

**Schema**:
- `users` - User accounts and encryption keys
- `domains` - Virtual email domains
- `sender_whitelist` - Approved senders
- `sender_blacklist` - Blocked senders
- `consent_settings` - Per-user consent rules
- `consent_requests` - Pending consent requests

### 4. Redis (Cache/Sessions)
**Purpose**: Stores web sessions

### 5. Nginx (Reverse Proxy)
**Purpose**: SSL termination and routing

**Routes**:
- `https://domain.com/` → Webmail
- `https://domain.com/warofbest` → Admin Panel
- `smtp://domain.com:587` → Postfix SMTP
- `imaps://domain.com:993` → Dovecot IMAP

### 6. Webmail (Python Flask)
**Purpose**: Web-based email client

**Features**:
- Read/compose email via IMAP/SMTP
- Client-side end-to-end encryption
- PortID authentication support
- Consent management UI
- Email categorization
- Public key lookup API

**Endpoints**:
- `/` - Inbox
- `/compose` - Send email
- `/settings/consent` - Manage consent
- `/api/pubkey/<email>` - Public key lookup

### 7. Admin Panel (Python Flask)
**Purpose**: Domain and user management

**Features**:
- Add/remove domains
- Create/manage users
- View system stats
- PortID authentication support

## Data Flow

### Incoming Email
```
External SMTP Server
    ↓
Nginx :25 → Postfix :25
    ↓
Consent Policy Check (postfix/consent_policy.py)
    ↓ (if approved)
Encryption Filter (postfix/encrypt_filter.py)
    ↓
Dovecot (IMAP storage)
    ↓
Webmail/IMAP Client
```

### Outgoing Email
```
Webmail/SMTP Client
    ↓
Nginx :587 → Postfix :587
    ↓
DKIM Signing (OpenDKIM)
    ↓
External SMTP Server
```

### Email Composition (Encrypted)
```
Webmail Browser
    ↓
Lookup recipient public key (/api/pubkey/<email>)
    ↓
Encrypt email client-side (JavaScript)
    ↓
Send via SMTP
    ↓
Email stored/transmitted encrypted
```

## Security Features

### 1. End-to-End Encryption

**Client-Side Encryption**:
- RSA-4096 keys generated per user
- Private key encrypted with recovery key
- Public keys stored in database
- JavaScript encryption in webmail

**Gateway Encryption**:
- Encrypts external (non-Privra) emails
- Transparent to external senders
- Uses recipient's public key

### 2. Consent Management

Users can configure:
- **Require Consent**: Block all emails except from approved senders
- **Whitelist Mode**: Only allow whitelisted senders
- **Blacklist**: Block specific senders/domains
- **Whitelist**: Approve specific senders/domains

### 3. PortID Authentication

Decentralized authentication system:
- No password storage required
- Users authenticate via PortID app
- Linked to email accounts

### 4. DKIM Email Signing

- Domain-based email signing
- Prevents email spoofing
- Improves deliverability

### 5. Transport Security

- TLS for SMTP submission
- SSL for IMAP connections
- HTTPS for web interfaces

## Configuration

### Environment Variables

Create `.env` file based on `.env.example`:

```bash
# Domain settings
MAIL_DOMAIN=example.com
MAIL_HOSTNAME=mail.example.com

# Database
DB_NAME=privramail
DB_USER=privramail
DB_PASSWORD=secure_password_here

# Security
SECRET_KEY=generate_random_key_here

# PortID (optional)
PORTID_APP_ID=privra-mail-v1
PORTID_API_URL=http://localhost:5001
```

### SSL Certificates

Place certificates in `certs/`:
- `certs/mail.crt` - SSL certificate
- `certs/mail.key` - Private key

Run `./deploy.sh fix` to automatically expand certificate chains if needed.

### DKIM Keys

Generated automatically in `dkim-keys/` volume.

Use `./deploy.sh fix` to verify DKIM configuration (displays DNS record to add).

## Maintenance

### Using Deploy Script (Recommended)

```bash
# View status
./deploy.sh status

# View logs (all services)
./deploy.sh logs

# View logs (specific service)
./deploy.sh logs webmail

# Fix issues automatically
./deploy.sh fix

# Restart all services
./deploy.sh restart

# Rebuild everything
./deploy.sh rebuild

# Stop all services
./deploy.sh stop

# Start all services
./deploy.sh start
```

### Direct Docker Commands

If you prefer direct control:

```bash
# View logs
docker compose logs -f
docker compose logs -f webmail

# Restart service
docker compose restart [service]

# Rebuild service
docker compose build --no-cache [service]
docker compose up -d [service]
```

### Backup Database
```bash
docker compose exec db pg_dump -U privramail privramail > backup.sql
```

### Restore Database
```bash
docker compose exec -T db psql -U privramail privramail < backup.sql
```

### Check Email Queue
```bash
docker compose exec postfix mailq
```

### Clear Email Queue
```bash
docker compose exec postfix postsuper -d ALL
```

## Performance Tuning

### Postfix
- Adjust `maxproc` in `master.cf` for concurrent connections
- Tune `message_size_limit` for large attachments

### Dovecot
- Adjust `mail_max_userip_connections` for IMAP connections
- Enable `mail_cache` for better performance

### PostgreSQL
- Increase `shared_buffers` for more cache
- Tune `max_connections` based on load

### Webmail
- Adjust gunicorn workers in `Dockerfile`
- Enable Redis session caching

## Troubleshooting

See [troubleshooting/](troubleshooting/) directory for detailed guides.

### Quick Fix

For most issues, run:

```bash
./deploy.sh fix
```

This automatically:
- Rebuilds webmail container
- Fixes SSL certificate chains
- Checks and displays DKIM configuration
- Restarts all services

### Common Issues

1. **Webmail won't start**: Run `./deploy.sh fix`
2. **DKIM not working**: Run `./deploy.sh fix` to see DNS record, then add to your DNS
3. **SSL errors**: Run `./deploy.sh fix` to expand certificate chain
4. **Email not delivering**: Check Postfix logs with `./deploy.sh logs postfix`
5. **Any service failing**: Try `./deploy.sh rebuild` for nuclear option

## Monitoring

### Health Checks

Quick status check:

```bash
./deploy.sh status
```

Manual checks:

```bash
# Check all services
docker compose ps

# Check database
docker compose exec db pg_isready -U privramail

# Check Redis
docker compose exec redis redis-cli ping
```

### Metrics
- Postfix: Check `/var/log/mail.log` in container
- Dovecot: Check `/var/log/dovecot.log` in container
- Webmail: Check gunicorn access logs
- Nginx: Check `/var/log/nginx/` in container

## Development

### Local Testing
```bash
# Start services
docker compose up

# Run tests
docker compose exec webmail pytest

# Access database
docker compose exec db psql -U privramail privramail
```

### Making Changes
1. Edit source files in respective directories
2. Rebuild affected service: `docker compose build [service]`
3. Restart service: `docker compose up -d [service]`
4. Test changes
5. Commit to git

## API Reference

### Webmail Public Key Lookup

**Endpoint**: `GET /api/pubkey/<email>`

**Response**:
```json
{
  "email": "user@example.com",
  "public_key": "-----BEGIN PUBLIC KEY-----...",
  "is_privra": true,
  "encrypted": true
}
```

**Status Codes**:
- 200: User found with encryption
- 404: User not found or no encryption keys

## Further Reading

- [Encryption Architecture](architecture/ENCRYPTION_ARCHITECTURE.md)
- [Deployment Guide](deployment/DEPLOY.md)
- [PortID Integration](architecture/PORTID_ANALYSIS.md)
