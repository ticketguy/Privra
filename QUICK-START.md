# Quick Fix Guide for Privra Mail Server

## Current Issue
The nginx front container is failing with: `invalid number of arguments in "location" directive`

## Three Fix Options (Try in Order)

### Option 1: Nginx Override Fix (RECOMMENDED)
This creates a custom start script that removes the broken nginx configuration lines.

```bash
cd ~/Privra  # or wherever your mail server is
git pull
./nginx-override-fix.sh
```

**Wait 15 seconds**, then check status with:
```bash
docker compose ps front
```

---

### Option 2: Alternative .env Fix
If Option 1 doesn't work, this completely removes WEBMAIL/WEBDAV variables and disables the webmail service.

```bash
./alternative-fix.sh
```

---

### Option 3: Manual Fix
If both automated scripts fail:

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
