# 🔐 Privra Mail Server

**Privacy-first, self-hosted email server powered by Docker**

A complete, encrypted email solution built on [Mailu](https://mailu.io) with privacy and sovereignty at its core.

---

## ✨ Features

- **🔒 Privacy by Default**: Encryption at rest enabled
- **🌐 Web Interface**: Full-featured admin panel and webmail (Roundcube)
- **📧 Complete Mail Stack**: SMTP, IMAP, anti-spam (Rspamd)
- **🎯 Easy Deployment**: One-command setup on any server
- **🔧 Fully Customizable**: Override any component configuration
- **📦 Portable**: Entire setup in one directory - move anywhere
- **🆔 PortID Ready**: Built to integrate with PortID authentication

---

## 🚀 Quick Start

### Prerequisites

- DigitalOcean Droplet (or any Linux server) with:
  - **2GB RAM minimum** (4GB recommended)
  - Ubuntu 22.04 LTS
  - Public IP address
  - Domain name with DNS access

### 1. DNS Configuration (CRITICAL!)

Before deploying, configure these DNS records:

```
A     mail.privra.com        →  YOUR_SERVER_IP
MX    privra.com             →  mail.privra.com (priority 10)
TXT   privra.com             →  "v=spf1 mx ~all"
TXT   _dmarc.privra.com      →  "v=DMARC1; p=quarantine; rua=mailto:admin@privra.com"
```

**Note**: DNS propagation can take up to 24 hours. Verify with:
```bash
dig mail.privra.com
dig privra.com MX
```

### 2. Clone Repository on Your Server

```bash
# SSH into your DigitalOcean Droplet
ssh root@YOUR_SERVER_IP

# Clone the repository
git clone https://github.com/YOUR_USERNAME/Privra.git
cd Privra

# Switch to the mail server branch
git checkout claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM
```

### 3. Run Setup Script

```bash
# Make script executable
chmod +x setup.sh

# Run setup
sudo ./setup.sh
```

The script will:
- ✅ Install Docker if needed
- ✅ Generate secure SECRET_KEY
- ✅ Create required directories
- ✅ Pull Docker images
- ✅ Configure your domain

### 4. Start Mail Server

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# Follow logs
docker compose logs -f
```

### 5. Create Admin Account

```bash
# Replace PASSWORD with a strong password
docker compose exec admin flask mailu admin admin privra.com YOUR_STRONG_PASSWORD
```

### 6. Access Your Mail Server

- **Admin Panel**: `https://mail.privra.com/admin`
- **Webmail**: `https://mail.privra.com/webmail`
- **First login**: `admin@privra.com` with your password

---

## 📂 Directory Structure

```
Privra/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Configuration (CUSTOMIZE THIS!)
├── setup.sh                    # Setup script
├── README.md                   # This file
│
├── data/                       # Persistent data
├── mail/                       # User mailboxes
├── dkim/                       # DKIM keys (auto-generated)
├── certs/                      # TLS certificates
├── filter/                     # Anti-spam data
├── webmail/                    # Webmail data
├── mailqueue/                  # Mail queue
└── overrides/                  # Custom configurations
    ├── nginx/
    ├── postfix/
    ├── dovecot/
    ├── rspamd/
    └── roundcube/
```

**Important**: The entire mail system is in this directory. To migrate:
1. Stop services: `docker compose down`
2. Copy entire directory to new server
3. Start services: `docker compose up -d`

---

## 🔧 Configuration

### Essential Settings (`.env` file)

```bash
# Your domain
DOMAIN=privra.com
HOSTNAMES=mail.privra.com

# TLS (Let's Encrypt auto-certificates)
TLS_FLAVOR=letsencrypt

# Features
ADMIN=true                    # Web admin interface
WEBMAIL=roundcube            # Webmail client
ANTIVIRUS=none               # ClamAV requires 2GB+ RAM
ENCRYPTION=true              # At-rest encryption

# Limits
MESSAGE_SIZE_LIMIT=50000000  # 50MB max email size
AUTH_RATELIMIT_IP=60/hour    # Rate limiting
```

### Customization Levels

#### Level 1: Configuration (Easy)
Edit `.env` file - changes persist across updates

#### Level 2: Overrides (Intermediate)
Add custom configs in `overrides/` directory:
```bash
# Example: Custom Nginx config
echo "client_max_body_size 100M;" > overrides/nginx/custom.conf
docker compose restart front
```

#### Level 3: Custom Images (Advanced)
Modify `docker-compose.yml` to use custom Dockerfiles

---

## 🎯 Creating Email Accounts

### Via Web Interface (Recommended)
1. Login to admin panel: `https://mail.privra.com/admin`
2. Navigate to "Mail Domains" → "Users"
3. Click "Add User"
4. Create user (e.g., `peter@privra.com`)

### Via Command Line
```bash
docker compose exec admin flask mailu user peter privra.com 'STRONG_PASSWORD'
```

---

## 📊 What You Can See Right Now

Once running, you have access to:

### 1. **Admin Dashboard** (`/admin`)
- Create/manage users
- View mail queue
- Monitor spam filter
- Check logs
- Manage domains

### 2. **Webmail Interface** (`/webmail`)
- Send/receive emails
- Organize folders
- Manage contacts
- Configure filters
- Change password

### 3. **Real-time Logs**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f smtp
docker compose logs -f admin
docker compose logs -f antispam
```

---

## 🛠️ Maintenance Commands

```bash
# View status
docker compose ps

# Restart specific service
docker compose restart smtp

# Update to latest version
docker compose pull
docker compose up -d

# Backup
tar -czf privra-backup-$(date +%Y%m%d).tar.gz data/ mail/ dkim/ .env

# Restore
tar -xzf privra-backup-YYYYMMDD.tar.gz
```

---

## 🔐 Security Checklist

- [ ] DNS records configured (MX, SPF, DMARC)
- [ ] Firewall configured (UFW or iptables)
- [ ] SECRET_KEY is unique and random
- [ ] Strong admin password set
- [ ] TLS_FLAVOR set to `letsencrypt`
- [ ] DISABLE_STATISTICS=True (privacy)
- [ ] Regular backups scheduled
- [ ] Fail2ban installed (optional but recommended)

### Firewall Setup (UFW)
```bash
ufw allow 22/tcp    # SSH
ufw allow 25/tcp    # SMTP
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 587/tcp   # Submission
ufw allow 993/tcp   # IMAPS
ufw enable
```

---

## 🔗 Integration with PortID

### Future Enhancement
This mail server is designed to integrate with PortID authentication:

1. **Identity Management**: Use PortID as primary identity
2. **Login**: Authenticate via PortID instead of passwords
3. **Email Address**: Link `portid` → `email@privra.com`
4. **API Integration**: Mailu API + PortID verification

Implementation guide coming soon!

---

## 🐛 Troubleshooting

### Can't access admin panel
```bash
# Check if services are running
docker compose ps

# Check admin logs
docker compose logs admin

# Ensure port 443 is open
netstat -tulpn | grep 443
```

### Emails not sending
```bash
# Check SMTP logs
docker compose logs smtp

# Verify DNS records
dig privra.com MX
dig mail.privra.com

# Check mail queue
docker compose exec admin flask mailu queue
```

### Let's Encrypt certificate failed
```bash
# Check front logs
docker compose logs front

# Ensure DNS is pointing to server
# Ensure ports 80 and 443 are accessible
# Wait a few minutes and restart
docker compose restart front
```

### "Connection refused" errors
```bash
# Make sure all services are healthy
docker compose ps

# Restart everything
docker compose down
docker compose up -d
```

---

## 📈 Monitoring

### Check Service Health
```bash
# Quick status
docker compose ps

# Detailed stats
docker stats

# Check disk usage
du -sh data/ mail/ mailqueue/
```

### Performance Metrics
```bash
# Mail queue size
docker compose exec admin flask mailu queue

# Spam statistics
# Login to Rspamd web UI: https://mail.privra.com/admin/antispam
```

---

## 🌐 Testing Your Mail Server

### 1. Send Test Email
Login to webmail and send an email to your personal Gmail/Yahoo account.

### 2. Mail Tester
Send an email to `test@mail-tester.com` and visit https://www.mail-tester.com to check your score.

### 3. MXToolbox
Check your domain at https://mxtoolbox.com/domain/privra.com

---

## 📚 Resources

- **Mailu Documentation**: https://mailu.io/2.0/
- **Docker Compose**: https://docs.docker.com/compose/
- **Email Best Practices**: https://www.rfc-editor.org/rfc/rfc5321.html
- **DKIM/SPF/DMARC**: https://mxtoolbox.com/dmarc.aspx

---

## 🤝 Contributing

This is part of the **Privra** privacy-focused ecosystem built by **Harboria Labs**.

- **Founder**: ticketguy (Harboria Labs)
- **Related Projects**: [PortID](https://github.com/HarboriaLabs/portid)

---

## 📄 License

This configuration is open-source and customizable. Mailu itself is licensed under MIT.

---

## 🎯 Roadmap

- [x] Basic mail server setup
- [x] Web interface (admin + webmail)
- [x] Encryption at rest
- [ ] PortID authentication integration
- [ ] Custom Privra webmail theme
- [ ] NFT-based identity verification
- [ ] AI-powered spam filtering
- [ ] Privacy vault integration
- [ ] Mobile app support

---

**Built with privacy, owned by you. 🔐**

*Questions? Issues? Open an issue on GitHub.*
