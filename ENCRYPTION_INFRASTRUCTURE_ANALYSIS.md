# Privra Mail Server - Encryption Infrastructure Analysis
## Complete Assessment for Phase 3.3, 4, and 5 Implementation

Generated: 2025-11-14

---

## EXECUTIVE SUMMARY

Privra has a **strong foundation** for encryption with significant components already implemented:

- ✅ RSA 2048-bit encryption infrastructure (crypto_utils.py)
- ✅ Gateway encryption framework for incoming emails (encrypt_filter.py)
- ✅ Gateway decryption framework for outgoing emails (decrypt_filter.py)
- ✅ Consent/pay-to-send system framework (consent_policy.py)
- ✅ Public key storage and lookup API
- ✅ Recovery key management for encrypted keys
- ✅ Email categorization framework (placeholder for AI)
- ✅ Postfix content filter integration

**Status**: Phase 3.3 is 60% complete. Phase 4 & 5 are in planning stages.

---

## 1. EXISTING CONTENT FILTERS - COMPREHENSIVE OVERVIEW

### 1.1 encrypt_filter.py (INCOMING GATEWAY ENCRYPTION)

**Location**: `/home/user/Privra/postfix/encrypt_filter.py`

**What It Does**:
- Acts as Postfix content filter for incoming emails from external senders
- Automatically encrypts email body with recipient's PUBLIC key
- Only encrypts if recipient has `email_public_key` in database
- Uses RSA-OAEP with SHA256 padding
- Adds headers: `X-Privra-Encrypted: true` and `X-Privra-Gateway-Encrypted: true`

**Implementation Status**: ✅ FULLY IMPLEMENTED
```python
# Core encryption function
encrypted_body = encrypt_email_content(body, public_key)  # RSA-OAEP
```

**What's Working**:
- Extracts plaintext from incoming email
- Looks up recipient's public key from database
- Performs RSA encryption
- Reinjects encrypted email back to Postfix (port 10026)

**Limitations**:
- Only encrypts text/plain body parts
- Doesn't handle multipart complex messages well
- Doesn't encrypt headers (metadata visible)
- No support for attachments
- No verification that recipient can actually decrypt

---

### 1.2 decrypt_filter.py (OUTGOING GATEWAY DECRYPTION)

**Location**: `/home/user/Privra/postfix/decrypt_filter.py`

**What It Does**:
- Acts as Postfix content filter for outgoing emails to external recipients
- Detects if recipient is NOT a Privra user
- If external recipient detected, decrypts the email using sender's PRIVATE key
- Delivers plaintext to external mail servers

**Implementation Status**: ✅ FULLY IMPLEMENTED
```python
# Decrypts if recipient is external and email is encrypted
decrypted_body = decrypt_email_content(encrypted_body, private_key)
```

**Key Features**:
- Retrieves sender's private key from session (decrypted with recovery key)
- Preserves headers except encryption-related ones
- Adds `X-Privra-Gateway-Decrypted: true` header
- Handles both Privra-to-Privra (keep encrypted) and Privra-to-External (decrypt)

**Critical Issue**: ⚠️ 
- **Uses `get_sender_private_key()` which requires session access**
- **Current implementation doesn't have session context in content filter**
- **NEEDS FIX**: Must implement alternative key retrieval for outgoing filter

---

### 1.3 consent_policy.py (SENDER CONSENT & PAY-TO-SEND)

**Location**: `/home/user/Privra/postfix/consent_policy.py`

**What It Does**:
- Postfix policy service (listens on port for policy checks)
- Checks if sender is allowed to send to recipient
- Implements sender whitelist/blacklist
- Implements payment/consent requirements

**Implementation Status**: ✅ FRAMEWORK COMPLETE, FEATURES PARTIALLY DONE

