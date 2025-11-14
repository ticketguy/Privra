# Privra Encryption Implementation Checklist

## Quick Status Overview

| Phase | Component | Status | Priority |
|-------|-----------|--------|----------|
| 3.3 | Gateway Encryption (Incoming) | 60% ✅ | HIGH |
| 3.4 | Gateway Decryption (Outgoing) | 60% ⚠️ | HIGH |
| 3.5 | Client-Side Encryption | 40% ⚠️ | MEDIUM |
| 4 | AI Intelligence | 5% ❌ | MEDIUM |
| 5 | Pay-to-Send | 60% ⚠️ | LOW |

---

## Critical Blocking Issues

### 1. decrypt_filter.py - Session Key Retrieval ⚠️ CRITICAL
**File**: `/home/user/Privra/postfix/decrypt_filter.py` (line 84)

**Problem**:
```python
private_key = get_sender_private_key(sender_email)
# This tries to load from database, but content filters don't have session context
```

**Impact**: Outgoing gateway decryption won't work without fixing this

**Solution**: Choose one of:
- A) Cache decrypted keys in Redis during login
- B) Retrieve private key using recovery_key during content filter execution
- C) Implement secure key agent service

---

## Phase 3.3: Gateway Encryption - READY TO ACTIVATE

### What's Already Working ✅
- `encrypt_filter.py` fully implemented
- RSA encryption algorithm ready
- Database schema for public keys
- Postfix master.cf configured with reinject port 10026
- Public key lookup API functional

### Activation Steps
1. [ ] Ensure `/usr/local/bin/encrypt_filter.py` exists in Postfix container
2. [ ] Verify `postfix/main.cf` includes:
   ```
   content_filter = encrypt:dummy
   ```
3. [ ] Restart Postfix: `docker compose restart postfix`
4. [ ] Test by sending email from Gmail to your Privra account
5. [ ] Verify email is encrypted at rest in Dovecot

### Code Files to Review
- **Main filter**: `/home/user/Privra/postfix/encrypt_filter.py`
- **Config**: `/home/user/Privra/postfix/master.cf` (lines 4-5, 51-52, 59-70)
- **Crypto**: `/home/user/Privra/postfix/crypto_utils.py`
- **Database**: Lines 65-66 in `/home/user/Privra/admin/init_db.py`

---

## Phase 3.4: Gateway Decryption - FIX NEEDED THEN TEST

### Critical Fix Required
**File**: `/home/user/Privra/postfix/decrypt_filter.py`

**Current Code** (broken):
```python
# Line 84 - tries to load from database
private_key = get_sender_private_key(sender_email)

# Function tries to fetch from database, but missing recovery key for decryption
def get_sender_private_key(sender_email):
    # Returns encrypted private key from DB
    # But can't decrypt without user's session context
```

**Recommended Fix**: Use recovery key instead of session
```python
def get_sender_private_key(sender_email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT email_private_key_encrypted, recovery_key FROM users
           WHERE email = %s AND active = TRUE""",
        (sender_email,)
    )
    result = cur.fetchone()
    if result and result[0] and result[1]:
        # Now decrypt using recovery key (always available)
        return decrypt_private_key_with_recovery_key(result[0], result[1])
    return None
```

### After Fix
1. [ ] Test by sending encrypted email from Privra to Gmail
2. [ ] Verify Gmail receives plaintext
3. [ ] Verify Privra keeps local copy encrypted

---

## Phase 3.5: Client-Side Encryption - IN PROGRESS

### What Works ✅
- Private key loading on login (`webmail/app.py` line 241)
- Private key API endpoint (`/api/private-key`)
- Public key lookup API (`/api/pubkey/<email>`)
- Compose page accepts encrypted_body parameter

### What's Missing ❌
- **No JavaScript WebCrypto implementation yet**
- No encrypt button on compose page
- No decrypt logic on email viewing
- No visual encryption indicators

### Implementation Tasks
1. [ ] Create `webmail/static/js/crypto.js` with WebCrypto functions
2. [ ] Add encrypt button to compose form
3. [ ] Add decrypt logic to view_email page
4. [ ] Show lock icon for encrypted emails
5. [ ] Add UI indicator for Privra vs external recipients

### Key Files to Create/Modify
- **Create**: `/home/user/Privra/webmail/static/js/crypto.js` (new)
- **Modify**: `/home/user/Privra/webmail/templates/compose.html`
- **Modify**: `/home/user/Privra/webmail/templates/view_email.html`
- **Existing API**: `/home/user/Privra/webmail/app.py` (lines 383-399)

