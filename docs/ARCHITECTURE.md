# PRIVRA TECHNICAL ARCHITECTURE

## System Overview

Privra is a multi-tenant, zero-knowledge email and productivity workspace built on:
- **Containerization:** Docker Compose
- **Backend:** Python (Flask)
- **Database:** PostgreSQL
- **Email:** Postfix (SMTP) + Dovecot (IMAP)
- **Identity:** PortID SDK (zero-knowledge keyring)
- **AI:** vLLM + Llama 3.1 (multi-LoRA inference)
- **Hosting:** DigitalOcean Droplets

---

## Core Principles

### 1. Zero-Knowledge by Design
- Server stores encrypted data blobs
- Only user holds decryption keys (via PortID keyring)
- Even database breach = useless encrypted data

### 2. Multi-Tenancy with Isolation
- Single server serves 1000+ users
- User data isolated via database row-level security
- AI adapters hot-swapped per request

### 3. Privacy-First Defaults
- No tracking pixels in UI
- No third-party analytics
- No cloud AI (all local)

---

## Infrastructure Stack

```
┌─────────────────────────────────────────────────────────┐
│  PRIVRA DROPLET (DigitalOcean)                          │
│  ┌────────────────────────────────────────────────┐     │
│  │  Docker Compose Network                        │     │
│  │                                                 │     │
│  │  ┌──────────────┐  ┌──────────────┐            │     │
│  │  │  webmail     │  │  postgres    │            │     │
│  │  │  (Flask)     │  │  (privra-    │            │     │
│  │  │  Port: 5001  │  │   dockyard)  │            │     │
│  │  └──────────────┘  └──────────────┘            │     │
│  │         │                   │                   │     │
│  │         │                   │                   │     │
│  │  ┌──────────────┐  ┌──────────────┐            │     │
│  │  │  postfix     │  │  dovecot     │            │     │
│  │  │  (SMTP)      │  │  (IMAP)      │            │     │
│  │  │  Port: 25    │  │  Port: 993   │            │     │
│  │  └──────────────┘  └──────────────┘            │     │
│  │         │                   │                   │     │
│  │         │                   │                   │     │
│  │  ┌──────────────┐  ┌──────────────┐            │     │
│  │  │  vllm        │  │  redis       │            │     │
│  │  │  (AI)        │  │  (cache)     │            │     │
│  │  │  Port: 8000  │  │  Port: 6379  │            │     │
│  │  └──────────────┘  └──────────────┘            │     │
│  │         │                                       │     │
│  │         │                                       │     │
│  │  ┌──────────────┐                               │     │
│  │  │  adapter-    │                               │     │
│  │  │  trainer     │                               │     │
│  │  │  (worker)    │                               │     │
│  │  └──────────────┘                               │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
         │
         │ HTTPS (TLS)
         │
    [ INTERNET ]
         │
    [ USERS ]
```

---

## Database Schema

### Core Tables

```sql
-- Users (main identity)
users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),  -- bcrypt
    created_at TIMESTAMP,
    is_active BOOLEAN
)

-- PortID encrypted keyring backups
portid_backups (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    app_id VARCHAR(100),
    encrypted_data TEXT,  -- Contains: email keys, wallet keys, AI adapter keys
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- Session management (device tracking)
user_sessions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    session_token VARCHAR(255) UNIQUE,
    device_name VARCHAR(255),  -- "Chrome on Windows"
    browser VARCHAR(100),
    os VARCHAR(100),
    ip_address VARCHAR(45),
    location VARCHAR(255),
    last_activity TIMESTAMP,
    is_active BOOLEAN,
    revoked_at TIMESTAMP
)

-- Multi-chain wallets
wallet_keys (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    chain_type VARCHAR(20),  -- 'solana', 'evm'
    encrypted_private_key TEXT,
    public_key TEXT,
    address VARCHAR(255),
    created_at TIMESTAMP
)
```

### Priority 1: Privacy Shield Tables

