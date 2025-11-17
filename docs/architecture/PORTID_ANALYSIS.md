# PortID SDK Complete Analysis

## What PortID Actually Does

After reading the full source code, here's what PortID provides:

### Core Functionality

**1. User Authentication**
```python
# Sign up new user
result = portid.sign_up(username="alice@privra.com", password="pass123")
# Returns: {"username": "alice@privra.com", "recovery_key": "a3f7b2..."}

# Sign in existing user
success = portid.sign_in(username="alice@privra.com", password="pass123")

# Restore account with recovery key (password-less recovery)
data = portid.restore(recovery_key="a3f7b2...", password="pass123")
```

**2. Data Backup & Sync**
```javascript
// JavaScript SDK has these additional methods:
await portid.backupData({emails: [...], settings: {...}})
await portid.restoreData(username, recoveryKey)
await portid.enableAutoBackup(minIntervalHours=24)
```

**3. Encryption (Symmetric AES)**
- **Algorithm**: AES-CBC (Python) / AES (JavaScript)
- **Recovery Key**: 16-32 byte random hex string
- **Password Hashing**: SHA256
- **Storage**: IPFS for encrypted backups

---

## What PortID Does NOT Provide

❌ **No Public/Private Key Cryptography**
- No RSA or ECC key generation
- No asymmetric encryption
- Cannot encrypt data for another user

❌ **No User-to-User Encryption**
- No way to look up another user's public key
- No key exchange mechanism
- Designed for single-user data sync, not messaging

❌ **No Email-Specific Features**
- Not designed for email encryption
- No S/MIME or PGP-like functionality

---

## How PortID Works

### Architecture

```
User Device                    PortID Sync Server           IPFS Network
     |                                |                           |
     | sign_up(username, password)    |                           |
     |---------------------------->   |                           |
     |                                |                           |
     | Generate recovery_key          |                           |
     | (16-byte random hex)           |                           |
     |                                |                           |
     | Encrypt user_data with         |                           |
     | recovery_key (AES)             |                           |
     |                                |                           |
     | Send encrypted_data            |                           |
     |---------------------------->   |                           |
     |                                |                           |
     |                                | Store on IPFS             |
     |                                |-------------------------->|
     |                                |                           |
     | Receive recovery_key           |                           |
     | (MUST SAVE THIS!)              |                           |
     |<----------------------------|  |                           |
     |                                |                           |
```

### Recovery Flow

```
New Device                     PortID Sync Server           IPFS Network
     |                                |                           |
     | restore(recovery_key, password)|                           |
     |---------------------------->   |                           |
     |                                |                           |
     |                                | Fetch encrypted_data      |
     |                                |<--------------------------|
     |                                |                           |
     | Receive encrypted_data         |                           |
     |<----------------------------|  |                           |
     |                                |                           |
     | Decrypt with recovery_key      |                           |
     | (local, client-side)           |                           |
     |                                |                           |
```

---

## Storage Model

**Local Storage (Client-Side):**
```python
# Python SDK uses configurable storage backend
storage.store("credentials", {
    "username": "alice@privra.com",
    "recovery_key": "a3f7b2..."
})
```

**Remote Storage (IPFS):**
```javascript
// JavaScript SDK stores:
{
    "username": "alice@privra.com",
    "app_id": "privra-mail-v1",  // Our app identifier
    "encrypted_data": "U2FsdGVkX1...",  // AES encrypted
    "ipfs_hash": "Qm..."
}
```

---

## App ID Concept

**What is app_id?**
- Namespace for your application
- Allows PortID to separate data from different apps
- We're using: `"privra-mail-v1"`

**Example:**
```python
portid = PortID(
    app_id="privra-mail-v1",  # Our application identifier
    api_base_url="http://portid-server:5001"
)
```

Different apps can use same PortID server:
- `app_id="privra-mail-v1"` → Email data
- `app_id="privra-notes-v1"` → Notes data
- `app_id="my-chat-app"` → Chat data

---

## How We're Using PortID (Current Implementation)

### Phase 2 Integration (What We Built)

**Location**: `admin/portid_service.py`, `webmail/portid_service.py`

**Current Usage:**
```python
# We ONLY use PortID for authentication
result = portid_service.sign_up(username, password)
# Returns: {"username": "alice@privra.com", "recovery_key": "..."}

# Store in OUR database (not PortID):
db.execute("""
    INSERT INTO users (email, portid, recovery_key, password)
    VALUES (%s, %s, %s, %s)
""", (username, result['portid'], result['recovery_key'], bcrypt_hash))
```

**We're using it as**:
- ✅ Identity verification (login/signup)
- ✅ Recovery key generation
- ❌ NOT using backup_data() yet
- ❌ NOT using IPFS storage yet
- ❌ NOT using for encryption yet

---

## How We SHOULD Use PortID for Email Encryption

### Updated Architecture (Phase 3)

Since PortID doesn't provide public/private keys for email encryption, we need to **generate our own keys** and use PortID's recovery key to encrypt them.

