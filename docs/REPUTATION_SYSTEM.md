# Reputation & Automated Penalty System

A privacy-preserving abuse prevention system that maintains platform hygiene without reading email content.

## Overview

The Reputation System uses a **Trust Score** (0-100) to automatically detect and penalize abusive behavior based on metadata, user reports, and sending patterns - never email content.

### Core Concept

- **Baseline**: Every user starts at score 100
- **Floor**: Score of 0 results in account freeze
- **Healing**: Scores slowly recover with good behavior (+5 points/day)
- **Privacy**: No email content is ever read - only metadata

## Trust Score Tiers

### Tier 1: Normal (Score 80-100)
**Status**: Full access, no restrictions

- Unlimited sending
- All features enabled
- No penalties

### Tier 2: Warning (Score 50-79)
**Status**: Warning issued, full access

- User receives automated warning email
- All features still enabled
- Notification of unusual activity
- Alert that continued violations will result in restrictions

### Tier 3: Throttle (Score 20-49)
**Status**: Rate limited

**Restrictions**:
- **10 emails per hour** limit
- 5-minute sending delay (greylisting)
- All other features enabled

**Goal**: Slow down potential spam without blocking legitimate use

### Tier 4: Walled Garden (Score 1-19)
**Status**: Internal-only mode

**Restrictions**:
- Can **receive** all emails normally
- Can **only send** to other Privra users
- **Cannot send** to external addresses (Gmail, Outlook, etc.)
- 5 emails per hour limit

**Goal**: Protect server IP reputation while containing the issue

### Tier 5: Frozen (Score 0)
**Status**: Account locked

**Restrictions**:
- Cannot send any emails
- Cannot access SMTP/IMAP
- Webmail access revoked
- **Admin review required** to unlock

**Goal**: Total containment for severe violations

## Input Signals (How Abuse is Detected)

The system relies on **metadata and external signals**, never email content:

### 1. User Reports (Weighted)
**Impact**: -5 points × reporter's reputation

When a user reports another user as spam:
- Impact is **weighted** by reporter's Trust Score
- Reporter with score 100 = full penalty (-5)
- Reporter with score 50 = half penalty (-2.5)
- Reporter with score 10 = minimal penalty (-0.5)

**Protections**:
- Users can only report the same sender **once per day**
- False reporters lose reputation themselves
- High-reputation users have more impact

**Example**:
```
Good User (score 100) reports Spammer
→ Spammer loses 5 points

Spammer (score 10) reports Good User
→ Good User loses only 0.5 points
```

### 2. Bounce Rate
**Impact**: -10 points when threshold exceeded

Tracks emails sent to non-existent addresses:
- Monitors last 100 emails in 24 hours
- Triggers when **>10% bounce rate**
- Indicates scraping/spamming behavior

### 3. Spam Trap Hits
**Impact**: -100 points (instant freeze)

Honeypot addresses that should never receive mail:
- Never published publicly
- Only bots/scrapers hit them
- Instant account freeze on hit

**Default traps** (auto-created):
- `noreply@yourdomain.com`
- `abuse@yourdomain.com`
- `postmaster@yourdomain.com`

### 4. Sending Velocity Spikes
**Impact**: -15 points

Detects sudden increases in sending volume:
- Baseline: Normal sending pattern
- Spike: 100+ emails over tier limit
- Indicates compromised account or spam campaign

**Example**:
```
Normal User: 5 emails/hour average
Suddenly: 500 emails/hour
→ Penalty applied, rate limit enforced
```

## Weighted Reporting Logic

To prevent abuse of the reporting system, reports are **weighted by reporter reputation**:

### Formula
```
Actual Penalty = Base Penalty × (Reporter Score / 100)
```

### Examples

| Reporter Score | Base Penalty | Actual Penalty | Impact |
|---------------|--------------|----------------|---------|
| 100 (trusted) | -5 | -5.0 | Full |
| 75 (good) | -5 | -3.75 | High |
| 50 (warning) | -5 | -2.5 | Medium |
| 25 (throttled) | -5 | -1.25 | Low |
| 10 (walled) | -5 | -0.5 | Minimal |

### Anti-Abuse Protections

