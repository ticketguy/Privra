# Quick Fix Guide for Privra Mail Server

## Solution
Replaced broken Mailu nginx with clean custom nginx:alpine configuration.

## 🎯 ONE-COMMAND FIX

```bash
cd ~/privra-mail
git pull
./cleanup-and-fix.sh
```

This script will:
- ✅ Stop all containers
- ✅ Reset repository to clean state
- ✅ Pull latest code (custom nginx config)
- ✅ Validate configuration
- ✅ Generate self-signed TLS certificates (if needed)
- ✅ Start all containers with custom nginx
- ✅ Show status

**Wait 20 seconds** for it to complete.

### 🔐 About TLS Certificates

The script automatically generates **self-signed certificates** for HTTPS. Your browser will show a security warning - this is normal for self-signed certs.

For production use, you should replace these with **Let's Encrypt** certificates later.

## What Changed

We replaced the buggy Mailu nginx image with a clean `nginx:alpine` image and custom configuration:
- **Before**: `ghcr.io/mailu/nginx:2024.06` with broken Jinja2 template
- **After**: `nginx:alpine` with custom config (no template bugs!)

The custom config handles:
- ✅ HTTPS with automatic HTTP→HTTPS redirect
- ✅ Admin interface at /admin
- ✅ SMTP (ports 25, 587, 465)
- ✅ IMAP (ports 143, 993)
- ✅ POP3 (ports 110, 995)
- ✅ TCP stream proxying to backend mail servers

---

## 🔍 Verify Everything Works

```bash
docker compose ps
```

All containers should show "Up" status.

## 🌐 Access Your Mail Server

Once front container is running:
- **Admin Interface**: https://mail.privra.xyz/admin
- **Domain**: privra.xyz

## 📝 Next Steps

1. Create your first admin user at https://mail.privra.xyz/admin
2. Add domain: privra.xyz
3. Create mailboxes
4. Configure DNS records (SPF, DKIM, DMARC)

## 🐛 Still Having Issues?

Check logs:
```bash
docker compose logs front --tail=50
```

Verify override exists:
```bash
ls -lh overrides/nginx/start
cat overrides/nginx/start
```

Test nginx config:
```bash
docker compose run --rm --entrypoint /bin/sh front -c "nginx -t"
```
