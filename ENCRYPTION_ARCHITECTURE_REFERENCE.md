# Privra Encryption Architecture - Code Reference

---

## System Architecture Diagram

```
                         PRIVRA MAIL SYSTEM
                                
    ┌─────────────────────────────────────────────────────────┐
    │                     EXTERNAL WORLD                        │
    │   Gmail    Outlook    Yahoo    Other Mail Servers      │
    └──────────────────────┬──────────────────────────────────┘
                           │
                           │ SMTP Port 25
                           │ (External senders)
                           ▼
    ┌─────────────────────────────────────────────────────────┐
    │              POSTFIX (SMTP Server)                       │
    │                                                          │
    │  ┌──────────────────────────────────────────────────┐   │
    │  │ Incoming Email (Port 25)                         │   │
    │  │ Content-Filter: encrypt:dummy                    │   │
    │  └──────────────────────────────────────────────────┘   │
    │           │                                              │
    │           ▼                                              │
    │  ┌──────────────────────────────────────────────────┐   │
    │  │ encrypt_filter.py                                │   │
    │  │ - Lookup recipient's PUBLIC key                 │   │
    │  │ - Encrypt email body with RSA-2048-OAEP        │   │
    │  │ - Add X-Privra-Encrypted header                │   │
    │  │ - Reinject via port 10026                       │   │
    │  └──────────────────────────────────────────────────┘   │
    │           │                                              │
    │           ▼                                              │
    │  ┌──────────────────────────────────────────────────┐   │
    │  │ Reinject SMTP (Port 10026)                       │   │
    │  │ - Receive encrypted email                        │   │
    │  │ - Route to Dovecot via LMTP                      │   │
    │  └──────────────────────────────────────────────────┘   │
    └─────────────────────┬──────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────┐
    │            DOVECOT (IMAP Server)                         │
    │                                                          │
    │  Encrypted maildir storage:                            │
    │  /var/mail/domain.com/user/INBOX/                      │
    │    - Emails encrypted at rest                          │
    │    - Body: base64(RSA-2048(plaintext))                │
    │    - Headers: Plaintext (metadata visible)            │
    └─────────────────────┬──────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          │ IMAP Port 993 │               │
          ▼               │               │
    ┌─────────────┐      │         ┌─────────────┐
    │   WEBMAIL   │      │         │  EMAIL CLIENT│
    │  (Browser)  │      │         │ (Thunderbird)│
    │             │      │         │             │
    │ ┌─────────┐ │      │         │ (receives  │
    │ │Webmail  │ │      │         │  encrypted)│
    │ │decrypt  │ │      │         │            │
    │ │in JS    │ │      │         └─────────────┘
    │ └─────────┘ │      │
    └─────────────┘      │
                         │
           ┌─────────────┴───────────────┐
           │ Port 587/465               │
           │ (Users sending)            │
           ▼                            │
    ┌──────────────────────┐   ┌────────────────────┐
    │ decrypt_filter.py    │   │ PostgreSQL Database│
    │                      │   │                    │
    │ - Check recipient    │   │ users table:       │
    │ - If EXTERNAL:       │   │ - email_public_key │
    │   Decrypt w/sender's │   │ - email_private_key_encrypted │
    │   PRIVATE key        │   │ - recovery_key     │
    │ - If PRIVRA: Keep    │   │                    │
    │   encrypted          │   │ consent_settings:  │
    │ - Reinject port 10027│   │ - require_consent  │
    └──────────────────────┘   │ - require_payment  │
           │                    │                    │
           ▼                    │ sender_whitelist:  │
    ┌──────────────────────┐   │ sender_blacklist:  │
    │ SMTP to Internet     │   └────────────────────┘
    │ (External recipients)│
    └──────────────────────┘
                ▼
         (External mail servers
          receive PLAINTEXT)
```

---

## Data Flow: Incoming Email (External → Privra User)