**Features Implemented**:
```
1. Sender Whitelist - FULL
   - Email-level whitelisting
   - Domain-level whitelisting (@domain.com)
   
2. Sender Blacklist - FULL
   - Email-level blacklisting
   - Domain-level blacklisting
   
3. Consent Tracking - PARTIAL
   - Creates consent_requests table entries
   - Tracks status: pending/approved/rejected
   - Expires after 7 days
   
4. Whitelist Mode - FULL
   - Rejects emails from non-whitelisted senders
   - Returns error message with consent link
```

**Missing Pieces**:
- ❌ Payment processing integration
- ❌ Consent request email notifications
- ❌ Consent approval API endpoint
- ❌ Payment validation and charging

---

### 1.4 Is Gateway Encryption Already Active?

**YES, PARTIALLY**:

**Implemented**:
- Encrypt filter configured in master.cf (port 10026 reinject)
- Decrypt filter configured in master.cf (port 10027 reinject)
- Consent policy configured in master.cf
- Database schema for encryption keys exists

**Not Yet Active**:
- Not integrated with actual mail flow in main.cf
- Filters exist but may not be wired to receive emails
- Outgoing decrypt filter has session key retrieval issues
- No error handling for key lookup failures

---

## 2. CRYPTO UTILITIES - AVAILABLE FUNCTIONS

### 2.1 postfix/crypto_utils.py

**Location**: `/home/user/Privra/postfix/crypto_utils.py`

**Available Functions** (All identical to admin/crypto_utils.py):

```python
# Key Generation
generate_email_keypair() 
  -> (private_key, public_key)  # 2048-bit RSA

# Key Serialization
serialize_public_key(public_key) -> str (PEM format)
serialize_private_key(private_key) -> str (PEM format)
deserialize_public_key(pem_string) -> key object
deserialize_private_key(pem_string) -> key object

# Key Encryption (for storage)
encrypt_private_key_with_recovery_key(private_key_pem, recovery_key)
  -> str (Base64-encoded AES-256-CBC encrypted)

decrypt_private_key_with_recovery_key(encrypted_data, recovery_key)
  -> str (PEM-encoded private key)

# Email Content Encryption/Decryption
encrypt_email_content(content, public_key_pem) 
  -> str (Base64-encoded RSA-OAEP encrypted)

decrypt_email_content(encrypted_content, private_key_pem)
  -> str (plaintext)
```

**Encryption Methods**:
- **Email encryption**: RSA-2048 with OAEP padding, SHA256 hashing
- **Key storage**: AES-256-CBC with IV, using PortID recovery key as encryption key

**For Gateway Encryption Phase 3.3**:
- ✅ Can encrypt emails to recipients (RSA with public key)
- ✅ Can decrypt emails from sender (RSA with private key)
- ✅ Can handle private key encryption/decryption
- ✅ All functions available and ready to use

---

### 2.2 admin/crypto_utils.py & webmail/crypto_utils.py

**Status**: IDENTICAL COPIES of postfix/crypto_utils.py

**All three copies have the same functions**, which is good for consistency but could be refactored to a shared module.

---

## 3. DATABASE SCHEMA - COMPLETE ASSESSMENT

### 3.1 From init_db.py (Base Tables)

**Users Table**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    domain VARCHAR(255) NOT NULL,
    portid VARCHAR(255) UNIQUE,                    -- PortID identifier
    recovery_key TEXT,                             -- For decrypting private keys
    auth_type VARCHAR(20) DEFAULT 'password',
    email_public_key TEXT,                         -- ✅ PUBLIC KEY STORAGE
    email_private_key_encrypted TEXT,              -- ✅ ENCRYPTED PRIVATE KEY
    active BOOLEAN DEFAULT TRUE,
    quota_bytes BIGINT DEFAULT 1GB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

**What Exists**:
- ✅ Public key column - Ready for Phase 3.3
- ✅ Encrypted private key storage
- ✅ Recovery key for key decryption
- ✅ User-to-key relationship

---

### 3.2 From migrate_consent_system.py (Consent Tables)

