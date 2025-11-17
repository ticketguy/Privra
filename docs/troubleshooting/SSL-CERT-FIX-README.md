# SSL Certificate Fix for admin.privra.xyz

## Problem
The current SSL certificate only covers `mail.privra.xyz` but not `admin.privra.xyz`, causing browsers to show "Not Secure" warnings when accessing the admin panel.

**Certificate Details:**
- Common Name: mail.privra.xyz
- Issued: November 12, 2025
- Expires: February 10, 2026
- Issuer: Let's Encrypt (R12)

## Why Restarting nginx Doesn't Fix It
The certificate file itself (`/etc/letsencrypt/live/mail.privra.xyz/fullchain.pem`) only contains mail.privra.xyz in its Subject Alternative Names (SAN). Restarting nginx just reloads the same certificate - it doesn't change what domains are covered.

## Solution
You need to use certbot to **expand** the existing certificate to include both domains.

### Option 1: Run the Automated Script (Recommended)

```bash
cd ~/privra-mail
./fix-ssl-cert.sh
```

This script will:
1. Stop nginx container
2. Run certbot with `--expand` flag to add admin.privra.xyz
3. Copy new certificates to ~/privra-mail/certs/
4. Restart nginx
5. Verify both domains are working

### Option 2: Manual Steps

If you prefer to run commands manually:

```bash
# 1. Stop nginx so certbot can use port 80/443
cd ~/privra-mail
docker compose stop nginx

# 2. Expand the certificate
sudo certbot certonly --standalone --expand \
  -d mail.privra.xyz \
  -d admin.privra.xyz \
  --non-interactive --agree-tos \
  -m admin@privra.xyz

# 3. Copy new certificates
sudo cp /etc/letsencrypt/live/mail.privra.xyz/fullchain.pem ~/privra-mail/certs/
sudo cp /etc/letsencrypt/live/mail.privra.xyz/privkey.pem ~/privra-mail/certs/
sudo chown privra:privra ~/privra-mail/certs/*.pem

# 4. Start nginx with new certificates
docker compose up -d nginx
```

## Verification

After running the fix, verify both domains show secure:

```bash
# Should show HTTP/2 200 without SSL errors
curl -I https://mail.privra.xyz/
curl -I https://admin.privra.xyz/warofbest/

# View certificate SAN (should list both domains)
openssl s_client -connect admin.privra.xyz:443 -servername admin.privra.xyz < /dev/null 2>/dev/null | openssl x509 -text -noout | grep -A 2 'Subject Alternative Name'
```

Expected output should show:
```
X509v3 Subject Alternative Name:
    DNS:admin.privra.xyz, DNS:mail.privra.xyz
```

## Browser Testing
After the fix:
- https://mail.privra.xyz/ should show secure (already working)
- https://admin.privra.xyz/warofbest/ should show secure (will be fixed)

Both should show a valid certificate issued by Let's Encrypt covering both domains.