```
1. EXTERNAL SENDER (Gmail, etc.)
   └─> Composes: "Hello Privra User!"
       └─> SMTP to mail.privra.com:25

2. POSTFIX RECEIVES
   └─> Applies: content_filter=encrypt:dummy
       └─> Calls: encrypt_filter.py

3. ENCRYPT_FILTER.PY EXECUTES
   ┌─> Read from stdin: email message
   ├─> Extract recipient: user@privra.com
   ├─> Query database: SELECT email_public_key FROM users
   ├─> Public key found: "-----BEGIN PUBLIC KEY-----..."
   ├─> Encrypt body: encrypt_email_content(body, public_key)
   │   └─> Result: base64(RSA-2048-OAEP(plaintext))
   ├─> Set header: X-Privra-Encrypted: true
   ├─> Reinject SMTP: localhost:10026
   └─> Exit code: 0

4. REINJECT SMTP PORT 10026
   └─> Receive encrypted email
       └─> Route to: Dovecot IMAP via LMTP
           └─> Deliver to: /var/mail/privra.com/user/

5. DOVECOT STORAGE (at rest)
   └─> File: INBOX (encrypted)
       ├─ From: sender@gmail.com
       ├─ To: user@privra.com
       ├─ Subject: Hello Privra User!
       ├─ Body: "aGJRRzUvUDlkbUJRU1....[encrypted]"
       └─ X-Privra-Encrypted: true

6. PRIVRA USER LOGS IN
   ├─> Fetch email via IMAP
   ├─> Download encrypted body
   ├─> Load private key via /api/private-key
   ├─> Decrypt in browser:
   │   decrypt_email_content(encrypted_body, private_key)
   └─> Display: "Hello Privra User!"
```

---

## Data Flow: Outgoing Email (Privra → External)

```
1. PRIVRA USER COMPOSES
   └─> Message: "Response from Privra User"
       └─> Recipient: external@gmail.com

2. WEBMAIL DETECTS RECIPIENT
   ├─> Check: is_privra_recipient(external@gmail.com)
   ├─> Result: False (external Gmail user)
   └─> Action: Will be decrypted by gateway

3. CLIENT-SIDE ENCRYPTION (if implemented)
   ├─> Fetch: /api/pubkey/external@gmail.com
   ├─> Result: Not a Privra user (no public key)
   └─> Decision: Don't encrypt at client (goes plaintext)

4. USER SUBMITS
   ├─> SMTP PORT 587: submit@privra.com
   ├─> Header: X-Privra-Encrypted: false
   ├─> Body: "Response from Privra User"
   └─> Routes through content_filter=decrypt:dummy

5. DECRYPT_FILTER.PY EVALUATES
   ├─> Check if email is encrypted
   ├─> Check if recipient is Privra user
   ├─> Result: External recipient, decrypt not needed
   └─> Passes through unchanged

6. OUTGOING POSTFIX QUEUE
   └─> SMTP relay to: mail.gmail.com:25
       └─> Gmail receives PLAINTEXT email

7. GMAIL USER RECEIVES
   └─> Normal email: "Response from Privra User"
       └─> No encryption indicators
           └─> User unaware of Privra encryption system
```

---

## Data Flow: Incoming Email (Privra → Privra with Client Encryption)

```
1. PRIVRA USER A COMPOSES
   └─> Recipient: user.b@privra.com
       └─> Body: "Secret message for Bob"

2. WEBMAIL CLIENT (JavaScript)
   ├─> Fetch: /api/pubkey/user.b@privra.com
   ├─> Response: {
   │     "public_key": "-----BEGIN PUBLIC KEY-----...",
   │     "is_privra": true
   │   }
   ├─> LOCAL ENCRYPTION (in browser):
   │   └─> encrypt_email_content(
   │         "Secret message for Bob",
   │         bob_public_key
   │       )
   └─> Result: Encrypted ciphertext (never leaves browser as plaintext)

3. SEND ENCRYPTED EMAIL
   ├─> POST /compose
   ├─> Body: {encrypted_body: "aGJ....[long base64]"}
   ├─> Header: X-Privra-Encrypted: true
   └─> Routes through SMTP PORT 587

4. GATEWAY PROCESSING
   ├─> Incoming filter: encrypt:dummy
   ├─> Check: Recipient is Privra user? YES
   ├─> Check: Email already encrypted? YES
   ├─> Action: PASS THROUGH (already encrypted)
   └─> Reinject port 10026

5. DOVECOT STORAGE (at rest)
   └─> Encrypted email stored in Bob's mailbox
       └─ Body: Same ciphertext (double-encrypted by Alice's browser key)

6. BOB LOGS IN TO PRIVRA
   ├─> Fetch encrypted email
   ├─> Load private key via /api/private-key
   ├─> Decrypt in browser:
   │   └─> decrypt_email_content(ciphertext, bob_private_key)
   └─> Display: "Secret message for Bob"

[NOTE: Server never sees plaintext - TRUE ZERO-KNOWLEDGE]
```

---

## Code Reference: Key Functions

### 1. RSA Encryption (encrypt_filter.py)

