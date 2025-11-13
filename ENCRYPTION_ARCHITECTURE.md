# Privra Hybrid Encryption Architecture - Phase 3

## Overview

Privra implements a **hybrid encryption model** that provides:
- **Zero-knowledge encryption** between Privra users (E2E encrypted)
- **Compatibility** with traditional email systems (gateway encryption/decryption)
- **Automatic encryption** of all stored emails

## Encryption Flows

### 1. Privra → Privra (Full E2E Encryption)

```
Alice (Privra)                    Server                    Bob (Privra)
     |                              |                             |
     | Compose email                |                             |
     |----------------------------->|                             |
     |                              |                             |
     | Lookup Bob's public key      |                             |
     |<-----------------------------|                             |
     |                              |                             |
     | Encrypt with Bob's key       |                             |
     | (client-side JavaScript)     |                             |
     |                              |                             |
     | Send encrypted email         |                             |
     |----------------------------->|                             |
     |                              |                             |
     |                              | Store encrypted             |
     |                              | (server never sees plain)   |
     |                              |                             |
     |                              | Deliver encrypted           |
     |                              |---------------------------->|
     |                              |                             |
     |                              |                             | Decrypt with own key
     |                              |                             | (client-side)
     |                              |                             |
```

**Key Points:**
- Encryption happens in browser before sending
- Server only sees encrypted ciphertext
- Recipient decrypts in their browser
- True zero-knowledge

---

### 2. External → Privra (Gateway Encryption)

```
Gmail User                        Privra Server              Alice (Privra)
     |                                  |                           |
     | Send plaintext email             |                           |
     |--------------------------------->|                           |
     |                                  |                           |
     |                                  | Postfix receives          |
     |                                  |                           |
     |                                  | Lookup Alice's public key |
     |                                  | (from PortID/database)    |
     |                                  |                           |
     |                                  | ENCRYPT with Alice's key  |
     |                                  | (Python crypto)           |
     |                                  |                           |
     |                                  | Store encrypted in Dovecot|
     |                                  |                           |
     |                                  | Alice fetches encrypted   |
     |                                  |-------------------------->|
     |                                  |                           |
     |                                  |                           | Decrypt in browser
     |                                  |                           |
```

**Key Points:**
- External email arrives as plaintext
- Postfix content filter encrypts before delivery
- Encrypted with recipient's PortID public key
- Stored encrypted in mailbox
- Recipient decrypts when reading

---

### 3. Privra → External (Gateway Decryption)

```
Alice (Privra)                    Privra Server              Gmail User
     |                                  |                           |
     | Compose email                    |                           |
     |                                  |                           |
     | Detect recipient is external     |                           |
     | (not in Privra user directory)   |                           |
     |                                  |                           |
     | Encrypt with Alice's own key     |                           |
     | (for storage/drafts)             |                           |
     |                                  |                           |
     | Send encrypted                   |                           |
     |--------------------------------->|                           |
     |                                  |                           |
     |                                  | Detect external recipient |
     |                                  |                           |
     |                                  | DECRYPT with sender's key |
     |                                  | (server has sender's session)|
     |                                  |                           |
     |                                  | Send as plaintext SMTP    |
     |                                  |-------------------------->|
     |                                  |                           |
     |                                  |                           | Receives plaintext
     |                                  |                           |
```

**Key Points:**
- User composes in encrypted form
- Server detects external recipient
- Decrypts at gateway using sender's session key
- Sends as normal plaintext email
- Compatible with Gmail, Outlook, etc.

---

## Technical Components

### 1. Public Key Infrastructure

**Database Schema:**
```sql
-- Add public key storage to users table
ALTER TABLE users ADD COLUMN public_key TEXT;
ALTER TABLE users ADD COLUMN private_key_encrypted TEXT;  -- Encrypted with PortID
```

**Public Key Lookup API:**
```python
# /api/lookup-key/<email>
# Returns: {"email": "user@privra.com", "public_key": "...", "is_privra": true}
# Or: {"email": "external@gmail.com", "is_privra": false}
```

### 2. Client-Side Encryption (WebCrypto API)

**Compose Page:**
```javascript
// When composing email:
1. Check if recipient is Privra user (API call)
2. If Privra: Encrypt with recipient's public key
3. If External: Encrypt with own key (for drafts)
4. Send to server
```

**Inbox Page:**
```javascript
// When viewing email:
1. Receive encrypted ciphertext
2. Decrypt with own private key (from PortID)
3. Display plaintext
```

