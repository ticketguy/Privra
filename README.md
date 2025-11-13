# Privra Mail Server

A simple, reliable mail server built from scratch. No complexity, just works.

## Features

- ✅ **SMTP** (Postfix) - Send and receive email
- ✅ **IMAP** (Dovecot) - Read email from any client
- ✅ **Webmail** - Built-in email client, no setup needed
- ✅ **SSL/TLS** - Automatic Let's Encrypt certificates
- ✅ **Simple Admin** - Web interface to manage users
- ✅ **PostgreSQL** - Reliable user database
- ✅ **Redis** - Fast session storage

## One-Command Setup

```bash
git clone https://github.com/ticketguy/Privra.git
cd Privra
./setup.sh
```

That's it! Your mail server is ready.

## Requirements

- Ubuntu 20.04+ server
- Domain name pointing to your server
- Ports 25, 80, 443, 587, 993 open

## Configuration

1. Copy `.env.example` to `.env`
2. Edit `.env` with your domain and settings
3. Run `./setup.sh`

## Usage

### Webmail (Built-in Email Client)
**https://mail.yourdomain.com/mail**

Login with your email credentials. Read, compose, and send emails instantly!

### Admin Panel (User Management)
**https://mail.yourdomain.com/**

Manage users, passwords, and domains.

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

```bash
# Add user
docker compose exec admin python manage.py adduser user@domain.com password

# Delete user
docker compose exec admin python manage.py deluser user@domain.com

# Change password
docker compose exec admin python manage.py passwd user@domain.com newpassword

# View logs
docker compose logs -f
```

## Support

Built with simplicity in mind. If it breaks, it's easy to fix.

No complex configurations, no hidden dependencies, no surprises.