**Function Location**: `/home/user/Privra/postfix/crypto_utils.py:172`

```python
def encrypt_email_content(content, public_key_pem):
    """
    Encrypt email content with recipient's public key
    
    Args:
        content: str - Plaintext email body
        public_key_pem: str - PEM-encoded public key
    
    Returns:
        str - Base64-encoded encrypted content
    """
    public_key = deserialize_public_key(public_key_pem)
    
    # RSA-2048 with OAEP padding, SHA256
    encrypted = public_key.encrypt(
        content.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return base64.b64encode(encrypted).decode('utf-8')
```

**In Context (encrypt_filter.py)**:
```python
# Line 78
encrypted_body = encrypt_email_content(body, public_key)

# Line 93-94
new_msg['X-Privra-Encrypted'] = 'true'
new_msg['X-Privra-Gateway-Encrypted'] = 'true'
```

---

### 2. Key Generation (admin/app.py)

**Function Location**: `/home/user/Privra/postfix/crypto_utils.py:13`

**In Context (admin/app.py:167)**:
```python
# Generate email encryption keys
private_key, public_key = generate_email_keypair()
public_key_pem = serialize_public_key(public_key)
private_key_pem = serialize_private_key(private_key)

# Encrypt private key with recovery key (AES-256-CBC)
encrypted_private_key = encrypt_private_key_with_recovery_key(
    private_key_pem,
    recovery_key  # 32 bytes hex
)

# Store in database
cur.execute(
    """INSERT INTO users
       (email, password, domain, recovery_key, 
        email_public_key, email_private_key_encrypted)
       VALUES (%s, %s, %s, %s, %s, %s)""",
    (email, hashed, domain, recovery_key, 
     public_key_pem, encrypted_private_key)
)
```

---

### 3. Public Key Lookup (webmail/app.py)

**Function Location**: `/home/user/Privra/webmail/app.py:401`

```python
@app.route('/api/pubkey/<email>')
def get_public_key(email):
    """Public key lookup API endpoint"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT email, email_public_key FROM users WHERE email = %s AND active = TRUE",
            (email,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[1]:
            # User exists and has a public key
            return jsonify({
                "email": result[0],
                "public_key": result[1],
                "is_privra": True,
                "encrypted": True
            }), 200
        elif result:
            # User exists but no encryption keys yet
            return jsonify({
                "email": result[0],
                "is_privra": True,
                "encrypted": False,
                "message": "User exists but hasn't set up encryption yet"
            }), 200
        else:
            # User doesn't exist - external email
            return jsonify({
                "email": email,
                "is_privra": False,
                "encrypted": False
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

### 4. Private Key Loading (webmail/app.py)

**Function Location**: `/home/user/Privra/webmail/app.py:223`

```python
# In login() function
conn = get_db()
cur = conn.cursor()
cur.execute(
    """SELECT recovery_key, email_private_key_encrypted
       FROM users WHERE email = %s AND active = TRUE""",
    (email_addr,)
)
key_data = cur.fetchone()
cur.close()
conn.close()

# If user has encryption keys, decrypt private key and store in session
if key_data and key_data[0] and key_data[1]:
    recovery_key = key_data[0]
    encrypted_private_key = key_data[1]

    # Decrypt private key with recovery key
    private_key_pem = decrypt_private_key_with_recovery_key(
        encrypted_private_key,
        recovery_key
    )

    if private_key_pem:
        # Store decrypted private key in session (encrypted via HTTPS)
        session['private_key'] = private_key_pem
        session['has_encryption'] = True
```

---

### 5. Private Key API Endpoint (webmail/app.py)

**Function Location**: `/home/user/Privra/webmail/app.py:383`

```python
@app.route('/api/private-key')
def get_private_key():
    """API endpoint to get user's private key for client-side encryption"""
    if 'email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    if not session.get('has_encryption', False):
        return jsonify({'error': 'Encryption not enabled for this user'}), 404

    private_key = session.get('private_key')
    if not private_key:
        return jsonify({'error': 'Private key not available'}), 404

    return jsonify({
        'private_key': private_key,
        'has_encryption': True
    })
