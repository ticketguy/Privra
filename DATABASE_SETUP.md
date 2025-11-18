# Database Setup Guide

## Current Issue
The webmail application was trying to connect to database `privramail` but the actual database is named `privra-dockyard`.

## Fix Applied
Created `.env` file with correct database name:
```
DB_NAME=privra-dockyard
```

## Steps to Complete Setup

### 1. Verify Database Exists
```bash
docker compose exec db psql -U privramail -l
```

You should see `privra-dockyard` in the list of databases.

### 2. Restart Services
Restart all services to pick up the new `.env` configuration:
```bash
docker compose restart
```

Or for a full restart:
```bash
docker compose down
docker compose up -d
```

### 3. Initialize Database Tables
Run the database initialization script to create all 29 required tables:
```bash
docker compose exec admin python init_db.py
```

This will create:
- `user_profiles` (for profile page)
- `email_folders` (for Sent, Spam, Drafts, etc.)
- `consent_settings` (for pay-to-send)
- `payment_transactions` (for payment history)
- `user_wallets` (for wallet management)
- And 24 other essential tables

### 4. Verify Tables Created
```bash
docker compose exec db psql -U privramail -d privra-dockyard -c "\dt"
```

You should see all tables listed.

### 5. Test Profile Page
Navigate to the profile page - it should now load correctly instead of returning a 302 redirect.

## Expected Behavior After Fix

✅ Profile page loads correctly
✅ Email folders (Sent, Spam, Important, Drafts, Trash) work
✅ Pay-to-send settings save properly
✅ Wallet information displays
✅ User profiles auto-create on signup

## Troubleshooting

### If profile still shows 302 redirect:
Check the webmail logs:
```bash
docker compose logs webmail | grep -i profile
```

### If tables don't exist:
Run init_db.py again with verbose output:
```bash
docker compose exec admin python init_db.py
```

### If database connection fails:
Verify `.env` file has correct password:
```bash
cat .env | grep DB_PASSWORD
```

## Notes

- The `.env` file is gitignored for security (contains database passwords)
- All Python services read database config from environment variables
- No hardcoded database names exist in the codebase
- Profile auto-creation was already fixed in `webmail/app.py:494-498`
