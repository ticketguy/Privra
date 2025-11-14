# Changelog

## 2025-11-13 - Dovecot Configuration Fixes

### Fixed
- **Dovecot container crash on startup** - Removed LMTP protocol which was causing fatal errors
- **Missing postfix user reference** - Removed unix socket configurations that referenced non-existent postfix user
- **Default config override issue** - Modified Dockerfile to remove Ubuntu's default Dovecot configs before copying custom configs
  - This was preventing Dovecot from using our custom settings (mail_location, SSL certs, etc.)
  - Default configs were overriding our settings even though we had them in place

### Changes
- `dovecot/Dockerfile`: Added `rm -rf /etc/dovecot/conf.d/*` to remove default configs
- `dovecot/dovecot.conf`: Changed `protocols = imap lmtp` to `protocols = imap`
- `dovecot/conf.d/10-master.conf`: Removed LMTP service and unix socket configurations
- `README.md`: Fixed admin panel URL to `https://mail.yourdomain.com/` (not `/admin`)

### Testing
- Port 993 should now be listening properly
- Dovecot should load our custom configurations correctly
- IMAP authentication should work with PostgreSQL-backed users

### Verification Steps
See `DEPLOY.md` for complete deployment and testing instructions.

Quick verification:
```bash
docker compose logs dovecot --tail=30  # Should show no errors
docker compose exec dovecot netstat -tlnp | grep 993  # Should show port listening
docker compose exec dovecot doveconf -n | grep mail_location  # Should show maildir:/var/mail/%d/%n
```

## Previous Commits

### 2025-11-13 - Complete Mail Server Rebuild
- Removed complex Mailu setup
- Built simple mail server from scratch with: Postfix, Dovecot, PostgreSQL, Redis, Nginx, Flask
- Created docker-compose orchestration
- Implemented one-command setup script
- Added SSL certificate management with Let's Encrypt
- Built web admin interface for user management

### Key Architecture Decisions
- **PostgreSQL over SQLite** - More reliable for production use
- **Nginx as reverse proxy** - Handles SSL termination and TCP proxying for mail ports
- **Flask admin interface** - Simple, lightweight user management
- **Maildir format** - Industry standard for email storage
- **SASL authentication** - Dovecot provides auth for both IMAP and SMTP