```sql
-- Dynamic email aliases
email_aliases (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    alias VARCHAR(255) UNIQUE,  -- netflix.user@privra.xyz
    service_name VARCHAR(255),  -- "Netflix"
    created_at TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    burned_at TIMESTAMP
)

-- Gatekeeper challenges
sender_challenges (
    id SERIAL PRIMARY KEY,
    sender_email VARCHAR(255),
    recipient_email VARCHAR(255) REFERENCES users(email),
    challenge_code VARCHAR(10),
    challenge_sent_at TIMESTAMP,
    challenge_passed BOOLEAN DEFAULT FALSE,
    passed_at TIMESTAMP
)

-- Trusted senders (passed gatekeeper)
trusted_senders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    sender_email VARCHAR(255),
    trust_level VARCHAR(20),  -- 'auto', 'manual', 'org'
    added_at TIMESTAMP
)
```

### Priority 3: B2B/Organization Tables

```sql
-- Organizations
organizations (
    id SERIAL PRIMARY KEY,
    org_did VARCHAR(255) UNIQUE,  -- did:privra:org:acme-corp
    org_name VARCHAR(255),
    admin_email VARCHAR(255) REFERENCES users(email),
    subscription_tier VARCHAR(50),
    max_employees INT,
    created_at TIMESTAMP
)

-- Digital badges (Verifiable Credentials)
digital_badges (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id),
    employee_portid VARCHAR(255),
    badge_credential TEXT,  -- Signed JWT
    role VARCHAR(50),  -- 'admin', 'member', 'contractor'
    expires_at TIMESTAMP,  -- NULL = permanent
    issued_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(255)
)

-- Organization membership
org_members (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id),
    user_email VARCHAR(255) REFERENCES users(email),
    badge_id INT REFERENCES digital_badges(id),
    role VARCHAR(50),
    joined_at TIMESTAMP
)

-- Company knowledge base
org_knowledge_base (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id),
    document_name VARCHAR(255),
    document_type VARCHAR(50),  -- 'pdf', 'markdown', 'slack_export'
    uploaded_by VARCHAR(255),
    uploaded_at TIMESTAMP,
    file_path TEXT
)

-- Legal holds
legal_holds (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id),
    user_email VARCHAR(255) REFERENCES users(email),
    reason TEXT,
    initiated_by VARCHAR(255),
    initiated_at TIMESTAMP,
    released_at TIMESTAMP
)
```

### Priority 2: AI Workspace Tables

```sql
-- User LoRA adapters
user_adapters (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    org_id INT REFERENCES organizations(id),
    adapter_name VARCHAR(255) UNIQUE,
    adapter_path TEXT,  -- /adapters/user_123.safetensors
    adapter_type VARCHAR(50),  -- 'individual', 'org_shared', 'role_based'
    last_trained_at TIMESTAMP,
    training_data_count INT,
    is_active BOOLEAN DEFAULT TRUE
)

-- Adapter training queue
adapter_training_queue (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    adapter_id INT REFERENCES user_adapters(id),
    status VARCHAR(50),  -- 'pending', 'training', 'completed', 'failed'
    priority INT DEFAULT 5,
    training_config JSONB,
    queued_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
)

-- Email embeddings (using pgvector extension)
email_embeddings (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    email_id VARCHAR(255),
    embedding vector(384),  -- Sentence-Transformer dimensions
    indexed_at TIMESTAMP
)

-- AI memory blobs (Neural Sync)
ai_memory_blobs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    blob_version INT,
    encrypted_blob TEXT,  -- JSON: preferences, writing style, context
    created_at TIMESTAMP,
    synced_to_portid BOOLEAN DEFAULT FALSE
)

-- Living documents
living_docs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    thread_id VARCHAR(255),
    doc_title VARCHAR(255),
    markdown_content TEXT,
    last_updated TIMESTAMP,
    auto_update BOOLEAN DEFAULT TRUE
)

-- User AI preferences
ai_user_preferences (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) UNIQUE REFERENCES users(email),
    writing_style VARCHAR(50),  -- 'casual', 'professional', 'technical'
    verbosity VARCHAR(50),  -- 'concise', 'balanced', 'detailed'
    industry VARCHAR(100),  -- 'medical', 'legal', 'tech', 'finance'
    jargon_level VARCHAR(50),  -- 'minimal', 'moderate', 'heavy'
    allow_training BOOLEAN DEFAULT TRUE,
    training_frequency VARCHAR(50),  -- 'daily', 'weekly', 'monthly'
    updated_at TIMESTAMP
)
```