### 3. Server-Side Encryption Gateway

**Postfix Content Filter:**
```python
# /usr/local/bin/encrypt-filter.py
# Reads incoming email from stdin
# Encrypts with recipient's public key
# Delivers to Dovecot
```

**Postfix configuration:**
```
# master.cf
encrypt    unix  -       n       n       -       -       pipe
  flags=Rq user=mail argv=/usr/local/bin/encrypt-filter.py ${recipient}

# main.cf
content_filter = encrypt:
```

### 4. Server-Side Decryption Gateway (for outbound)

**SMTP Submission Filter:**
```python
# Before sending to external recipients:
1. Detect if recipient is external (not in Privra directory)
2. Decrypt using sender's session key (stored during PortID auth)
3. Send plaintext via SMTP
```

---

## Security Considerations

### Key Management

1. **Private Keys**: Never leave the client
   - Encrypted with PortID password
   - Decrypted in browser memory only
   - Never sent to server

2. **Public Keys**: Stored in database
   - Distributed via API
   - Verified via PortID
   - Can be public (it's a public key!)

3. **Session Keys**: Temporary
   - Held during active session for gateway decryption
   - Cleared on logout
   - Encrypted in Redis

### Trust Model

- **Privra users trust the server** for gateway operations
- Server can decrypt emails to external recipients (by design)
- Server cannot decrypt Privra-to-Privra emails (zero-knowledge)
- External emails are encrypted at rest

### Metadata

- Email metadata (From, To, Subject) still visible to server
- Future enhancement: Encrypted headers
- Timestamps, IP addresses logged (privacy consideration)

---

## Implementation Phases

### Phase 3.1: Key Infrastructure
- [x] PortID integration (Phase 2 - DONE)
- [ ] Add public_key column to database
- [ ] Key generation during PortID signup
- [ ] Public key lookup API
- [ ] Privra user directory

### Phase 3.2: Client-Side Encryption
- [ ] WebCrypto integration in webmail
- [ ] Compose page encryption
- [ ] Inbox decryption
- [ ] Key storage in browser (IndexedDB)

### Phase 3.3: Gateway Encryption (Incoming)
- [ ] Postfix content filter
- [ ] Encrypt external → Privra emails
- [ ] Test with Gmail, Outlook

### Phase 3.4: Gateway Decryption (Outgoing)
- [ ] SMTP submission filter
- [ ] Detect external recipients
- [ ] Decrypt Privra → external emails
- [ ] Test delivery to external

### Phase 3.5: Testing & Refinement
- [ ] End-to-end tests
- [ ] Performance optimization
- [ ] Error handling
- [ ] User experience polish

---

## User Experience

### For Privra Users:

**Sending:**
- Compose email normally
- System automatically detects recipient type
- Badge shows: "🔒 Encrypted (Privra)" or "🔓 External (unencrypted)"
- No extra steps required

**Reading:**
- Click email to view
- Auto-decrypts in browser
- Shows plaintext instantly
- Lock icon indicates encryption status

### For External Users:

**Receiving from Privra:**
- Receives normal plaintext email
- No special client needed
- Works with Gmail, iPhone Mail, etc.

**Sending to Privra:**
- Sends normal email
- Server encrypts upon receipt
- Privra user sees decrypted version
- External user unaware of encryption

---

## Migration Path

1. **Current State**: PortID auth, plaintext storage
2. **Phase 3.1**: Add key infrastructure
3. **Phase 3.2**: Enable client-side crypto (opt-in)
4. **Phase 3.3**: Enable gateway encryption (automatic)
5. **Phase 3.4**: Enable gateway decryption (automatic)
6. **Full Deployment**: All emails encrypted at rest

Existing emails remain plaintext (can be migrated later).

---

## Advantages of This Approach

✅ **Zero-knowledge** between Privra users
✅ **Compatible** with traditional email
✅ **Gradual rollout** possible
✅ **No special client** needed for external users
✅ **Encrypted at rest** for all users
✅ **Works with IMAP** (encrypted messages)

## Trade-offs

⚠️ **Server can decrypt** emails to external recipients (gateway function)
⚠️ **Metadata visible** to server (From, To, Subject)
⚠️ **Search complexity** (encrypted content)
⚠️ **External clients** see encrypted gibberish if they use IMAP directly

---

## Next Steps

Ready to implement Phase 3.1: Key Infrastructure?

This includes:
1. Generate key pairs during PortID signup
2. Store public keys in database
3. Create public key lookup API
4. Build Privra user directory
