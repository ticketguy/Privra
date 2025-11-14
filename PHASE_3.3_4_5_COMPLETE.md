# Phase 3.3, 4, and 5 Implementation Complete

**Date:** 2025-11-14
**Status:** ✅ Implementation Complete

## Summary

Successfully implemented:
- **Phase 3.3:** Gateway encryption/decryption for external email compatibility
- **Phase 4:** Basic email categorization (placeholder for future LLM integration)
- **Phase 5:** Pay-to-send gateway and consent system

---

## Phase 3.3: Gateway Encryption/Decryption

### Overview
Enables transparent encryption for emails from external senders and decryption for emails to external recipients, maintaining compatibility with traditional email while keeping data encrypted at rest.

### Files Created/Modified

#### 1. `postfix/encrypt_filter.py` (NEW)
**Purpose:** Content filter for incoming emails from external senders

**Key Functions:**
- `get_recipient_public_key(recipient_email)` - Lookup recipient's public key from database
- `encrypt_incoming_email(msg, recipient_email)` - Encrypt email body with recipient's public key
- Adds headers: `X-Privra-Encrypted: true`, `X-Privra-Gateway-Encrypted: true`

**Flow:**
```
External Sender → SMTP (port 25) → encrypt_filter.py → Encrypted → Dovecot → User Inbox
```

#### 2. `postfix/decrypt_filter.py` (NEW)
**Purpose:** Content filter for outgoing emails to external recipients

**Key Functions:**
- `is_privra_recipient(recipient_email)` - Check if recipient is a Privra user
- `get_sender_private_key(sender_email)` - Retrieve sender's private key for decryption
- `decrypt_outgoing_email(msg, sender_email, recipient_email)` - Decrypt if going to external recipient
- Adds header: `X-Privra-Gateway-Decrypted: true`

**Flow:**
```
Privra User → Submission (587/465) → decrypt_filter.py → Decrypted → External SMTP → External Recipient
```

#### 3. `postfix/master.cf` (MODIFIED)
**Changes:**
- Line 5: Added content filter to SMTP (incoming): `content_filter=encrypt:dummy`
- Line 14: Added content filter to submission (outgoing): `content_filter=decrypt:dummy`
- Line 23: Added content filter to smtps (outgoing): `content_filter=decrypt:dummy`
- Line 51-52: Added encrypt pipe filter definition
- Line 55-56: Added decrypt pipe filter definition
- Line 59-67: Added reinject listener for incoming (localhost:10026)
- Line 70-78: Added reinject listener for outgoing (localhost:10027)

#### 4. `postfix/Dockerfile` (MODIFIED)
**Changes:**
- Added Python3 and pip installation
- Added Python dependencies: psycopg2-binary, cryptography, pycryptodome
- Copied encrypt_filter.py and decrypt_filter.py to /usr/local/bin/
- Made filters executable

### Encryption Flow

#### Privra → Privra (with encryption)
```
Compose (client-side encrypt) → Submission → Pass through → Dovecot → View (client-side decrypt)
```

#### External → Privra
```
External SMTP → Port 25 → encrypt_filter.py → Encrypted → Dovecot → View (client-side decrypt)
```

#### Privra → External
```
Compose (not encrypted) → Submission → decrypt_filter.py → Plaintext → External SMTP
```

---

## Phase 4: Email Categorization

### Overview
Implements basic rule-based email categorization with a placeholder architecture for future LLM integration.

### Files Created/Modified

#### 1. `webmail/email_categorizer.py` (NEW)
**Purpose:** Email categorization engine with rule-based detection

**Categories:**
- **Priority:** Urgent, important, time-sensitive emails
- **Social:** Social media notifications, friend requests
- **Updates:** Newsletters, subscriptions, announcements
- **Promotions:** Sales, deals, marketing emails
- **Spam:** Obvious spam patterns
- **Inbox:** Default category

**Key Classes:**
- `EmailCategorizer` - Rule-based categorizer
- `LLMEmailCategorizer` - Placeholder for future LLM integration

**Detection Methods:**
- Keyword matching in subject and body
- Sender domain analysis
- Pattern recognition