---

## Security Architecture

### 1. Encryption Layers

```
┌─────────────────────────────────────────────────┐
│  CLIENT (Browser)                               │
│  ┌───────────────────────────────────────┐      │
│  │  PortID SDK                           │      │
│  │  - Generates keys in IndexedDB        │      │
│  │  - Encrypts keyring with password     │      │
│  │  - Never sends plaintext keys         │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
                    │
                    │ HTTPS (TLS 1.3)
                    ▼
┌─────────────────────────────────────────────────┐
│  SERVER (Privra)                                │
│  ┌───────────────────────────────────────┐      │
│  │  Flask Application                    │      │
│  │  - Receives encrypted blobs           │      │
│  │  - Stores in PostgreSQL               │      │
│  │  - CANNOT decrypt (no keys)           │      │
│  └───────────────────────────────────────┘      │
│                                                  │
│  ┌───────────────────────────────────────┐      │
│  │  PostgreSQL (Data at Rest)            │      │
│  │  - Encrypted columns (AES-256)        │      │
│  │  - TLS connections                    │      │
│  │  - Regular backups (encrypted)        │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
```

### 2. Authentication Flow

```
User Registration:
1. User creates account (email + password)
2. PortID generates recovery key (client-side)
3. PortID creates encrypted keyring
4. Keyring synced to server (encrypted)
5. User downloads recovery key (PDF)

User Login:
1. User enters email + password
2. Server validates credentials
3. Server returns encrypted keyring blob
4. PortID decrypts keyring (client-side)
5. Session created with device tracking
6. AI adapter keys extracted from keyring

New Device Login:
1. User enters email + password + recovery key
2. PortID decrypts keyring with recovery key
3. Keyring restored to new device
4. AI "remembers" user (Neural Sync)
```

### 3. Email Encryption

```
Outgoing Email:
1. User composes email
2. If recipient has PGP key → Encrypt with PGP
3. If recipient is Privra user → Use email keypair from keyring
4. Else → Send plaintext (warn user)

Incoming Email:
1. Postfix receives email
2. If encrypted → Store as-is
3. If plaintext → Optionally encrypt at rest
4. Deliver to user's IMAP mailbox
5. User decrypts in client (if needed)
```

---

## Email Infrastructure

### Postfix Configuration (SMTP)

```conf
# /etc/postfix/main.cf

# Virtual alias support
virtual_alias_maps = pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# Content filtering (for Gatekeeper Agent)
content_filter = gatekeeper:127.0.0.1:10025

# TLS settings
smtpd_tls_cert_file = /etc/letsencrypt/live/privra.xyz/fullchain.pem
smtpd_tls_key_file = /etc/letsencrypt/live/privra.xyz/privkey.pem
smtpd_tls_security_level = may

# SPF/DKIM
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
```

### PostgreSQL Virtual Alias Map

```conf
# /etc/postfix/pgsql-virtual-alias-maps.cf
hosts = localhost
user = postfix_query
password = ***
dbname = privra_dockyard
query = SELECT user_email FROM email_aliases
        WHERE alias='%s' AND is_active=TRUE
        LIMIT 1
```

### Gatekeeper Content Filter

```python
# gatekeeper_daemon.py (runs on port 10025)
class GatekeeperDaemon:
    def process_email(self, sender, recipient, message):
        # Check if sender is trusted
        if is_trusted(sender, recipient):
            return "ACCEPT"

        # Check if sender has passed challenge
        if has_passed_challenge(sender, recipient):
            return "ACCEPT"

        # Send challenge email
        send_challenge(sender, recipient)
        return "HOLD"
```

---

## AI Architecture (Priority 2)

### Multi-LoRA Inference

```
Request Flow:
1. User asks: "Summarize my emails from John"
2. Flask receives request with user_email
3. vllm_client.generate(prompt, user_email="alice@privra.xyz")
4. vLLM loads:
   - Base model (llama-3.1-8b) - already in VRAM
   - User adapter (alice_adapter.safetensors) - 50MB
5. Model processes with merged weights
6. Response generated
7. Adapter unloaded (if VRAM needed)

Cache Optimization:
- vLLM caches 100 most-used adapters in RAM
- LRU eviction when cache full
- Redis tracks adapter usage frequency
```

