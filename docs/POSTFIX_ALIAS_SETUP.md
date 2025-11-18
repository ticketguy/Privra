# Postfix Configuration for Dynamic Shield Aliasing

This guide explains how to configure Postfix to route email aliases to user mailboxes.

## Overview

Email aliases like `netflix.user@privra.xyz` need to be resolved to the actual user's mailbox (`user@privra.xyz`) by Postfix during mail delivery.

## Configuration Steps

### 1. Create PostgreSQL Query Configuration

Create `/etc/postfix/pgsql-virtual-alias-maps.cf`:

```conf
# PostgreSQL connection settings
hosts = localhost
user = postfix_query
password = YOUR_POSTFIX_QUERY_PASSWORD
dbname = privra

# Query to resolve aliases
query = SELECT user_email FROM email_aliases
        WHERE alias='%s' AND is_active=TRUE
        LIMIT 1
```

### 2. Create Restricted PostgreSQL User

```sql
-- Create read-only user for Postfix queries
CREATE USER postfix_query WITH PASSWORD 'secure_password_here';

-- Grant SELECT permission on email_aliases table only
GRANT SELECT ON email_aliases TO postfix_query;

-- Revoke all other permissions
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM postfix_query;
GRANT SELECT ON email_aliases TO postfix_query;
```

### 3. Update Postfix main.cf

Add to `/etc/postfix/main.cf`:

```conf
# Virtual alias mapping via PostgreSQL
virtual_alias_maps = pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# Ensure privra.xyz is in virtual_alias_domains
virtual_alias_domains = privra.xyz
```

### 4. Set Correct Permissions

```bash
# Postfix config should be readable by postfix user only
sudo chown root:postfix /etc/postfix/pgsql-virtual-alias-maps.cf
sudo chmod 640 /etc/postfix/pgsql-virtual-alias-maps.cf
```

### 5. Test the Configuration

```bash
# Test PostgreSQL query manually
postmap -q "netflix.user@privra.xyz" pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# Expected output: user@privra.xyz

# Test with a burned alias (should return nothing)
postmap -q "burned-alias@privra.xyz" pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# Expected output: (nothing - alias is burned)
```

### 6. Reload Postfix

```bash
sudo postfix reload
```

## How It Works

### Email Delivery Flow

```
1. Email arrives: sender@example.com → netflix.user@privra.xyz
                                           ↓
2. Postfix queries PostgreSQL:
   SELECT user_email FROM email_aliases
   WHERE alias='netflix.user@privra.xyz' AND is_active=TRUE
                                           ↓
3. Database returns: user@privra.xyz
                                           ↓
4. Postfix rewrites recipient: netflix.user@privra.xyz → user@privra.xyz
                                           ↓
5. Email delivered to user's mailbox
                                           ↓
6. alias_service.update_alias_stats() increments email_count
```

### Burned Alias Behavior

```
1. Email arrives: sender@example.com → burned-alias@privra.xyz
                                           ↓
2. Postfix queries PostgreSQL:
   SELECT user_email FROM email_aliases
   WHERE alias='burned-alias@privra.xyz' AND is_active=TRUE
                                           ↓
3. Database returns: NULL (is_active=FALSE due to burn)
                                           ↓
4. Postfix rejects email: 550 5.1.1 User unknown in virtual alias table
                                           ↓
5. Sender receives bounce: "User unknown"
```

## Security Considerations

1. **Read-Only User:** The `postfix_query` user has SELECT-only permissions
2. **Password Protection:** Store password in `/etc/postfix/pgsql-virtual-alias-maps.cf` with 640 permissions
3. **SQL Injection Protection:** Postfix properly escapes the `%s` parameter
4. **No Direct User Table Access:** Postfix cannot query the users table

## Monitoring

### Check Postfix Logs

```bash
# Watch alias resolution in real-time
sudo tail -f /var/log/mail.log | grep "virtual alias"

# Example log entries:
# postfix/cleanup[1234]: rewrite: netflix.user@privra.xyz -> user@privra.xyz
```

### Check Alias Statistics

```sql
-- Most used aliases
SELECT alias, service_name, email_count, last_used
FROM email_aliases
WHERE user_email = 'user@privra.xyz'
ORDER BY email_count DESC
LIMIT 10;

-- Recently burned aliases
SELECT alias, service_name, burned_at
FROM email_aliases
WHERE user_email = 'user@privra.xyz'
  AND burned_at IS NOT NULL
ORDER BY burned_at DESC;
```

## Troubleshooting

### Alias not resolving

```bash
# Test PostgreSQL connection from command line
psql -h localhost -U postfix_query -d privra -c \
  "SELECT user_email FROM email_aliases WHERE alias='netflix.user@privra.xyz' AND is_active=TRUE;"

# Check Postfix logs for errors
sudo grep "pgsql" /var/log/mail.log
```

### Permission denied errors

```bash
# Verify file permissions
ls -la /etc/postfix/pgsql-virtual-alias-maps.cf

# Should show: -rw-r----- 1 root postfix

# Verify PostgreSQL permissions
sudo -u postfix psql -h localhost -U postfix_query -d privra -c "\dp email_aliases"
```

### Performance Issues

If you have millions of aliases, add an index:

```sql
-- Already created by init_db.py, but verify:
CREATE INDEX IF NOT EXISTS idx_aliases_lookup
ON email_aliases(alias) WHERE is_active = TRUE;

-- Check index usage
EXPLAIN ANALYZE
SELECT user_email FROM email_aliases
WHERE alias='netflix.user@privra.xyz' AND is_active=TRUE;

-- Should show "Index Scan using idx_aliases_lookup"
```

## Docker Compose Integration

If running Postfix in Docker, mount the config file:

```yaml
services:
  postfix:
    image: boky/postfix
    volumes:
      - ./postfix/pgsql-virtual-alias-maps.cf:/etc/postfix/pgsql-virtual-alias-maps.cf:ro
    environment:
      - POSTGRES_HOST=privra-dockyard
      - POSTGRES_DB=privra
      - POSTGRES_USER=postfix_query
      - POSTGRES_PASSWORD=${POSTFIX_QUERY_PASSWORD}
```

## Testing End-to-End

### 1. Generate an alias via UI

```
Navigate to: http://localhost:5001/aliases
Click: "Generate New Alias"
Service: "Test Service"
Result: test-service.user@privra.xyz
```

### 2. Send test email

```bash
echo "Test email body" | mail -s "Test" test-service.user@privra.xyz
```

### 3. Verify delivery

```sql
-- Check alias stats were updated
SELECT alias, email_count, last_used
FROM email_aliases
WHERE alias = 'test-service.user@privra.xyz';

-- email_count should be 1
-- last_used should be current timestamp
```

### 4. Burn the alias

```
Click: "Burn" button in UI
Confirm: Yes
```

### 5. Test burned alias

```bash
echo "This should bounce" | mail -s "Test2" test-service.user@privra.xyz

# Expected: 550 User Unknown error
```

---

**Configuration Complete!**

Users can now generate unlimited aliases that automatically route to their mailbox.
