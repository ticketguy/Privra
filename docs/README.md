# Privra Mail Documentation

Complete documentation for the Privra secure mail server system.

## Quick Start

```bash
./deploy.sh
```

One command deploys everything! For details, see [Deployment Guide](deployment/DEPLOY.md)

## Documentation Structure

### Architecture
- [Encryption Architecture](architecture/ENCRYPTION_ARCHITECTURE.md) - End-to-end encryption system design
- [PortID Integration](architecture/PORTID_ANALYSIS.md) - PortID authentication system
- [What is PortID](architecture/WHAT_IS_PORTID.md) - Overview of PortID
- [Reputation System](REPUTATION_SYSTEM.md) - Automated abuse prevention and trust scores

### Deployment
- [Deployment Guide](deployment/DEPLOY.md) - Complete deployment instructions

### Troubleshooting
- [NFT Import Error Fix](troubleshooting/FIX_NFT_IMPORT_ERROR.md) - Fix webmail container import error
- [DKIM Configuration](troubleshooting/DKIM-FIX-README.md) - DKIM email signing issues
- [SSL Certificate Setup](troubleshooting/SSL-CERT-FIX-README.md) - SSL certificate configuration
- [Git Conflicts](troubleshooting/GIT_CONFLICTS.md) - Resolving git divergent branches

### Guides
- [PortID Testing](guides/PORTID_TESTING.md) - Testing PortID integration

### History
Historical implementation documents and changelogs. See [history/](history/) folder.

## System Overview

Privra Mail is a privacy-focused email server with:

- **End-to-End Encryption**: Client-side email encryption using RSA
- **PortID Authentication**: Decentralized authentication system
- **Consent Management**: Control who can email you
- **Email Categorization**: Automatic email organization
- **Domain Verification**: Verify domain ownership via DNS

## Components

- **Postfix**: SMTP server for sending/receiving email
- **Dovecot**: IMAP server for email storage and retrieval
- **PostgreSQL**: User and domain database
- **Redis**: Session storage
- **Nginx**: Reverse proxy and SSL termination
- **Webmail**: Web-based email client
- **Admin Panel**: Domain and user management

## Common Tasks

### Deploy/Start the System
```bash
./deploy.sh
```

### Fix Issues
```bash
./deploy.sh fix
```

### Check Status
```bash
./deploy.sh status
```

### View Logs
```bash
./deploy.sh logs           # All services
./deploy.sh logs webmail   # Specific service
```

### Restart Services
```bash
./deploy.sh restart
```

### Rebuild Everything
```bash
./deploy.sh rebuild
```

### Stop the System
```bash
./deploy.sh stop
```

## Support

For issues and bug reports, please check the troubleshooting documentation first.