1. **Rate Limiting**: 1 report per target per day
2. **Weighted Impact**: Low-reputation users can't mass-report
3. **False Report Tracking**: Reporters who file false reports lose reputation
4. **Reciprocal Reporting Detection**: Mutual reporting flagged for admin review

## Automated Penalty Enforcement

### How It Works

1. **Real-time Monitoring**: Every email checks reputation
2. **Automatic Tier Assignment**: Score determines tier
3. **Instant Enforcement**: Restrictions apply immediately
4. **User Notification**: Automated emails explain changes

### Integration Points

**Postfix (SMTP)**:
- Policy server checks sender before accepting
- Enforces rate limits
- Blocks external sending for walled tier
- Detects spam trap hits

**Webmail**:
- Shows reputation score on dashboard
- Abuse reporting interface
- Tier status display

**IMAP/Dovecot**:
- Frozen accounts cannot authenticate

## Score Recovery (Healing)

Users can recover from mistakes:

### Healing Rate
- **+5 points per day** of good behavior
- Runs daily via cron at 2 AM
- Only applies if no violations in 24+ hours
- Stops at score 100

### Recovery Timeline

| Current Score | Days to Normal (80+) | Days to Full (100) |
|--------------|---------------------|-------------------|
| 75 (Warning) | 1 day | 5 days |
| 50 (Throttle) | 6 days | 10 days |
| 20 (Walled) | 12 days | 16 days |
| 1 (Near Freeze) | 16 days | 20 days |

**Note**: Score 0 (frozen) requires **manual admin review**

## Technical Implementation

### Database Tables

- `user_reputation`: Current scores and tiers
- `reputation_events`: Full audit log
- `abuse_reports`: User-submitted reports
- `bounce_tracking`: Email bounce history
- `spam_trap_hits`: Honeypot hits
- `velocity_violations`: Rate limit violations

### Services

**reputation_service.py**:
- Core reputation logic
- Score calculation
- Tier assignment
- Healing mechanism

**reputation_policy.py**:
- Postfix policy server
- Real-time enforcement
- SMTP integration

### Redis Rate Limiting

Uses Redis for fast velocity checks:
```
Key: velocity:{email}:hour
TTL: 3600 seconds (1 hour)
Value: Email count
```

## API Endpoints

### Check Own Reputation
```http
GET /reputation/check
```

**Response**:
```json
{
  "email": "user@domain.com",
  "score": 85,
  "tier": "normal",
  "is_frozen": false,
  "rate_limit": null
}
```

### Report Abuse
```http
POST /report/abuse
Content-Type: application/x-www-form-urlencoded

reported_email=spammer@domain.com&reason=spam&details=Unwanted commercial email
```

**Response**:
```json
{
  "success": true,
  "penalty": -5,
  "impact_multiplier": 1.0
}
```

## CLI Management

### Check User Reputation
```bash
docker compose exec postfix python3 /app/reputation_service.py check --user user@domain.com
```

### File Abuse Report
```bash
docker compose exec postfix python3 /app/reputation_service.py report \
  --reporter reporter@domain.com \
  --reported spammer@domain.com \
  --reason "Sending spam"
```

### Run Healing Process
```bash
docker compose exec postfix python3 /app/reputation_service.py heal
```

### View Statistics
```bash
docker compose exec postfix python3 /app/reputation_service.py stats
```

**Output**:
```
Reputation Statistics:
Tier          Users    Avg Score
-----------------------------------
normal        245      92.3
warning       12       64.5
throttle      3        35.0
walled        1        15.0
frozen        0        0.0
```

## Deployment

### 1. Initialize Database
```bash
docker compose exec db psql -U privramail privramail < db/reputation_schema.sql
```

### 2. Configure Postfix Policy Server

Add to `postfix/main.cf`:
```
smtpd_recipient_restrictions =
    ...
    check_policy_service unix:private/reputation-policy
    ...
```

Add to `postfix/master.cf`:
```
reputation-policy unix  -       n       n       -       0       spawn
    user=nobody argv=/usr/bin/python3 /app/reputation_policy.py
```

### 3. Set Up Cron Job
```bash
# Add to crontab
0 2 * * * /path/to/Privra/scripts/reputation-heal-cron.sh
```