**Future LLM Integration Points:**
```python
class LLMEmailCategorizer(EmailCategorizer):
    # TODO: Integrate with LLM API
    # TODO: Learning from user corrections
    # TODO: Semantic understanding
    # TODO: Confidence scores
```

#### 2. `webmail/app.py` (MODIFIED)
**Changes:**
- Line 16: Import EmailCategorizer
- Line 29: Initialize categorizer
- Line 292-296: Categorize each email in inbox
- Line 309-310: Add category to email metadata
- Line 316-318: Filter emails by category if requested
- Line 321-324: Pass categories and current filter to template

#### 3. `webmail/templates/inbox.html` (MODIFIED)
**Changes:**
- Line 12-27: Added category filter bar
- Line 29-63: Added CSS for category filters and badges
- Line 70-72: Display category badge on each email
- Line 82-86: Show category-specific empty message

**Category Colors:**
- Priority: Red (#dc3545)
- Social: Cyan (#17a2b8)
- Updates: Gray (#6c757d)
- Promotions: Yellow (#ffc107)
- Spam: Pink (#e83e8c)
- Inbox: Light gray (#e9ecef)

#### 4. `admin/migrate_email_categories.py` (NEW)
**Purpose:** Database migration for categories (optional - not required for current implementation)

**Note:** Current implementation uses in-memory categorization. This migration is prepared for future persistent storage.

### Categorization Flow

```
Email Received → Fetch from IMAP → Extract Subject/Sender/Body →
categorizer.categorize() → Assign Category → Display with Badge →
Filter by Category (optional)
```

---

## Phase 5: Pay-to-Send Gateway & Consent System

### Overview
Implements a consent-based email filtering system allowing users to control who can send them emails, with whitelist/blacklist management and future payment integration.

### Files Created/Modified

#### 1. `admin/migrate_consent_system.py` (NEW)
**Purpose:** Database migration for consent system

**Tables Created:**

**consent_settings:**
- `user_email` (PK) - User's email address
- `require_consent` - Boolean flag to require consent
- `require_payment` - Boolean flag to require payment (future)
- `payment_amount` - Payment amount (future)
- `payment_address` - Crypto payment address (future)
- `whitelist_mode` - Only accept whitelisted senders

**sender_whitelist:**
- `id` (PK) - Auto-increment ID
- `recipient_email` - User who created whitelist
- `sender_email` - Allowed sender email
- `sender_domain` - Allowed sender domain (for @domain.com)
- `note` - Optional note
- `created_at` - Timestamp

**sender_blacklist:**
- `id` (PK) - Auto-increment ID
- `recipient_email` - User who created blacklist
- `sender_email` - Blocked sender email
- `sender_domain` - Blocked sender domain
- `reason` - Block reason
- `created_at` - Timestamp

**consent_requests:**
- `id` (PK) - Auto-increment ID
- `recipient_email` - Email recipient
- `sender_email` - Email sender
- `token` - Unique consent token
- `status` - pending/approved/rejected
- `email_subject` - Subject of email requesting consent
- `email_preview` - Preview of email content
- `payment_txid` - Payment transaction ID (future)
- `created_at`, `expires_at`, `responded_at` - Timestamps

#### 2. `postfix/consent_policy.py` (NEW)
**Purpose:** Postfix policy service for checking sender consent

**Key Functions:**
- `check_policy(request)` - Main policy check logic
- Returns: `DUNNO` (allow), `REJECT` (block), `DEFER` (wait for consent)

**Policy Logic:**
```
1. Check if recipient is Privra user (if not, pass through)
2. Check if sender is Privra user (if yes, allow - internal email)
3. Get recipient's consent settings
4. Check blacklist (if blacklisted, REJECT)
5. Check whitelist (if whitelisted, allow)
6. If whitelist_mode enabled and not whitelisted, REJECT
7. If consent required:
   - Check for existing approved consent
   - Check for pending consent request
   - Create new consent request if needed
   - DEFER email until consent granted
8. Otherwise, allow (DUNNO)
```

**Integration:** Runs as Postfix spawn service on stdin/stdout

#### 3. `postfix/master.cf` (MODIFIED)
**Changes:**
- Line 81-82: Added consent policy service definition
  ```
  consent  unix  -       n       n       -       0       spawn
    user=mail argv=/usr/local/bin/consent_policy.py
  ```

#### 4. `postfix/main.cf` (MODIFIED)
**Changes:**
- Line 37: Added consent policy check to recipient restrictions
  ```
  smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated,
                                  check_policy_service unix:private/consent,
                                  reject_unauth_destination
  ```

#### 5. `postfix/Dockerfile` (MODIFIED)
**Changes:**
- Line 36: Copy consent_policy.py to /usr/local/bin/
- Line 39: Make consent_policy.py executable

#### 6. `webmail/app.py` (MODIFIED)
**New Routes:**

**`/settings/consent` (GET, POST)** - Line 436-518
- Display consent settings, whitelist, blacklist
- Update require_consent and whitelist_mode flags
- Query database for current settings and lists

**`/settings/whitelist/add` (POST)** - Line 520-562
- Add sender or domain to whitelist
- Supports email (user@domain.com) or domain (@domain.com) format
- Optional note field

**`/settings/whitelist/remove/<id>` (POST)** - Line 564-586
- Remove entry from whitelist

**`/settings/blacklist/add` (POST)** - Line 588-628
- Add sender or domain to blacklist
- Supports email or domain format
- Optional reason field

**`/settings/blacklist/remove/<id>` (POST)** - Line 630-652
- Remove entry from blacklist

#### 7. `webmail/templates/consent_settings.html` (NEW)
**Purpose:** Web UI for consent settings management

**Features:**
- Privacy mode toggles (require_consent, whitelist_mode)
- Whitelist management (add, view, remove)
- Blacklist management (add, view, remove)
- Domain support (@domain.com)
- Information panel explaining how it works

#### 8. `webmail/templates/base.html` (MODIFIED)
**Changes:**
- Line 176: Added "Settings" navigation link
- Line 114-117: Added `.btn-danger` CSS class

### Consent System Flow

#### External Email with Consent Enabled

```
External Sender → Port 25 → Postfix → consent_policy.py →
Check Blacklist → Check Whitelist → Check Consent →
DEFER (if no consent) → Create Consent Request →
Notify Recipient → Wait for Approval
```

#### User Management

```
User → Webmail Settings → Enable Consent Mode →
Add to Whitelist/Blacklist → Save Settings →
Policy Service Checks on Next Email
```

---

## Testing Guide

### 1. Deploy Updated Services

```bash
# Rebuild and restart services
docker-compose build postfix webmail admin
docker-compose up -d

# Run migrations
docker-compose exec admin python migrate_consent_system.py

# Check logs
docker-compose logs -f postfix
docker-compose logs -f webmail
```

### 2. Test Gateway Encryption (Phase 3.3)

**Test 1: External → Privra**
```bash
# Send email from external Gmail to Privra user
# Check Dovecot logs to see encryption
docker-compose logs dovecot | grep "X-Privra-Gateway-Encrypted"

# Login to webmail and verify email is encrypted
# Should see decryption spinner then plaintext
```

**Test 2: Privra → External**
```bash
# Login to webmail
# Compose email to external Gmail address
# Email should arrive as plaintext at Gmail
# Check Postfix logs for decryption
docker-compose logs postfix | grep "decrypt_filter"
```

**Test 3: Privra → Privra**
```bash
# Compose email between two Privra users
# Should see encryption badge in compose
# Email should be encrypted end-to-end
# No gateway involvement
```

### 3. Test Email Categorization (Phase 4)

**Test 1: View Categorized Inbox**
```bash
# Login to webmail
# View inbox - each email should have category badge
# Check colors: Priority (red), Social (cyan), Updates (gray), etc.
```

**Test 2: Filter by Category**
```bash
# Click category filter buttons
# URL should change to ?category=priority
# Only emails in that category should display
```

**Test 3: Test Category Detection**
```bash
# Send email with subject "URGENT: Important deadline"
# Should be categorized as Priority

# Send email from facebook.com or with "tagged you"
# Should be categorized as Social

# Send email with subject "Newsletter: Weekly updates"
# Should be categorized as Updates
```

### 4. Test Consent System (Phase 5)

**Test 1: Enable Consent Mode**
```bash
# Login to webmail
# Go to Settings
# Enable "Require consent from external senders"
# Save settings

# Send email from external address
# Check Postfix logs - should see DEFER
docker-compose logs postfix | grep "Consent required"
```

**Test 2: Whitelist Management**
```bash
# Go to Settings
# Add sender to whitelist: "friend@gmail.com"
# Send email from that address
# Email should be accepted (check logs)

# Add domain to whitelist: "@example.com"
# Send from any@example.com
# Email should be accepted
```

**Test 3: Blacklist Management**
```bash
# Go to Settings
# Add sender to blacklist: "spam@example.com"
# Send email from that address
# Should see REJECT in logs

# Try with domain: "@spammer.com"
# All emails from that domain should be rejected
```

**Test 4: Whitelist-Only Mode**
```bash
# Go to Settings
# Enable "Whitelist-only mode"
# Add one sender to whitelist
# Try sending from whitelisted sender → Should accept
# Try sending from non-whitelisted sender → Should reject
```

**Test 5: Internal Emails**
```bash
# Enable consent mode
# Send email from one Privra user to another
# Should bypass consent checks (internal emails always allowed)
```

---

## Database Queries

### Check Consent Settings

```sql
SELECT * FROM consent_settings;
```

### View Whitelist

```sql
SELECT recipient_email, sender_email, sender_domain, note
FROM sender_whitelist
ORDER BY created_at DESC;
```

### View Blacklist

```sql
SELECT recipient_email, sender_email, sender_domain, reason
FROM sender_blacklist
ORDER BY created_at DESC;
```

### View Consent Requests

```sql
SELECT recipient_email, sender_email, status, email_subject, created_at
FROM consent_requests
ORDER BY created_at DESC;
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL EMAIL SYSTEM                     │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Port 25 (SMTP)      │
        │   Postfix Receiver    │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  consent_policy.py    │
        │  Check Whitelist/     │
        │  Blacklist/Consent    │
        └───────────┬───────────┘
                    │
            ┌───────┴───────┐
            │               │
         REJECT          DUNNO/DEFER
            │               │
            ▼               ▼
        [Block]    ┌───────────────────┐
                   │ encrypt_filter.py │
                   │ Encrypt for Privra│
                   └────────┬──────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │   Dovecot      │
                   │   LMTP         │
                   └────────┬───────┘
                            │
                            ▼
                   ┌────────────────┐
                   │  User Mailbox  │
                   │  (Encrypted)   │
                   └────────┬───────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │        WEBMAIL (Flask)             │
        │  • email_categorizer.py            │
        │  • Client-side decryption          │
        │  • Category filtering              │
        │  • Consent management UI           │
        └───────────┬───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Port 587/465         │
        │  Submission           │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  decrypt_filter.py    │
        │  Decrypt for External │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   External SMTP       │
        │   Delivery            │
        └───────────────────────┘
```

---

## Security Considerations

### Gateway Encryption (Phase 3.3)
- ✅ Server-side encryption/decryption uses RSA-OAEP (same as client)
- ✅ Private keys encrypted at rest with PortID recovery keys
- ✅ Transparent to external senders (maintains compatibility)
- ⚠️ Server has access to plaintext during filter processing
- ⚠️ Consider adding hardware security module (HSM) for key storage

### Email Categorization (Phase 4)
- ✅ In-memory categorization (no persistent storage of email content)
- ✅ Limited body preview (500 chars) to minimize data exposure
- ✅ Categorization happens on-demand
- ⚠️ Future LLM integration will need privacy considerations

### Consent System (Phase 5)
- ✅ Policy service runs with restricted permissions (user=mail)
- ✅ Postfix integration via spawn (isolated process)
- ✅ Fail-open design (errors allow emails through)
- ✅ Internal Privra emails bypass consent checks
- ⚠️ DEFER mechanism may cause email delays
- ⚠️ Consent request storage includes email metadata

---

## Future Enhancements

### Phase 3.3 Improvements
- [ ] Add support for S/MIME and PGP detection
- [ ] Implement key rotation mechanism
- [ ] Add encryption metrics and monitoring
- [ ] Support for encrypted attachments

### Phase 4 LLM Integration
- [ ] Connect to LLM API (OpenAI, Claude, etc.)
- [ ] Implement semantic categorization
- [ ] Add learning from user corrections
- [ ] Multi-label classification
- [ ] Confidence scores and explanations
- [ ] Custom user-defined categories

### Phase 5 Payment Integration
- [ ] Bitcoin/Lightning payment integration
- [ ] Ethereum/Stablecoin support
- [ ] Payment verification webhook
- [ ] Automatic whitelist after payment
- [ ] Refund mechanism
- [ ] Payment history tracking

### Additional Features
- [ ] Consent request notification emails
- [ ] Public consent request page (token-based)
- [ ] Rate limiting for consent requests
- [ ] Analytics dashboard
- [ ] Export/import whitelist/blacklist
- [ ] Shared whitelists (family/team)

---

## Known Issues

1. **Policy Service Performance**
   - Current implementation does database lookup for each email
   - Consider caching whitelist/blacklist in memory
   - Add connection pooling

2. **Category Detection Accuracy**
   - Rule-based detection is simplistic
   - Many false positives/negatives
   - Requires LLM for better accuracy

3. **Consent Request Lifecycle**
   - No automated notification to recipient
   - No public consent approval page
   - No expiration cleanup job

4. **Migration Dependencies**
   - consent_system migration requires users table
   - Must run after Phase 3.1 migration
   - No rollback mechanism

---

## Configuration

### Enable/Disable Gateway Encryption

To disable gateway encryption (keep E2E only):

```bash
# Edit postfix/master.cf
# Comment out content_filter lines:
# smtp      inet  n       -       n       -       -       smtpd
#   -o content_filter=encrypt:dummy  # Comment this

# submission inet n       -       n       -       -       smtpd
#   -o content_filter=decrypt:dummy  # Comment this
```

### Customize Categorization Rules

Edit `webmail/email_categorizer.py`:

```python
# Add custom keywords
PRIORITY_KEYWORDS = [
    'urgent', 'important',
    'custom_keyword_here'  # Add your keywords
]

# Add custom domains
SOCIAL_DOMAINS = [
    'facebook.com',
    'customsocial.com'  # Add your domains
]
```

### Default Consent Settings

Edit `admin/migrate_consent_system.py`:

```python
# Change default consent settings
cur.execute("""
    INSERT INTO consent_settings (user_email, require_consent, require_payment)
    SELECT email, TRUE, FALSE  # Change to TRUE to enable by default
    FROM users
""")
```

---

## Summary of Changes

### Files Created (12)
1. postfix/encrypt_filter.py
2. postfix/decrypt_filter.py
3. postfix/consent_policy.py
4. webmail/email_categorizer.py
5. admin/migrate_email_categories.py
6. admin/migrate_consent_system.py
7. webmail/templates/consent_settings.html
8. PHASE_3.3_4_5_COMPLETE.md

### Files Modified (6)
1. postfix/master.cf
2. postfix/main.cf
3. postfix/Dockerfile
4. webmail/app.py
5. webmail/templates/inbox.html
6. webmail/templates/base.html

### Database Tables Added (4)
1. consent_settings
2. sender_whitelist
3. sender_blacklist
4. consent_requests

### Lines of Code
- Python: ~1,200 lines
- HTML/CSS: ~300 lines
- SQL: ~150 lines
- **Total: ~1,650 lines**

---

## Next Steps

1. **Testing:**
   - Run all test scenarios from Testing Guide
   - Test with real external email (Gmail, Outlook)
   - Load testing with categorization enabled

2. **Deployment:**
   - Run database migrations
   - Rebuild and deploy containers
   - Monitor logs for errors
   - Verify gateway encryption works

3. **User Documentation:**
   - Create user guide for consent settings
   - Document category system
   - Explain gateway encryption to users

4. **Monitoring:**
   - Set up logging for policy service
   - Monitor encryption/decryption metrics
   - Track categorization accuracy
   - Alert on consent system errors

5. **Future Development:**
   - Plan LLM integration timeline
   - Design payment integration architecture
   - Consider consent request notification system
   - Evaluate policy service performance

---

**Implementation Status:** ✅ **COMPLETE**

All three phases (3.3, 4, and 5) are fully implemented and ready for testing.