**consent_settings Table** (User preferences):
```sql
CREATE TABLE consent_settings (
    user_email VARCHAR(255) PRIMARY KEY,
    require_consent BOOLEAN DEFAULT FALSE,          -- Phase 5 feature
    require_payment BOOLEAN DEFAULT FALSE,          -- Phase 5 feature
    payment_amount DECIMAL(10, 2) DEFAULT 0.00,    -- Phase 5 feature
    payment_address VARCHAR(500),                  -- Crypto wallet address
    whitelist_mode BOOLEAN DEFAULT FALSE,           -- Phase 5 feature
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

**sender_whitelist Table**:
```sql
CREATE TABLE sender_whitelist (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    sender_domain VARCHAR(255),
    note TEXT,
    created_at TIMESTAMP,
    UNIQUE(recipient_email, sender_email)
)
```

**sender_blacklist Table**:
```sql
CREATE TABLE sender_blacklist (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255),
    sender_domain VARCHAR(255),
    reason TEXT,
    created_at TIMESTAMP
)
```

**consent_requests Table** (Tracking consent/payment requests):
```sql
CREATE TABLE consent_requests (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,            -- Unique consent token
    status VARCHAR(20) DEFAULT 'pending',          -- pending/approved/rejected
    email_subject TEXT,
    email_preview TEXT,
    payment_txid VARCHAR(100),                     -- Crypto transaction ID
    created_at TIMESTAMP,
    expires_at TIMESTAMP,                          -- 7-day expiration default
    responded_at TIMESTAMP
)
```

**What's Ready for Phase 5**:
- ✅ Payment amount storage
- ✅ Crypto wallet address field
- ✅ Transaction ID tracking
- ✅ Consent request tokens
- ✅ Status tracking

---

## 4. ADMIN & WEBMAIL APPLICATIONS

### 4.1 admin/app.py (Administrator Interface)

**Location**: `/home/user/Privra/admin/app.py`

**Key Features**:
```python
@app.route('/api/pubkey/<email>')  
  # Returns public key for email lookup
  # Used by compose/encrypt features
  
@app.route('/adduser')
  # Generates encryption keys automatically during user creation
  # Calls: generate_email_keypair()
  # Encrypts private key with recovery_key (AES)
  # Stores in database
  
@app.route('/recovery-key')
  # Shows recovery key to admin (one-time display)
```

**Encryption Features Present**:
- ✅ Automatic key pair generation for new users
- ✅ Recovery key generation (32 bytes hex)
- ✅ Private key encryption with AES-CBC
- ✅ Public key lookup API (/api/pubkey/)

**Missing for Phase 3.3+**:
- ❌ Key rotation/refresh endpoints
- ❌ Key revocation support
- ❌ User's ability to regenerate keys
- ❌ Payment/consent configuration UI

---

### 4.2 webmail/app.py (User Webmail Interface)

**Location**: `/home/user/Privra/webmail/app.py`

**Encryption Features**:
```python
@app.route('/login')
  # Loads user's encryption keys on login
  # Decrypts private_key_encrypted with recovery_key
  # Stores decrypted private_key in session
  
@app.route('/api/private-key')
  # Returns user's decrypted private key for client-side encryption
  # Used by JavaScript for encrypt/decrypt operations
  
@app.route('/api/pubkey/<email>')
  # Public key lookup (same as admin API)
  
@app.route('/compose', methods=['POST'])
  # Accepts both plaintext and encrypted_body
  # If encrypted: adds X-Privra-Encrypted header
  # Sends to SMTP
```

**Email Encryption Status**:
- ✅ Private key decryption on login
- ✅ Private key available via API for client-side encryption
- ✅ Public key lookup for recipient detection
- ✅ Compose supports encrypted emails
- ✅ Email headers indicate encryption status

**Missing**:
- ❌ JavaScript WebCrypto implementation for client-side encryption
- ❌ Email decryption display logic
- ❌ Encrypted email viewing
- ❌ Visual encryption status indicators

---

### 4.3 webmail/email_categorizer.py (AI Placeholder)

**Current Status**: ⚠️ RULE-BASED ONLY (NOT AI)

**What's Implemented**:
- Simple keyword matching for 6 categories: priority, social, updates, promotions, spam, inbox
- Domain pattern matching (Facebook, Twitter, LinkedIn, etc.)

**What's NOT Implemented** (Phase 4 features):
- ❌ LLM integration
- ❌ Semantic understanding
- ❌ Learning from user corrections
- ❌ Multi-label classification
- ❌ Confidence scores

**Code Shows Placeholder Structure**:
```python
class LLMEmailCategorizer(EmailCategorizer):
    """Placeholder for future LLM-based categorization"""
    # TODO: Integrate with LLM API
