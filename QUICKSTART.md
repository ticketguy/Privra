# ⚡ Quick Start Guide

**Get Privra Mail running in 5 minutes**

## Prerequisites Checklist
- [ ] Linux server (Ubuntu 22.04) with 2GB+ RAM
- [ ] Domain name (e.g., privra.com)
- [ ] DNS access
- [ ] Server IP address

---

## Step 1: Configure DNS (Do This First!)

Add these records to your domain DNS:

```
Record Type    Name                  Value                    Priority
-----------    ----                  -----                    --------
A              mail.privra.com       YOUR_SERVER_IP           -
MX             privra.com            mail.privra.com          10
TXT            privra.com            "v=spf1 mx ~all"         -
TXT            _dmarc.privra.com     "v=DMARC1; p=quarantine" -
```

**Wait 5-10 minutes for DNS to propagate**, then verify:
```bash
dig mail.privra.com
```

---

## Step 2: SSH Into Server

```bash
ssh root@YOUR_SERVER_IP
```

---

## Step 3: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Privra.git
cd Privra
git checkout claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM
```

---

## Step 4: Run Setup

```bash
chmod +x setup.sh
sudo ./setup.sh
```

Enter your domain when prompted.

---

## Step 5: Start Services

```bash
docker compose up -d
```

---

## Step 6: Create Admin User

```bash
docker compose exec admin flask mailu admin admin privra.com YourStrongPassword123!
```

---

## Step 7: Access Web Interface

Open your browser:
- **Admin**: https://mail.privra.com/admin
- **Webmail**: https://mail.privra.com/webmail
- **Login**: admin@privra.com

---

## 🎉 Done!

You now have:
- ✅ Full mail server running
- ✅ Web interface accessible
- ✅ Encryption enabled
- ✅ Anti-spam configured

### Next Steps:
1. Create user accounts in the admin panel
2. Send a test email from webmail
3. Configure your email client (Thunderbird, Apple Mail, etc.)

### Useful Commands:
```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Stop everything
docker compose down

# Create new user
docker compose exec admin flask mailu user USERNAME privra.com PASSWORD
```

---

**Need help?** Check the full [README.md](README.md)