### Adapter Training Pipeline

```
Background Worker (Celery/RQ):
1. Cron job: Every Sunday at 2am
2. For each user with >50 new emails since last training:
   a. Collect sent emails as training data
   b. Format as prompt-completion pairs
   c. Add to adapter_training_queue
3. Worker picks job from queue (priority order)
4. Loads base model + PEFT config
5. Fine-tunes LoRA adapter (3 epochs, ~10 minutes)
6. Saves adapter to /adapters/user_123.safetensors
7. Updates user_adapters table
8. Adapter ready for next inference
```

---

## API Endpoints

### Public Routes
- `GET /` - Landing page
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /register` - Registration page
- `POST /register` - Create account
- `GET /sitemap.xml` - SEO sitemap

### Authenticated Routes
- `GET /inbox` - Email list
- `GET /email/<id>` - Email detail
- `POST /compose` - Send email
- `GET /wallet` - Crypto wallet
- `GET /sessions` - Device activity
- `POST /sessions/revoke` - Sign out device

### Priority 1: Privacy Shield
- `GET /aliases` - Alias management
- `POST /aliases/generate` - Create new alias
- `POST /aliases/<id>/burn` - Kill alias

### Priority 3: B2B
- `GET /org/register` - Org registration
- `GET /org/admin` - Admin dashboard
- `POST /org/badges/issue` - Issue badge
- `POST /org/badges/revoke` - Revoke badge
- `GET /org/traffic` - Traffic Tower
- `POST /org/knowledge/upload` - Upload docs

### Priority 2: AI
- `POST /api/rag/query` - Chat with email
- `POST /api/living-doc/generate` - Create living doc
- `GET /api/adapter/status` - Adapter training status

---

## Deployment

### Environment Variables

```bash
# Database
POSTGRES_HOST=privra-dockyard
POSTGRES_DB=privra
POSTGRES_USER=privra_user
POSTGRES_PASSWORD=***

# Flask
SECRET_KEY=***
FLASK_ENV=production

# Email
SMTP_HOST=postfix
SMTP_PORT=25
IMAP_HOST=dovecot
IMAP_PORT=993

# PortID
PORTID_APP_ID=privra-mail
PORTID_NETWORK_URL=https://portid.harboria.xyz

# AI (Priority 2)
VLLM_URL=http://vllm:8000
ADAPTER_STORAGE_PATH=/adapters
OLLAMA_BASE_URL=http://ollama:11434

# Redis
REDIS_URL=redis://privra-cache:6379
```

### Docker Compose

```yaml
version: '3.8'

services:
  webmail:
    build: ./webmail
    ports:
      - "5001:5001"
    environment:
      - POSTGRES_HOST=privra-dockyard
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    container_name: privra-dockyard
    environment:
      - POSTGRES_DB=privra
      - POSTGRES_USER=privra_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data

  postfix:
    image: boky/postfix
    ports:
      - "25:25"
    environment:
      - ALLOWED_SENDER_DOMAINS=privra.xyz

  dovecot:
    image: dovecot/dovecot
    ports:
      - "993:993"

  redis:
    image: redis:7
    container_name: privra-cache

volumes:
  postgres-data:
```

---

## Monitoring & Logging

### Metrics to Track
- User registrations per day
- Email volume (sent/received)
- Alias creation rate
- Alias burn rate
- Session creation/revocation
- AI query latency
- Adapter cache hit rate

### Logs
- Nginx access logs
- Flask application logs
- Postfix mail logs
- vLLM inference logs
- Database slow queries

---

## Backup Strategy

### Daily Backups
- PostgreSQL dump (encrypted)
- User adapter files
- Email storage

### Weekly Backups
- Full system snapshot (DigitalOcean)
- PortID keyring backups (already encrypted)

### Disaster Recovery
- RPO (Recovery Point Objective): 24 hours
- RTO (Recovery Time Objective): 4 hours
- Backup storage: S3 (encrypted)

---

This architecture scales to 10,000+ users on a single server with proper optimization.