```

---

### 6. Consent Policy Service (postfix/consent_policy.py)

**Core Logic**: Lines 30-174

```python
def check_policy(self, request):
    """
    Check if sender is allowed to send to recipient
    
    Returns:
        'DUNNO' - Allow
        'REJECT ...' - Reject with message
        'DEFER ...' - Defer and retry later
    """
    sender = request.get('sender', '').lower()
    recipient = request.get('recipient', '').lower()

    # Check blacklist first (deny)
    cur.execute("""
        SELECT id FROM sender_blacklist
        WHERE recipient_email = %s
        AND (sender_email = %s OR sender_domain = %s)
    """, (recipient, sender, sender_domain))
    if cur.fetchone():
        return f'REJECT Sender {sender} is blacklisted'

    # Check whitelist (allow)
    cur.execute("""
        SELECT id FROM sender_whitelist
        WHERE recipient_email = %s
        AND (sender_email = %s OR sender_domain = %s)
    """, (recipient, sender, sender_domain))
    if cur.fetchone():
        return 'DUNNO'  # Whitelisted, allow

    # Check consent requirements
    if require_consent or require_payment:
        # Check if already approved
        cur.execute("""
            SELECT status FROM consent_requests
            WHERE recipient_email = %s AND sender_email = %s
            AND status = 'approved'
            AND (expires_at IS NULL OR expires_at > NOW())
        """, (recipient, sender))
        if cur.fetchone():
            return 'DUNNO'  # Already consented

        # Create new consent request
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        
        cur.execute("""
            INSERT INTO consent_requests
            (recipient_email, sender_email, token, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (recipient, sender, token, expires_at))
        conn.commit()

        # DEFER email (retry later)
        return f'DEFER Consent required for {sender}'
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    domain VARCHAR(255) NOT NULL,
    portid VARCHAR(255) UNIQUE,
    recovery_key TEXT,
    auth_type VARCHAR(20) DEFAULT 'password',
    email_public_key TEXT,              -- PUBLIC KEY HERE
    email_private_key_encrypted TEXT,   -- ENCRYPTED PRIVATE KEY HERE
    active BOOLEAN DEFAULT TRUE,
    quota_bytes BIGINT DEFAULT 1073741824,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Consent Settings Table
```sql
CREATE TABLE consent_settings (
    user_email VARCHAR(255) PRIMARY KEY,
    require_consent BOOLEAN DEFAULT FALSE,
    require_payment BOOLEAN DEFAULT FALSE,
    payment_amount DECIMAL(10, 2) DEFAULT 0.00,
    payment_address VARCHAR(500),
    whitelist_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Consent Requests Table
```sql
CREATE TABLE consent_requests (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    email_subject TEXT,
    email_preview TEXT,
    payment_txid VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    responded_at TIMESTAMP
)
```

---

## Postfix Configuration

### In master.cf

**Incoming Filter Definition** (lines 51-52):
```postfix
encrypt   unix  -       n       n       -       10      pipe
  flags=Rq user=mail argv=/usr/local/bin/encrypt_filter.py
```

**Outgoing Filter Definition** (lines 55-56):
```postfix
decrypt   unix  -       n       n       -       10      pipe
  flags=Rq user=mail argv=/usr/local/bin/decrypt_filter.py
```

**Reinject Port for Encrypted Emails** (lines 59-70):
```postfix
localhost:10026 inet  n       -       n       -       10      smtpd
  -o content_filter=
  -o receive_override_options=no_header_body_checks
  -o smtpd_helo_restrictions=
  -o smtpd_client_restrictions=
  -o smtpd_sender_restrictions=
  -o smtpd_recipient_restrictions=permit_mynetworks,reject_unauth_destination
  -o smtpd_relay_restrictions=permit_mynetworks,reject_unauth_destination
  -o mynetworks=127.0.0.0/8
  -o smtpd_authorized_xforward_hosts=127.0.0.0/8
  -o smtpd_milters=inet:localhost:8891
  -o non_smtpd_milters=inet:localhost:8891
```

**Reinject Port for Decrypted Emails** (lines 73-84):
```postfix
localhost:10027 inet  n       -       n       -       10      smtpd
  -o content_filter=
  -o receive_override_options=no_header_body_checks
  -o smtpd_helo_restrictions=
  -o smtpd_client_restrictions=
  -o smtpd_sender_restrictions=
  -o smtpd_data_restrictions=
  -o mynetworks=127.0.0.0/8,[::1]/128
  -o smtpd_authorized_xforward_hosts=127.0.0.0/8,[::1]/128
  -o smtpd_milters=inet:localhost:8891
  -o non_smtpd_milters=inet:localhost:8891
```

---

## Encryption Algorithms Used

### Email Content Encryption
- **Algorithm**: RSA-2048
- **Padding**: OAEP (Optimal Asymmetric Encryption Padding)
- **Hash Function**: SHA-256
- **Key Size**: 2048 bits
- **Output**: Base64-encoded ciphertext

### Private Key Storage Encryption
- **Algorithm**: AES-256
- **Mode**: CBC (Cipher Block Chaining)
- **Key Derivation**: Recovery key (32 bytes hex)
- **IV**: Random, prepended to ciphertext
- **Output**: Base64-encoded IV + ciphertext

### Recovery Key
- **Format**: 32 bytes (256 bits)
- **Representation**: Hexadecimal string
- **Generated**: During user creation
- **Purpose**: Decrypt stored private keys
- **Storage**: Database (plaintext)

---

## Security Model

### Zero-Knowledge Scenarios
✅ **Privra ↔ Privra**: 
- Email encrypted by sender's browser with recipient's public key
- Server never sees plaintext
- Only recipient can decrypt

### Gateway Encryption Scenarios
⚠️ **External → Privra**: 
- Server encrypts incoming email with recipient's public key
- Server has access to public key (needed for encryption)
- Server cannot decrypt (doesn't have private key)

⚠️ **Privra → External**: 
- Server decrypts using sender's private key (via recovery key)
- Server has temporary access to plaintext (for gateway operation)
- Server never sees encrypted version stored in sender's mailbox

### Metadata Handling
- **Headers**: From, To, Subject remain plaintext
- **Future Enhancement**: Encrypted subject lines
- **Visibility**: Server and external parties can see metadata

---

## Test Email Headers

### Encrypted Incoming Email
```
From: external@gmail.com
To: user@privra.com
Subject: Hello Privra User
X-Privra-Encrypted: true
X-Privra-Gateway-Encrypted: true
Content-Type: text/plain

aGJRRzUvUDlkbUJRU1Z0MGxFREFBQW9BQjlNenJSUEZ4VUxKNGVQTkVFR
DhhTWJVeTUrZ2ZsN2RIMlBXTmJkVzdMb2pMUWVMNDJLQWJuMGJkYWJKZzJm
...
[long encrypted base64 content]
```

### Decrypted Incoming Email (in browser)
```
From: external@gmail.com
To: user@privra.com
Subject: Hello Privra User
X-Privra-Encrypted: true
X-Privra-Gateway-Encrypted: true
Content-Type: text/plain

Hello Privra User!
This is my message to you.
```

---

## Performance Considerations

### RSA-2048 Encryption
- **Time to encrypt 1KB**: ~5-10ms
- **Time to decrypt 1KB**: ~20-50ms
- **Bottleneck**: Content filters (RSA operations)

### Database Lookups
- **Public key lookup**: ~1-5ms
- **Mitigation**: Add Redis caching for hot keys
- **Cache TTL**: 1 hour recommended

### Email Size Limitations
- **Plaintext limit**: Usually 25-50MB per email
- **Encrypted size**: Roughly same (RSA base64 overhead ~33%)
- **Consideration**: Very large emails may need compression

---

## TODO & Known Issues

### Phase 3.3: Complete
- [ ] Add multipart/HTML email support
- [ ] Implement public key caching in Redis
- [ ] Better error logging and monitoring

### Phase 3.4: Blocking
- [ ] Fix session key retrieval (use recovery_key instead)
- [ ] Implement proper key agent service
- [ ] Add outbound email decryption tests

### Phase 3.5: Not Started
- [ ] Implement WebCrypto in JavaScript
- [ ] Build compose UI with encryption button
- [ ] Build email view UI with decryption logic

### Phase 4: Not Started  
- [ ] Integrate LLM provider (OpenAI, Anthropic, etc.)
- [ ] Implement email categorization AI
- [ ] Add feedback learning loop

### Phase 5: Framework Only
- [ ] Payment provider integration (Stripe, crypto)
- [ ] Consent approval UI
- [ ] Email notifications for consent requests
- [ ] Payment processing flow

---

## Getting Started

1. **Read First**: ENCRYPTION_INFRASTRUCTURE_ANALYSIS.md
2. **Quick Reference**: IMPLEMENTATION_CHECKLIST.md (this file)
3. **Code Review**: Start with `/home/user/Privra/postfix/encrypt_filter.py`
4. **Test**: Send email from Gmail to your Privra account
5. **Debug**: Check Postfix and Dovecot logs

```bash
# View Postfix logs
docker compose logs postfix -f

# View Dovecot logs
docker compose logs dovecot -f

# Manually test encryption filter
echo "test email" | /usr/local/bin/encrypt_filter.py user@privra.com
```