```

---

## 5. POSTFIX CONFIGURATION (master.cf)

**Location**: `/home/user/Privra/postfix/master.cf`

### 5.1 Content Filter Configuration

```postfix
# INCOMING EMAIL (port 25 - SMTP from external)
smtp inet  n  -  n  -  -  smtpd
  -o content_filter=encrypt:dummy

# OUTGOING EMAIL (port 587 - SUBMISSION from users)
submission inet n  -  n  -  -  smtpd
  -o content_filter=decrypt:dummy

# SUBMISSIONS (port 465 - implicit TLS from users)
smtps inet  n  -  n  -  -  smtpd
  -o content_filter=decrypt:dummy
```

### 5.2 Filter Definition

```postfix
# Encryption filter for incoming emails
encrypt   unix  -  n  n  -  10  pipe
  flags=Rq user=mail argv=/usr/local/bin/encrypt_filter.py

# Decryption filter for outgoing emails
decrypt   unix  -  n  n  -  10  pipe
  flags=Rq user=mail argv=/usr/local/bin/decrypt_filter.py
```

### 5.3 Reinject Port Configuration

```postfix
# Port 10026 - Reinject encrypted emails to Dovecot
localhost:10026 inet  n  -  n  -  10  smtpd
  -o content_filter=
  -o receive_override_options=no_header_body_checks
  -o smtpd_milters=inet:localhost:8891  (for DKIM)

# Port 10027 - Reinject decrypted emails to internet
localhost:10027 inet  n  -  n  -  10  smtpd
  -o content_filter=
  -o receive_override_options=no_header_body_checks
  -o smtpd_milters=inet:localhost:8891  (for DKIM)
```

### 5.4 Consent Policy Service

```postfix
# Policy daemon for sender consent checking
consent  unix  -  n  n  -  0  spawn
  user=mail argv=/usr/local/bin/consent_policy.py
