# What PortID Does in Privra Mail

## Short Answer

**PortID is OPTIONAL.** It provides:
- Zero-knowledge user authentication (alternative to passwords)
- Recovery keys for account restoration
- Decentralized data backup via IPFS (not yet used)

**Currently in Privra:** PortID is used ONLY for authentication. You can ignore it and use regular passwords.

---

## What PortID Actually Is

PortID is a **zero-knowledge authentication system** created by Harboria Labs. Think of it as:
- Alternative to traditional username/password login
- Users authenticate with PortID instead of passwords
- Server never sees the actual password
- Recovery key allows restoring account on new devices

**GitHub:** https://github.com/Harboria-Labs/PortID

---

## How PortID Works in Privra (Current Implementation)

### Phase 2: PortID Authentication (What We Built)

**When enabled**, users can check a box during login:

```
Login Page:
┌─────────────────────────┐
│ Username: [________]    │
│ Password: [________]    │
│ ☑ Use PortID Auth      │  ← This checkbox
│ [Login]                 │
└─────────────────────────┘
```

**Authentication Flow:**

```
User enters credentials
    ↓
If "Use PortID" checked:
    → Call PortID SDK to verify identity
    → PortID checks username/password via its server
    → Returns success/fail
    ↓
If PortID disabled or unchecked:
    → Use traditional password (bcrypt)
    → Check against database
    ↓
Login success
```

**What PortID SDK Does:**
```python
# From admin/portid_service.py
portid_service.login(username, password)

# This calls PortID's server to verify identity
# Returns: {success: True, portid: "user123", token: "..."}
```

---

## What PortID Does NOT Do (Yet)

❌ **Does NOT encrypt emails** (we built that separately in Phase 3.1)
❌ **Does NOT store email keys** (we generate RSA keys ourselves)
❌ **Does NOT provide public key directory** (we built `/api/pubkey/<email>`)
❌ **Does NOT handle email content** (just authentication)

---

## How We USE PortID for Email Encryption (Phase 3.1)

While PortID doesn't provide email encryption directly, we use its **recovery key** to encrypt email private keys:

### Our Encryption Architecture:

```
User Creation:
1. Generate PortID recovery key (32 bytes hex)
   recovery_key = "a3f7b2c1..." (64 characters)

2. Generate RSA key pair for emails (separate from PortID)
   email_private_key = RSA 2048-bit
   email_public_key = RSA 2048-bit

3. Encrypt email private key WITH PortID recovery key
   encrypted_private_key = AES_encrypt(email_private_key, recovery_key)

4. Store in database:
   - email_public_key (unencrypted - for others to lookup)
   - email_private_key_encrypted (encrypted with recovery_key)
   - recovery_key (user must save this!)
```

**Why this works:**
- User loses device → still has recovery_key saved
- User enters recovery_key → system decrypts email private key
- User can read encrypted emails again

---

## PortID in Privra: The Complete Picture

### Layer 1: Authentication (PortID)
```
PortID handles:
- User signup/login
- Recovery key generation
- Zero-knowledge authentication
```

### Layer 2: Email Encryption (Our Code)
```
We built:
- RSA key pair generation
- Email encryption/decryption
- Public key directory (/api/pubkey)
- Private key encrypted with PortID recovery key
```

### How They Connect:
```
PortID recovery key
       ↓
  (used to encrypt)
       ↓
Email private key
       ↓
  (used to decrypt)
       ↓
   Encrypted emails
```

---

## Do You Need PortID?

**NO!** PortID is completely optional.

**Without PortID:**
- Users login with regular passwords ✅
- Encryption still works ✅
- Recovery keys still generated ✅
- Everything functions normally ✅

**With PortID:**
- Alternative authentication method
- Zero-knowledge login
- No passwords stored on PortID server
- Decentralized backup (IPFS - not yet implemented)

---

## Configuration

**In `.env` file:**
```bash
# Leave these empty to DISABLE PortID
PORTID_APP_ID=privra-mail-v1
PORTID_API_URL=http://localhost:5001
```

**To disable PortID:**
- Set `PORTID_API_URL=` (empty)
- Restart services
- Checkbox won't appear on login page

**To enable PortID:**
1. Deploy PortID Sync Server: https://github.com/Harboria-Labs/PortID
2. Set `PORTID_API_URL=http://your-portid-server:5001`
3. Restart services
4. Checkbox appears on login page

---

## Summary

**What PortID Does:**
- 🔐 Zero-knowledge authentication
- 🔑 Recovery key generation
- ☁️ IPFS backup (not yet used in Privra)

**What Privra Does:**
- 📧 Email encryption (RSA)
- 🔒 Uses PortID recovery key to protect email private keys
- 🌐 Public key directory
- 📨 Hybrid encryption (Privra-to-Privra E2E, gateway for external)

**The Connection:**
- PortID = Identity layer
- Privra = Email encryption layer
- Recovery key = The link between them

**Current Status:**
- ✅ PortID authentication optional
- ✅ Recovery keys generated
- ✅ Email encryption infrastructure ready
- 🔄 Client-side encryption (Phase 3.2) - next!
