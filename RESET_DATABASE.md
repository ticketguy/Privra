# Reset Database Instructions

## Current Issue
Database was created with wrong credentials. Need to recreate with:
- Database name: `privra-dockyard`
- Database user: `privra`

## Steps to Reset

### 1. Stop all containers
```bash
docker compose down
```

### 2. Remove the database volume (this deletes all data)
```bash
docker volume rm privra_db-data
```

If the above fails with "volume is in use", force remove:
```bash
docker compose down -v
```

### 3. Verify volume is removed
```bash
docker volume ls | grep db-data
```

Should return nothing.

### 4. Start containers (database will be recreated)
```bash
docker compose up -d
```

This will create a fresh PostgreSQL database with:
- Database name: `privra-dockyard` (from your .env)
- User: `privra` (from your .env)
- Password: (from your .env)

### 5. Initialize database tables
Wait for database to be ready (about 10 seconds), then:
```bash
docker compose exec admin python init_db.py
```

This creates all 29 tables including:
- `user_profiles`
- `email_folders`
- `consent_settings`
- `payment_transactions`
- etc.

### 6. Verify tables created
```bash
docker compose exec db psql -U privra -d privra-dockyard -c "\dt"
```

You should see all 29 tables listed.

### 7. Test the application
Visit your webmail interface - everything should work now:
- Profile page should load
- Email folders should work
- Pay-to-send settings should save

## Important Notes

⚠️ **This will delete ALL existing data** including:
- All user accounts
- All emails
- All settings
- All reputation data

Only do this if you're okay losing the current data, or if you're still in development/testing phase.

## Alternative: Keep Data & Fix Credentials

If you need to keep existing data, you would need to:
1. Connect to the existing database
2. Rename it from the old name to `privra-dockyard`
3. Create/update the user to `privra`

But since you're having so many issues, a fresh start is recommended.
