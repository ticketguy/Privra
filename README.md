# Privra Mail Server

A simple, reliable mail server built from scratch. **Plug and play** - no complex setup.

## Quick Start

```bash
git clone https://github.com/ticketguy/Privra.git
cd Privra
./deploy.sh
```

**That's it!** The script will:
1. Check Docker installation
2. Create .env from template (edit and run again)
3. Initialize database
4. Start all services
5. Show access URLs

Your mail server is ready in 5 minutes.

## Features

- ✅ **Fully Working** - Send & receive emails instantly
- ✅ **Webmail** - Built-in email client (no Gmail/Outlook needed)
- ✅ **SMTP + IMAP** - Works with any email client
- ✅ **SSL/TLS** - Automatic Let's Encrypt certificates
- ✅ **Simple Admin** - Web interface to manage users
- ✅ **PostgreSQL** - Reliable user database
- ✅ **LMTP Delivery** - Modern, reliable mail delivery
- ✅ **Reputation System** - Automated abuse prevention with trust scores
- ✅ **End-to-End Encryption** - Client-side email encryption
- ✅ **Consent Management** - Control who can email you

## Access

- **Webmail**: http://mail.yourdomain.com:8443
- **Admin Panel**: https://mail.yourdomain.com

### External Email Clients (iPhone, Gmail, Thunderbird)

**IMAP (Incoming):**
- Server: mail.yourdomain.com
- Port: 993
- Security: SSL/TLS

**SMTP (Outgoing):**
- Server: mail.yourdomain.com
- Port: 587
- Security: STARTTLS

## Architecture

- **Postfix** - SMTP server (email sending/receiving)
- **Dovecot** - IMAP server (email reading)
- **Webmail** - Built-in email client (Flask)
- **Admin** - User management interface (Flask)
- **PostgreSQL** - User accounts database
- **Redis** - Session storage
- **Nginx** - SSL termination & reverse proxy

## Management

### Using Deploy Script
```bash
# View status
./deploy.sh status

# View logs
./deploy.sh logs

# Fix issues (rebuilds webmail, checks DKIM, etc)
./deploy.sh fix

# Restart services
./deploy.sh restart

# Rebuild everything
./deploy.sh rebuild
```

### Via Admin Panel (Easy)
Go to https://mail.yourdomain.com/warofbest and manage users with the web interface.

### Via Command Line
```bash
# Add user
docker compose exec admin python manage.py adduser user@domain.com password

# Delete user
docker compose exec admin python manage.py deluser user@domain.com

# Change password
docker compose exec admin python manage.py passwd user@domain.com newpassword
```

## What's Next?

1. **Test External Email** - Send email to Gmail/Outlook to verify delivery
2. **Configure DNS Records** - Add SPF, DKIM, DMARC for better deliverability
3. **Backup Setup** - Backup `/var/lib/docker/volumes/privra-mail_mail-storage`
4. **Monitor** - Check logs regularly: `docker compose logs -f`

## Requirements

- Ubuntu 20.04+ server
- Domain with A record pointing to your server
- Ports open: 25, 80, 443, 587, 993, 8443

### Important: Port 25 (SMTP)

**Cloud providers block port 25 by default** to prevent spam. You need to request it be unblocked:

**DigitalOcean**: Submit a support ticket requesting port 25 access (usually approved within hours)
**AWS/Azure**: Similar process - request via support
**Alternatives**: Vultr, Linode, Hetzner, OVH don't block port 25

Until port 25 is unblocked:
- ✅ You can **receive** emails from anyone
- ✅ You can send emails **internally** (user@yourdomain.com to user@yourdomain.com)
- ❌ You **cannot send** to external servers (Gmail, Outlook, etc.)

Once unblocked, your server is **fully independent** with no external dependencies.

## Documentation

**Comprehensive documentation** available in the [`docs/`](docs/) directory:

- [System Overview](docs/SYSTEM_OVERVIEW.md) - Complete technical documentation
- [Deployment Guide](docs/deployment/DEPLOY.md) - Production deployment
- [Troubleshooting](docs/troubleshooting/) - Common issues and fixes
- [Architecture](docs/architecture/) - System design and encryption

## Troubleshooting

### Any Issues? One Command to Fix

```bash
./deploy.sh fix
```

This automatically:
- Rebuilds webmail container
- Fixes SSL certificate chains
- Checks DKIM configuration
- Restarts all services

### Other Common Commands

```bash
./deploy.sh status    # Check what's running
./deploy.sh logs      # View all logs
./deploy.sh rebuild   # Nuclear option - rebuild everything
```

### Detailed Troubleshooting

Check the [troubleshooting directory](docs/troubleshooting/) for:
- DKIM configuration issues
- SSL certificate problems
- Database connection errors
- Git conflict resolution

## Support

Built with simplicity in mind. If it breaks, it's easy to fix.

No complex configurations, no hidden dependencies, no surprises.
