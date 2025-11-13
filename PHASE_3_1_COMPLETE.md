# Phase 3.1 Implementation Complete: Email Encryption Key Infrastructure

## ✅ What We Built

### 1. Database Schema
**Added to `users` table:**
- `email_public_key TEXT` - RSA public key (PEM format, unencrypted)
- `email_private_key_encrypted TEXT` - RSA private key encrypted with recovery key

### 2. Cryptography Module (`crypto_utils.py`)
Complete encryption toolkit with:
- **RSA Key Generation**: 2048-bit key pairs for email encryption
- **Key Serialization**: PEM format conversion
- **Private Key Encryption**: Uses PortID-compatible AES-CBC encryption
- **Email Encryption/Decryption**: RSA-OAEP for message content

### 3. User Creation Flow
**When admin creates a user:**
1. Generate 32-byte recovery key (hex format, PortID-compatible)
2. Generate RSA key pair for email encryption
3. Encrypt private key with recovery key (AES-CBC)
4. Store public key (unencrypted) and encrypted private key
5. Display recovery key ONCE with warning to save it

### 4. Public Key Lookup API
**Endpoint:** `/api/pubkey/<email>`

**Responses:**
```json
// Privra user with encryption
{
  "email": "alice@privra.com",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...",
  "is_privra": true,
  "encrypted": true
}

// Privra user without encryption yet
{
  "email": "bob@privra.com",
  "is_privra": true,
  "encrypted": false,
  "message": "User exists but hasn't set up encryption yet"
}

// External user (Gmail, etc)
{
  "email": "charlie@gmail.com",
  "is_privra": false,
  "encrypted": false
}
// Returns 404
```

---

## 🔐 How It Works

### Architecture

```
User Creation:
1. Admin creates user (email + password)
2. System generates recovery_key (32 bytes hex)
3. System generates RSA key pair (2048-bit)
4. Private key encrypted with recovery_key (AES-CBC)
5. Public key + encrypted private key stored in database
6. Recovery key shown to admin ONCE

Email Sending (Future - Phase 3.2):
1. Sender composes email in webmail
2. JavaScript calls /api/pubkey/<recipient>
3. If is_privra && encrypted:
   - Encrypt email body with recipient's public key (RSA-OAEP)
   - Send encrypted email
4. If !is_privra:
   - Gateway decrypts (server-side)
   - Send plaintext to external recipient

Email Reading (Future - Phase 3.2):
1. User logs in, private key decrypted with recovery_key
2. JavaScript receives private key (in session)
3. Encrypted emails decrypted in browser with private key
4. Plaintext shown to user
```

### Security Model

**What's Encrypted:**
- Email private keys (encrypted with recovery key)
- Email content between Privra users (future)

**What's NOT Encrypted:**
- Public keys (intentionally public for lookup)
- Email metadata (From, To, Subject - for now)
- Passwords (bcrypt hashed separately)

**Recovery:**
- User loses device → provides recovery_key
- System decrypts private key with recovery_key
- User can read encrypted emails again

---

## 🧪 How to Test

### On Your Server

```bash
# Pull latest changes
git pull origin claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM

# Run migration
docker-compose down
docker-compose build --no-cache admin webmail
docker-compose up -d

# Migrate existing database
docker-compose exec admin python migrate_email_keys.py

# Create a test user
# Go to https://yourdomain.com/admin
# Login with admin/admin
# Click "Add User"
# Create user: test@yourdomain.com
# SAVE THE RECOVERY KEY shown on next page!
```

### Test the API

```bash
# Test public key lookup (should return 200 with public key)
curl https://yourdomain.com/api/pubkey/test@yourdomain.com

# Test external email (should return 404)
curl https://yourdomain.com/api/pubkey/someone@gmail.com
```

---

## 📊 What's Next: Phase 3.2

### Client-Side Encryption in Webmail

**Compose Page:**
1. Add JavaScript encryption library (WebCrypto API)
2. When user types recipient email:
   - Call `/api/pubkey/<recipient>`
   - Show encryption badge: "🔒 Encrypted" or "📧 External"
3. Before sending:
   - If Privra user: Encrypt body with public key
   - If external: Send plaintext (or encrypt for storage)

**Inbox Page:**
1. Detect encrypted emails (metadata flag)
2. Load user's private key from session
3. Decrypt email body in browser (RSA-OAEP)
4. Display plaintext

**Login Flow:**
1. User logs in with password
2. Server decrypts private key using recovery_key
3. Private key sent to browser (encrypted in transit via HTTPS)
4. Private key stored in memory (JavaScript variable)
5. Used to decrypt emails as needed

### Gateway Encryption/Decryption (Phase 3.3)

**Incoming from External:**
- Postfix content filter intercepts plaintext email
- Looks up recipient's public key
- Encrypts email body
- Delivers encrypted email to Dovecot

**Outgoing to External:**
- SMTP submission filter detects external recipient
- Decrypts email with sender's private key (from session)
- Sends plaintext to external server

---

## 🎯 Current Status

**Phase 2: PortID Authentication** ✅
- Login/signup with PortID
- Recovery key generation
- Hybrid auth (PortID + password)

**Phase 3.1: Key Infrastructure** ✅
- RSA key generation
- Key encryption with recovery key
- Public key directory
- API endpoint for key lookup

**Phase 3.2: Client-Side Encryption** 🔄 Next
- Browser encryption (WebCrypto)
- Compose page integration
- Inbox decryption
- Login private key delivery

**Phase 3.3: Gateway Encryption** ⏳ Future
- Postfix content filter
- SMTP submission filter
- External compatibility

---

## 💾 Dependencies Added

**Python:**
- `cryptography==41.0.7` - RSA key generation, OAEP padding
- `pycryptodome==3.19.0` - AES encryption (PortID-compatible)

**Both added to:**
- `admin/requirements.txt`
- `webmail/requirements.txt`

---

## 🔑 Key Files Modified

```
admin/
├── app.py                      # Added pubkey API, key generation in adduser
├── init_db.py                  # Added email_public_key, email_private_key_encrypted
├── requirements.txt            # Added cryptography, pycryptodome
├── crypto_utils.py             # NEW: Encryption utilities
├── migrate_email_keys.py       # NEW: Migration script
└── portid_service.py          # (from Phase 2)

webmail/
├── requirements.txt            # Added cryptography, pycryptodome
└── crypto_utils.py            # NEW: Copy of encryption utilities
```

---

## 🚀 Ready for Phase 3.2?

The foundation is complete! We now have:
- ✅ RSA keys generated and stored
- ✅ Public key lookup API
- ✅ Recovery key system
- ✅ PortID-compatible encryption

**Next step:** Implement client-side encryption in the webmail compose and inbox pages.

Want to continue with Phase 3.2 (browser encryption)?
