# Quick Fix Guide for Privra Mail Server

## Current Issue
The nginx front container is failing with: `invalid number of arguments in "location" directive`

## 🎯 ONE-COMMAND FIX (RECOMMENDED)

This comprehensive fix handles everything automatically:

```bash
cd ~/privra-mail  # or ~/Privra depending on your folder name
git pull
./final-comprehensive-fix.sh
```

This script will:
- ✅ Validate and fix docker-compose.yml if needed
- ✅ Create the nginx override script
- ✅ Add entrypoint override to docker-compose.yml
- ✅ Restart all containers
- ✅ Show you the status

**Wait 20 seconds** for it to complete.

---

## Alternative Options (If Needed)

### Option 2: Manual Fix
If the comprehensive script doesn't work:

1. Stop all containers:
   ```bash
   docker compose down
   ```

2. Edit `.env` and completely remove these lines:
   ```
   WEBMAIL=...
   WEBDAV=...
   ```

3. Start containers:
   ```bash
   docker compose up -d
   ```

---

## Verify Everything Works

Run the verification script:
```bash
./verify-fix.sh
```

## Expected Result

All 8 containers should show "Up" status:
- ✅ redis
- ✅ front (nginx)
- ✅ resolver
- ✅ admin
- ✅ imap
- ✅ smtp
- ✅ antispam
- ✅ webmail (if enabled)

## Access Your Mail Server

Once front container is running:
- **Admin Interface**: https://mail.privra.xyz/admin
- **Domain**: privra.xyz

## Next Steps After Fix

1. Create your first admin user at the admin interface
2. Add domain: privra.xyz
3. Create mailboxes
4. Configure DNS records (SPF, DKIM, DMARC)

## Need Help?

Check logs:
```bash
docker compose logs front
docker compose logs --tail=50 front
```

Restart specific container:
```bash
docker compose restart front
```