### 4. Restart Services
```bash
./deploy.sh restart
```

## Monitoring

### View Recent Events
```sql
SELECT user_email, event_type, score_change, old_score, new_score, reason, created_at
FROM reputation_events
ORDER BY created_at DESC
LIMIT 20;
```

### Check Frozen Accounts
```sql
SELECT user_email, current_score, last_violation_at
FROM user_reputation
WHERE is_frozen = TRUE;
```

### Abuse Report Summary
```sql
SELECT reported_email, COUNT(*) as report_count
FROM abuse_reports
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY reported_email
ORDER BY report_count DESC
LIMIT 10;
```

## Privacy & Security

### What We Track
✅ Bounce rates (metadata)
✅ Sending velocity (counts)
✅ User reports (sender/recipient)
✅ Spam trap hits (recipient addresses)

### What We DON'T Track
❌ Email content/body
❌ Email subjects (except in reports)
❌ Attachment contents
❌ Reading patterns

### Zero-Knowledge Principle

The system knows:
- "User X sent 500 emails in 1 hour" (violation)
- "User X was reported by 5 users" (violation)

The system does NOT know:
- What those emails said
- Why users reported them (beyond category)

## Notifications

Users receive automated emails when tier changes:

**Warning Tier**:
```
Subject: Account Warning - Unusual Activity Detected
Body: Your Trust Score is 75/100. Continued violations may result in restrictions.
```

**Throttle Tier**:
```
Subject: Account Restricted - Rate Limiting Applied
Body: Your Trust Score is 45/100. Sending limited to 10 emails/hour.
```

**Walled Tier**:
```
Subject: Account Severely Restricted - Internal Only
Body: Your Trust Score is 15/100. External email is BLOCKED.
```

**Frozen Tier**:
```
Subject: Account FROZEN - Immediate Action Required
Body: Your Trust Score is 0/100. Contact admin to unlock.
```

## Best Practices

### For Users
1. Don't send spam or unsolicited email
2. Maintain valid recipient lists
3. Report spam you receive
4. Monitor your reputation score

### For Admins
1. Review frozen accounts regularly
2. Monitor abuse reports for patterns
3. Adjust spam traps periodically
4. Check healing cron job runs daily

## Troubleshooting

### User Frozen Unfairly

1. Check reputation events:
   ```sql
   SELECT * FROM reputation_events
   WHERE user_email = 'user@domain.com'
   ORDER BY created_at DESC;
   ```

2. Review reports:
   ```sql
   SELECT * FROM abuse_reports
   WHERE reported_email = 'user@domain.com';
   ```

3. Manual score adjustment:
   ```sql
   UPDATE user_reputation
   SET current_score = 100, tier = 'normal', is_frozen = FALSE
   WHERE user_email = 'user@domain.com';
   ```

### Rate Limiting Not Working

1. Check Redis:
   ```bash
   docker compose exec redis redis-cli
   > KEYS velocity:*
   ```

2. Verify policy server:
   ```bash
   docker compose logs postfix | grep reputation
   ```

### Healing Not Running

1. Check cron job:
   ```bash
   crontab -l | grep reputation
   ```

2. Run manually:
   ```bash
   docker compose exec postfix python3 /app/reputation_service.py heal
   ```

## Future Enhancements

Potential improvements:

- **Machine Learning**: Anomaly detection for sending patterns
- **IP Reputation**: Integrate external IP reputation services
- **Sender Verification**: DKIM/SPF check integration
- **Appeal System**: Allow users to appeal penalties
- **Graduated Recovery**: Faster healing for minor violations
- **Team Accounts**: Shared reputation for organizations

## Summary

The Reputation System provides:

✅ **Automated Protection**: No manual intervention needed
✅ **Privacy-Preserving**: Never reads email content
✅ **Fair & Balanced**: Weighted reporting prevents abuse
✅ **Redemption Path**: Users can recover from mistakes
✅ **Tiered Approach**: Graduated penalties, not binary ban
✅ **Transparent**: Users know their score and why it changed

This creates a **self-regulating ecosystem** that maintains platform quality while respecting user privacy.