---

## Phase 4: AI Intelligence - PLANNING STAGE

### Current Implementation
- `webmail/email_categorizer.py` - Rule-based only (5% complete)
- Categories: Priority, Social, Updates, Promotions, Spam, Inbox
- Keywords and domain patterns hardcoded

### NOT Implemented ❌
- LLM integration (0%)
- API calls to AI service
- User feedback/learning loop
- Confidence scoring

### Implementation Plan
1. [ ] Choose LLM provider:
   - OpenAI GPT-4
   - Anthropic Claude API
   - Local llama.cpp
   - Other

2. [ ] Integrate API client (e.g., `pip install openai`)

3. [ ] Replace `LLMEmailCategorizer.categorize()` with real LLM call

4. [ ] Add privacy safeguards:
   - [ ] Limit content sent to external API
   - [ ] Add opt-in/opt-out
   - [ ] Local processing option
   - [ ] Data retention policies

5. [ ] Build feedback loop:
   - [ ] User corrections update categorization
   - [ ] Confidence scores improve over time

### Files to Modify
- `/home/user/Privra/webmail/email_categorizer.py` (lines 158-205)
- `/home/user/Privra/webmail/app.py` (instantiates categorizer)

---

## Phase 5: Pay-to-Send - FRAMEWORK DONE, FEATURES MISSING

### What Works ✅
- Database schema (consent_settings, sender_whitelist, sender_blacklist, consent_requests)
- Policy service logic (`postfix/consent_policy.py`)
- Whitelist/blacklist management in webmail
- Consent token generation

### What's Missing ❌

#### 1. Consent Approval Flow
- [ ] Email notification to recipient (TODO on line 159)
- [ ] Consent approval page (click token link → approve)
- [ ] API endpoint to approve consent requests
- [ ] Auto-add sender to whitelist on approval

#### 2. Payment Processing
- [ ] Choose payment provider (Stripe, crypto, etc.)
- [ ] Collect payment method
- [ ] Process payment
- [ ] Store transaction ID in `payment_txid` field

#### 3. Postfix Integration
- [ ] Wire policy service in `main.cf`:
   ```
   smtp_data_restrictions = check_policy_service inet:localhost:10030
   ```
- [ ] Test with external sender (should be deferred if not consented)

#### 4. Admin/User Features
- [ ] Payment configuration UI in admin
- [ ] User can set payment amount
- [ ] User can view payment history
- [ ] Dashboard showing pending consents

### Code to Review/Modify
- **Policy service**: `/home/user/Privra/postfix/consent_policy.py`
  - Missing: Email notifications (line 159)
  - Missing: Payment validation
  
- **Database**: `/home/user/Privra/admin/migrate_consent_system.py`
  - Tables exist and are correct
  
- **Webmail**: `/home/user/Privra/webmail/app.py`
  - Whitelist/blacklist management exists (lines 708-840)
  - Missing: Consent approval page
  - Missing: Payment flow

- **Admin**: `/home/user/Privra/admin/app.py`
  - Missing: Payment configuration UI

---

## Database Schema Ready to Use

### Public Key Storage ✅
```sql
-- Already in users table
email_public_key TEXT
email_private_key_encrypted TEXT
recovery_key TEXT
```

### Encryption Settings ✅
```sql
-- Tables created in migrate_consent_system.py
consent_settings (user_email, require_consent, require_payment, payment_amount, payment_address)
sender_whitelist (recipient_email, sender_email, sender_domain)
sender_blacklist (recipient_email, sender_email, sender_domain)
consent_requests (recipient_email, sender_email, token, status, payment_txid, expires_at)
```

### No Schema Changes Needed
All tables already exist and are properly configured!

---

## Available APIs

### Public Key Lookup
```bash
GET /api/pubkey/<email>

Response:
{
  "email": "user@privra.com",
  "public_key": "-----BEGIN PUBLIC KEY-----...",
  "is_privra": true,
  "encrypted": true
}
```

**Location**: `webmail/app.py:401` & `admin/app.py:107`

### Private Key Retrieval (Authenticated)
```bash
GET /api/private-key

Response:
{
  "private_key": "-----BEGIN PRIVATE KEY-----...",
  "has_encryption": true
}
```

**Location**: `webmail/app.py:383`

---

## Crypto Functions Available

