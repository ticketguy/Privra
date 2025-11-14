# Testing PortID Integration

## Step 1: Pull Latest Changes and Rebuild

```bash
# Pull the latest changes
git pull origin claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM

# Rebuild containers with new dependencies
docker-compose down
docker-compose build --no-cache admin webmail
docker-compose up -d

# Check logs
docker-compose logs -f admin webmail
```

## Step 2: Run Database Migration

```bash
# Run the migration script to add PortID columns
docker-compose exec admin python migrate_portid.py

# Verify the migration
docker-compose exec db psql -U privramail -d privramail -c "\d users"
```

You should see the new columns: `portid`, `recovery_key`, `auth_type`

## Step 3: Check the Login Pages

1. **Admin Panel**: https://yourdomain.com/admin
   - You should see a "Use PortID Authentication" checkbox below the password field

2. **Webmail**: https://yourdomain.com:8443
   - You should see the same PortID checkbox

## Step 4: Configure PortID (Required for Testing)

The PortID authentication won't work yet because you need a PortID instance running. To set this up:

```bash
# Add to your .env file
PORTID_APP_ID=privra-mail-v1
PORTID_API_URL=http://your-portid-instance:5001
```

Then restart services:
```bash
docker-compose restart admin webmail
```

## Current Limitations

- **PortID Instance Required**: You need to deploy a PortID instance from https://github.com/Harboria-Labs/PortID
- **Hybrid Authentication**: Currently uses PortID for web auth, but still uses traditional IMAP passwords for mail server
- **No Client-Side Encryption Yet**: Email content is not encrypted with PortID keys (that's Phase 3)

## What Works Now

- Login pages show PortID option when enabled
- Database schema supports PortID identities
- Hybrid authentication (PortID + password fallback)
- Session tracking of auth type