**Step 1: Generate Email Encryption Keys**
```python
from cryptography.hazmat.primitives.asymmetric import rsa

def signup_with_encryption(username, password):
    # 1. Create PortID identity
    portid_result = portid_service.sign_up(username, password)
    recovery_key = portid_result['recovery_key']

    # 2. Generate RSA key pair for EMAIL encryption (separate!)
    email_private_key = rsa.generate_private_key(65537, 2048)
    email_public_key = email_private_key.public_key()

    # 3. Encrypt the email private key with PortID recovery key
    from encryption import encrypt_data  # From PortID SDK
    encrypted_email_private_key = encrypt_data(
        {"private_key": serialize(email_private_key)},
        recovery_key  # Use PortID recovery key as encryption key
    )

    # 4. Store in database
    db.execute("""
        INSERT INTO users (
            email,
            portid,
            recovery_key,
            email_public_key,           -- Anyone can read this
            email_private_key_encrypted -- Only user can decrypt (needs recovery_key)
        ) VALUES (%s, %s, %s, %s, %s)
    """, (
        username,
        portid_result['portid'],
        recovery_key,
        serialize(email_public_key),
        encrypted_email_private_key
    ))

    return {
        "username": username,
        "recovery_key": recovery_key,  # User MUST save this!
        "public_key": serialize(email_public_key)
    }
```

**Step 2: Login and Decrypt Private Key**
```python
def login_with_encryption(username, password):
    # 1. Verify with PortID
    portid_result = portid_service.login(username, password)

    # 2. Get recovery key from database
    user = db.query("SELECT recovery_key, email_private_key_encrypted FROM users WHERE email=%s", username)

    # 3. Decrypt email private key using PortID recovery key
    from encryption import decrypt_data
    email_private_key_dict = decrypt_data(
        user.email_private_key_encrypted,
        user.recovery_key
    )
    email_private_key = deserialize(email_private_key_dict['private_key'])

    # 4. Store in session (encrypted)
    session['email_private_key'] = encrypt_for_session(email_private_key)
    session['recovery_key'] = user.recovery_key
```

**Step 3: Encrypt Email for Recipient**
```javascript
// In browser (webmail compose)
async function sendEncryptedEmail(recipient, subject, body) {
    // 1. Lookup recipient's PUBLIC key
    let response = await fetch(`/api/pubkey/${recipient}`)

    if (!response.ok) {
        // External user - send plaintext or gateway decrypt
        return sendPlaintextEmail(recipient, subject, body)
    }

    let data = await response.json()

    // 2. Encrypt email body with recipient's PUBLIC key
    let publicKey = await importRSAKey(data.public_key)
    let encrypted = await crypto.subtle.encrypt(
        {name: "RSA-OAEP"},
        publicKey,
        new TextEncoder().encode(body)
    )

    // 3. Send encrypted email
    await fetch('/api/send', {
        method: 'POST',
        body: JSON.stringify({
            to: recipient,
            subject: subject,
            body: arrayBufferToBase64(encrypted),
            encrypted: true
        })
    })
}
```

**Step 4: Decrypt Received Email**
```javascript
// In browser (webmail inbox)
async function decryptEmail(encryptedBody) {
    // 1. Get user's PRIVATE key from session
    let privateKeyData = await fetch('/api/session/private-key')
    let privateKey = await importRSAKey(privateKeyData.private_key)

    // 2. Decrypt email body
    let decrypted = await crypto.subtle.decrypt(
        {name: "RSA-OAEP"},
        privateKey,
        base64ToArrayBuffer(encryptedBody)
    )

    return new TextDecoder().decode(decrypted)
}
```

---

## Using PortID Backup for Email Keys

We can ALSO use PortID's `backupData()` to sync keys across devices:

```javascript
// After generating email encryption keys
await portid.backupData({
    email_public_key: publicKeyPEM,
    email_private_key_encrypted: encryptedPrivateKey,
    app_data: "privra-mail-v1"
})

// On new device
let restored = await portid.restoreData(username, recoveryKey)
// Now user has their email keys on the new device!
```

---

## Summary: PortID's Role in Privra

**What PortID Provides:**
1. ✅ **Identity Management**: Sign up, login, restore
2. ✅ **Recovery Key Generation**: For account recovery
3. ✅ **Symmetric Encryption**: AES for data backup
4. ✅ **IPFS Storage**: Decentralized backup
5. ✅ **Multi-Device Sync**: Backup and restore across devices

**What We Must Build:**
1. ❌ **Email Encryption Keys**: Generate RSA/ECC ourselves
2. ❌ **Public Key Directory**: `/api/pubkey/<email>` lookup
3. ❌ **Key Management**: Encrypt private keys with PortID recovery key
4. ❌ **Email Encryption Logic**: Client-side encrypt/decrypt
5. ❌ **Gateway Encryption/Decryption**: For external email compatibility

---

## Next Steps for Phase 3

1. **Modify signup to generate email encryption keys**
2. **Encrypt private key with PortID recovery key**
3. **Store public keys in database**
4. **Create public key lookup API**
5. **Implement client-side email encryption (WebCrypto)**
6. **Implement gateway encryption/decryption**

PortID handles the **identity layer**, we handle the **email encryption layer**.