### In `/home/user/Privra/postfix/crypto_utils.py`:

**Key Generation**:
```python
private_key, public_key = generate_email_keypair()
```

**Encryption**:
```python
encrypted = encrypt_email_content(plaintext, recipient_public_key_pem)
```

**Decryption**:
```python
plaintext = decrypt_email_content(encrypted_content, sender_private_key_pem)
```

**Key Management**:
```python
# Encrypt private key for storage
encrypted_key = encrypt_private_key_with_recovery_key(private_key_pem, recovery_key)

# Decrypt private key from storage
private_key_pem = decrypt_private_key_with_recovery_key(encrypted_key, recovery_key)
```

---

## Postfix Configuration Details

### Content Filters Active in master.cf ✅
- **Incoming**: encrypt:dummy (port 10026 reinject)
- **Outgoing**: decrypt:dummy (port 10027 reinject)

### Filters Defined in master.cf ✅
- encrypt (line 51-52)
- decrypt (line 55-56)
- Reinject ports configured (line 59-84)

### Still Needed in main.cf ⚠️
Need to verify/add these lines in `/home/user/Privra/postfix/main.cf`:
```
# Enable encryption on incoming SMTP
smtp content_filter = encrypt:dummy

# Enable decryption on submission (user-to-internet)
submission content_filter = decrypt:dummy
```

---

## Testing Checklist

### Phase 3.3 Testing
- [ ] Create user via admin panel
- [ ] Send email from Gmail to that user
- [ ] Check Dovecot maildir - email should be encrypted
- [ ] Log in as user in webmail
- [ ] Email should display correctly (decrypted on view)

### Phase 3.4 Testing
- [ ] Create test user A (Privra) and test user B (Gmail)
- [ ] User A composes encrypted email to User B
- [ ] Email should be decrypted by gateway
- [ ] User B (Gmail) receives plaintext
- [ ] User A's draft remains encrypted

### Phase 3.5 Testing (When WebCrypto implemented)
- [ ] Compose email to Privra user
- [ ] Should show encryption icon
- [ ] Send encrypted
- [ ] Recipient receives encrypted
- [ ] Both can decrypt in browser

---

## File Locations Quick Reference

| Component | File Path | Status |
|-----------|-----------|--------|
| Incoming Filter | `/home/user/Privra/postfix/encrypt_filter.py` | ✅ Ready |
| Outgoing Filter | `/home/user/Privra/postfix/decrypt_filter.py` | ⚠️ Needs fix |
| Policy Service | `/home/user/Privra/postfix/consent_policy.py` | ⚠️ Needs completion |
| Crypto Utils | `/home/user/Privra/postfix/crypto_utils.py` | ✅ Ready |
| Admin App | `/home/user/Privra/admin/app.py` | ✅ Partial |
| Webmail App | `/home/user/Privra/webmail/app.py` | ✅ Partial |
| Categorizer | `/home/user/Privra/webmail/email_categorizer.py` | ⚠️ Placeholder |
| Postfix Config | `/home/user/Privra/postfix/master.cf` | ✅ Ready |
| Database Setup | `/home/user/Privra/admin/init_db.py` | ✅ Ready |
| Migrations | `/home/user/Privra/admin/migrate_*.py` | ✅ Ready |

---

## Next Steps (Priority Order)

### IMMEDIATE (This Week)
1. Fix `decrypt_filter.py` session key issue (BLOCKING)
2. Activate content filters in Postfix
3. Test Phase 3.3 (incoming encryption)
4. Implement webmail UI for viewing encrypted emails

### SHORT TERM (Next 2 Weeks)
1. Complete Phase 3.4 (outgoing decryption)
2. Build WebCrypto client-side encryption
3. Add visual encryption indicators

### MEDIUM TERM (Next Month)
1. Implement LLM integration for Phase 4
2. Complete pay-to-send payment flow
3. Build consent approval UI

### LONG TERM (Ongoing)
1. Performance optimization
2. Error handling improvements
3. Security audit
4. User documentation

---

## Questions to Ask When Implementing

1. **Outgoing Decryption**: Should private keys be cached in Redis or loaded on-demand from recovery key?
2. **AI Privacy**: Should email content be sent to external LLM API or keep local only?
3. **Payment Provider**: Stripe, cryptocurrency, or custom payment system?
4. **Client Encryption**: Browser-only or also support IMAP clients?
5. **Key Rotation**: Plan for updating encryption keys over time?