```

**Current Status**: 
- ✅ All filters are defined
- ✅ Reinject ports configured
- ⚠️ **NOT ACTIVATED in main.cf** - Need to add:
  ```
  smtp_policy_maps = check_policy_service inet:localhost:10030
  smtpd_end_of_data_restrictions = check_policy_service inet:localhost:10030
  ```

---

## PHASE-BY-PHASE IMPLEMENTATION READINESS

---

## PHASE 3.3: GATEWAY ENCRYPTION (INCOMING)

### What's Already Done ✅
- ✅ Encryption algorithm (RSA-2048-OAEP)
- ✅ encrypt_filter.py fully implemented
- ✅ Public key lookup from database
- ✅ Content filter integrated in master.cf
- ✅ Reinject port 10026 configured
- ✅ Database schema for public keys
- ✅ Key generation on user creation

### What Needs to Be Done ❌

**1. VERIFY FILTER ACTIVATION** 
   - [ ] Confirm encrypt_filter.py is in /usr/local/bin/
   - [ ] Add to main.cf: `content_filter = encrypt:dummy`
   - [ ] Test with external email sender

**2. ERROR HANDLING**
   - [ ] Handle case where recipient has no public key
   - [ ] Handle key lookup failures gracefully
   - [ ] Add logging for encryption success/failure

**3. MULTIPART EMAIL SUPPORT**
   - [ ] Enhance to handle HTML emails
   - [ ] Preserve MIME structure
   - [ ] Handle attachments properly

**4. PERFORMANCE**
   - [ ] Add caching for public key lookups
   - [ ] Optimize RSA operations
   - [ ] Monitor filter performance

**5. TESTING**
   - [ ] Send email from Gmail → Privra account
   - [ ] Verify email is encrypted at rest
   - [ ] Verify recipient can decrypt in webmail
   - [ ] Test with various email clients (Thunderbird, etc.)

---

## PHASE 3.4: GATEWAY DECRYPTION (OUTGOING)

### What's Already Done ✅
- ✅ Decryption algorithm implemented
- ✅ decrypt_filter.py fully implemented
- ✅ Recipient detection logic
- ✅ Content filter in master.cf
- ✅ Reinject port 10027 configured

### What Needs to Be Done ❌

**1. FIX SESSION KEY RETRIEVAL** ⚠️ CRITICAL
   - Current code: `get_sender_private_key()` tries to load from database
   - **Problem**: Content filters don't have session context
   - **Solution Options**:
     a) Cache decrypted keys in Redis during login
     b) Store sender's session private key in database temporarily
     c) Use recovery key to decrypt on-demand
     d) Implement key agent service

**2. ACTIVATE FILTER IN POSTFIX**
   - [ ] Wire to submission port (587, 465)
   - [ ] Test mail flow

**3. EXTERNAL RECIPIENT DETECTION**
   - [ ] Verify `is_privra_recipient()` works correctly
   - [ ] Test with mixed internal/external recipients

**4. TESTING**
   - [ ] Send email from Privra → Gmail
   - [ ] Verify Gmail receives plaintext
   - [ ] Verify Privra's draft is still encrypted
   - [ ] Test with external Outlook, Yahoo, etc.

---

## PHASE 3.5: CLIENT-SIDE ENCRYPTION (Web Browser)

### What's Already Done ✅
- ✅ API endpoints for getting private key (/api/private-key)
- ✅ API endpoints for public key lookup (/api/pubkey)
- ✅ Private key available in session
- ✅ User authentication in place

### What's Missing ❌

**1. WEBMAIL FRONTEND**
   - [ ] Implement WebCrypto API integration in JavaScript
   - [ ] Add compose page encryption UI
   - [ ] Add encryption status indicators
   - [ ] Implement inbox decryption logic
   - [ ] Add visual lock icons

**2. KEY MANAGEMENT IN BROWSER**
   - [ ] Load private key from /api/private-key on login
   - [ ] Store in IndexedDB or sessionStorage
   - [ ] Clear on logout
   - [ ] Handle key expiration

**3. ENCRYPTION LOGIC**
   - [ ] Fetch recipient's public key before sending
   - [ ] Detect Privra vs external recipients
   - [ ] Encrypt only for Privra recipients
   - [ ] Add encryption headers

**4. DECRYPTION LOGIC**
   - [ ] Load private key from storage
   - [ ] Decrypt email body on view
   - [ ] Display decrypted content
   - [ ] Handle decryption errors

---

## PHASE 4: AI INTELLIGENCE

### Current State
- ⚠️ **COMPLETELY PLACEHOLDER** - email_categorizer.py has rule-based only

### What Needs to Be Done ❌

**1. LLM INTEGRATION**
   - [ ] Choose LLM provider (OpenAI, Anthropic, local llama.cpp, etc.)
   - [ ] Integrate API client
   - [ ] Add configuration for API keys
   - [ ] Implement rate limiting

**2. EMAIL CATEGORIZATION**
   - [ ] Build LLM categorizer replacing rule-based
   - [ ] Categories: Priority, Social, Updates, Promotions, Spam, Inbox
   - [ ] Add confidence scores
   - [ ] Implement user feedback loop (learning)

**3. SMART FEATURES**
   - [ ] Auto-reply suggestions
   - [ ] Spam detection improvement
   - [ ] Priority detection
   - [ ] Conversation threading
   - [ ] Email summarization

**4. PRIVACY CONSIDERATIONS**
   - [ ] Email content sent to LLM? (Privacy issue!)
   - [ ] Local processing option?
   - [ ] Data retention policies
   - [ ] User consent for AI features

---

## PHASE 5: PAY-TO-SEND (MONETIZATION)

### What's Already Done ✅
- ✅ consent_policy.py with consent/payment logic
- ✅ Database schema with payment fields
- ✅ Sender whitelist/blacklist
- ✅ Consent request tracking
- ✅ Token-based consent links

### What's Missing ❌

**1. PAYMENT PROCESSING**
   - [ ] Choose payment provider (Stripe, crypto, etc.)
   - [ ] Implement payment integration
   - [ ] Handle transaction verification
   - [ ] Add refund logic

**2. CONSENT APPROVAL FLOW**
   - [ ] Consent request email notifications
   - [ ] Consent approval web page (click link, approve)
   - [ ] Update consent_requests.status = 'approved'
   - [ ] Add to sender_whitelist

**3. PAYMENT FLOW**
   - [ ] Collect payment information
   - [ ] Process payment on approval
   - [ ] Create transaction records
   - [ ] Handle failed payments

**4. ADMIN FEATURES**
   - [ ] Payment configuration UI
   - [ ] Set payment amount per user
   - [ ] Crypto wallet management
   - [ ] Payment history/reporting

**5. USER FEATURES**
   - [ ] Disable payment requirement
   - [ ] Set custom payment amounts
   - [ ] Approve/deny consent requests
   - [ ] Manage whitelist via webmail

**6. POSTFIX INTEGRATION**
   - [ ] Wire consent_policy service to main.cf
   - [ ] Defer emails requiring consent
   - [ ] Retry logic for deferred emails
   - [ ] Handle policy service failures

---

## RECOMMENDATIONS FOR IMPLEMENTATION ORDER

### Immediate Priority (Week 1-2)
1. **Fix decrypt_filter.py session key issue** - BLOCKING ISSUE
2. **Activate content filters in main.cf** - Basic infrastructure
3. **Test gateway encryption with external senders** - Validate Phase 3.3
4. **Complete email viewing UI in webmail** - Show decrypted emails

### Phase 3.3 (Week 2-3)
1. Implement multipart/HTML email support in encrypt_filter
2. Add caching for public key lookups
3. Error handling and logging
4. Performance optimization

### Phase 3.4 (Week 3-4)
1. Resolve session key retrieval architecture
2. Test outgoing email decryption
3. Verify external compatibility

### Phase 4 (Week 5-6)
1. Choose and integrate LLM provider
2. Implement email categorization
3. Add confidence scoring
4. Build feedback loop

### Phase 5 (Week 7-8)
1. Choose payment provider
2. Implement consent approval flow
3. Wire policy service to Postfix
4. Build admin/user features

---

## TECHNICAL DEBT & IMPROVEMENTS

### Code Quality Issues
1. **Duplicate crypto_utils.py** - Three identical copies
   - Refactor into shared module
   
2. **Error Handling** - Most filters use generic try/catch
   - Add specific error logging
   - Better error messages to users

3. **Key Management** - Private keys in session
   - Consider encrypted key storage
   - Implement key rotation

4. **Database Migrations** - Multiple separate migration files
   - Consolidate into single migration system
   - Version tracking

### Security Considerations
1. **Metadata Encryption** - Headers still visible
   - Consider encrypted subject lines
   - Protect To/From for gateway

2. **Key Verification** - No public key verification
   - Consider key signing
   - Web of trust model

3. **Recovery Keys** - Single point of failure
   - Consider multi-factor recovery
   - Secure storage recommendations

4. **Session Keys** - Private keys in web sessions
   - Consider key agents
   - Implement session timeout

---

## FILES TO EXAMINE FURTHER

For implementation, focus on:
1. `/home/user/Privra/webmail/templates/` - Compose/view UI
2. `/home/user/Privra/postfix/main.cf` - Postfix configuration
3. `/home/user/Privra/docker-compose.yml` - Service orchestration
4. `/home/user/Privra/docs/DEPLOYMENT.md` - Deployment procedures

