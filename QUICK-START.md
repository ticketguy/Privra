# Quick Fix Guide for Privra Mail Server

## Current Issue
The nginx front container is failing due to a bug in Mailu 2024.06's Jinja2 template that generates broken nginx config.

## 🎯 ONE-COMMAND CLEANUP & FIX

First, clean up your repository:

```bash
cd ~/privra-mail
git pull
./cleanup-and-fix.sh
```

This script will:
- ✅ Stop all containers
- ✅ Reset repository to clean state (discards local changes)
- ✅ Pull latest code
- ✅ Verify docker-compose.yml has entrypoint override
- ✅ Create nginx override to fix the config
- ✅ Start all containers
- ✅ Show status

**Wait 20 seconds** for it to complete.

---

## 🔄 Alternative: Replace with Custom Nginx (RECOMMENDED IF ABOVE FAILS)

If the override approach still doesn't work, replace the broken Mailu nginx entirely:

```bash
cd ~/privra-mail
git pull
# Edit docker-compose.yml and replace the front service with:
```

```yaml
  front:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
      - "25:25"
      - "465:465"
      - "587:587"
      - "110:110"
      - "995:995"
      - "143:143"
      - "993:993"
    volumes:
      - "./certs:/certs:ro"
      - "./custom-nginx.conf:/etc/nginx/nginx.conf:ro"
    networks:
      - mailnet
    depends_on:
      - admin
      - imap
      - smtp
```

Then:
```bash
docker compose down
docker compose up -d
```

This uses a clean, custom nginx configuration that bypasses the Mailu template bug entirely.

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
