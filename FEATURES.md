# Privra Mail Server - Complete Feature Documentation

**Last Updated**: November 14, 2025
**Version**: 1.0
**Branch**: `claude/fix-dkim-admin-security-01TwL5XHHQivpvZdf7qmugne`

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Implemented Features](#implemented-features)
3. [User Profile System](#user-profile-system)
4. [NFT Verification](#nft-verification)
5. [DNS Domain Verification](#dns-domain-verification)
6. [Reputation System](#reputation-system)
7. [X402 Payment Protocol](#x402-payment-protocol)
8. [AI Email Categorization](#ai-email-categorization)
9. [Gateway Encryption](#gateway-encryption)
10. [Consent & Pay-to-Send](#consent-pay-to-send)
11. [Database Schema](#database-schema)
12. [Remaining Work](#remaining-work)
13. [Deployment](#deployment)

---

## Overview

Privra is a privacy-first email server with:
- **Zero-knowledge encryption**
- **Solana NFT verification** (like Gmail's checkmark but decentralized)
- **Reputation-based trust system**
- **AI-powered categorization**
- **Economic spam prevention** (X402 micropayments)
- **Gateway encryption** for external emails

---

## Implemented Features

### ✅ Core Mail Server
- Postfix SMTP server
- Dovecot IMAP server
- DKIM signing (dynamic configuration)
- SPF & DMARC support
- SSL/TLS with Let's Encrypt
- PostgreSQL database
- Redis session storage

### ✅ Phase 3.3: Gateway Encryption
- **Incoming**: Encrypt external emails with recipient's public key
- **Outgoing**: Decrypt emails to external recipients
- **Internal**: End-to-end encrypted Privra-to-Privra
- **Filters**: `encrypt_filter.py`, `decrypt_filter.py`
- **Crypto**: RSA-2048 with OAEP padding

### ✅ Phase 4: AI Intelligence
- Background categorization service
- 5 categories: Priority, Social, Updates, Promotions, Spam, Inbox
- Rule-based matching (LLM-ready architecture)
- Real-time processing (60-second intervals)
- Database: `email_categories` table

### ✅ Phase 5: Pay-to-Send & Consent
- Consent system with whitelist/blacklist
- X402 payment protocol (Solana + Base mainnet)
- Lightning payment support
- Admin UI for consent management
- Policy service: `consent_policy.py`

### ✅ User Profile System ⭐ NEW
- Display name, bio, avatar
- Individual OR organization profiles
- Social links (Twitter, GitHub, LinkedIn)
- Wallet management (multiple Solana wallets)
- Modern anime-inspired UI

### ✅ NFT Verification ⭐ NEW
- **NFT = Profile Picture** (like Gmail but decentralized)
- Solana NFT ownership verification
- NFT image becomes user avatar
- Reputation metadata sync
- Verification badge in emails

### ✅ DNS Domain Verification ⭐ NEW
- TXT record verification (`privra-verify=<token>`)
- Automatic token generation
- Domain ownership proof
- Organization verification

### ✅ Reputation System ⭐ NEW
- 5 levels: New, Trusted, Verified, Elite, Legendary
- Automatic scoring from email behavior
- Trust percentage (0-100%)
- Event tracking and audit trail
- NFT metadata sync

---

## User Profile System

### Profile Types

**Individual Profile**:
```
{
  "display_name": "John Doe",
  "bio": "Software developer & privacy advocate",
  "avatar_url": "https://arweave.net/nft-image",
  "profile_type": "individual",
  "social_links": {
    "twitter": "@johndoe",
    "github": "johndoe",
    "website": "https://johndoe.com"
  }
}
```

**Organization Profile**:
```
{
  "org_name": "Acme Corp",
  "org_type": "Technology",
  "industry": "Software",
  "verified_domain": "acme.com",
  "domain_verified": true,
  "logo_url": "https://acme.com/logo.png"
}
```

### Database Tables

**user_profiles**:
- Display name, bio, avatar URL
- Profile type (individual/organization)
- Organization details (name, domain, website)
- Social links (Twitter, GitHub, LinkedIn)
- Verification status and method
- NFT badge mint address
- Reputation score

**organization_profiles**:
- Organization name, type, industry
- Employee count, founding year
- Logo and banner images
- Verified domain
- NFT badge mint
- Reputation score

### UI Design

**Modern Anime Aesthetic**:
- Gradient backgrounds (#667eea to #764ba2)
- Smooth animations (slide-up, fade-in)
- Glass morphism effects
- Colored reputation badges
- SF Pro Display typography
- Mobile-first responsive design
- Avatar with verified badge overlay

**Profile Card**:
- Banner with gradient overlay
- Circular avatar (120px)
- Display name and email
- Reputation level badge
- Stats grid (score, wallets, verified status)
- Profile information form
- Wallet management section
- NFT verification section

---

## NFT Verification

### Simplified Flow (Like Gmail Profile Picture)

1. **User Connects Wallet**
   - Add Solana wallet address
   - Multiple wallets supported
   - Mark one as primary

2. **User Sets NFT as Avatar**
   - Provide NFT mint address
   - System verifies ownership on Solana
   - **NFT image becomes profile picture**
   - No separate "verification badge"

3. **Reputation Syncs to NFT**
   - NFT metadata updated with reputation score
   - On-chain reputation tracking
   - Decentralized trust

### Service: `nft_verification_service.py`

**Key Functions**:

```python
# Set NFT image as user avatar
set_nft_as_avatar(user_email, nft_mint, wallet_address)
  → Verifies ownership
  → Fetches NFT metadata
  → Sets NFT image as avatar_url
  → Grants +50 reputation points

# Update NFT with reputation
update_nft_reputation(user_email)
  → Gets current reputation score
  → Updates NFT metadata on-chain
  → Syncs reputation level
```

### Database Tables

**user_wallets**:
- User email
- Wallet address (Solana mainnet)
- Wallet type (solana/ethereum)
- Primary wallet flag
- Verification status

**nft_verifications**:
- NFT mint address
- NFT name, symbol, image URL
- Verification type
- Reputation level and score
- Metadata URI
- Active status

### How It Shows in Emails

```
From: john@example.com
Avatar: [NFT Image]
"This sender's profile is verified via Solana NFT"
Reputation: Elite (2,450 points)
```

---

## DNS Domain Verification

### How It Works

1. **Generate Token**
   ```python
   token = nft_verification_service.generate_domain_verification_token(
       user_email="admin@acme.com",
       domain="acme.com"
   )
   # Returns: "a3f2b9c1e5d8..."
   ```

2. **Add TXT Record**
   ```
   Type: TXT
   Name: @
   Value: privra-verify=a3f2b9c1e5d8...
   ```

3. **Verify Domain**
   ```python
   verified, message = nft_verification_service.verify_domain_ownership(
       user_email="admin@acme.com",
       domain="acme.com"
   )
   # Checks DNS TXT records
   # Marks domain as verified
   # Grants +100 reputation points
   ```

### Service Functions

**DNS Library**: `dnspython==2.4.2`

```python
# Generate verification token
generate_domain_verification_token(user_email, domain)
  → Generates SHA256 token
  → Stores in domain_verifications table
  → Returns token for DNS record

# Verify domain ownership
verify_domain_ownership(user_email, domain)
  → Queries DNS TXT records
  → Checks for privra-verify=<token>
  → Marks domain as verified
  → Updates user profile
  → Records reputation event
```

### Database Table

**domain_verifications**:
- User email
- Domain name
- Verification token (SHA256 hash)
- Verified boolean
- Created timestamp
- Verified timestamp

### Organization Verification

For organizations:
```python
# 1. Create organization profile
profile_type = "organization"
organization_name = "Acme Corp"
organization_domain = "acme.com"

# 2. Generate verification token
token = generate_domain_verification_token(email, "acme.com")

# 3. Add DNS TXT record
# acme.com TXT "privra-verify=<token>"

# 4. Verify
verified = verify_domain_ownership(email, "acme.com")

# 5. Result:
# - organization_profiles.domain_verified = TRUE
# - Shows "✓ Verified Domain: acme.com" in emails
```

---

## Reputation System

### Reputation Levels

| Level | Points | Badge Color | Benefits |
|-------|--------|-------------|----------|
| **New** | 0-100 | Gray | Basic sender |
| **Trusted** | 100-500 | Blue | Bypass some spam filters |
| **Verified** | 500-1,000 | Green | Domain/NFT verified |
| **Elite** | 1,000-5,000 | Orange | Priority inbox |
| **Legendary** | 5,000+ | Pink/Purple | VIP treatment |

### Scoring Events

**Positive**:
- Email sent: +1
- Email received: +1
- Payment made: +10
- Domain verified: +100
- NFT verified: +50
- Positive interaction: +5
- Whitelisted: +3

**Negative**:
- Spam report: -20
- Payment failed: -5
- Blacklisted: -10
- Negative interaction: -3

### Service: `reputation_service.py`

**Key Functions**:

```python
# Record reputation event
record_event(
    user_email,
    event_type,      # e.g., 'email_sent', 'spam_report'
    event_category,  # e.g., 'email', 'verification'
    description,
    metadata
)

# Get reputation data
reputation = get_reputation(user_email)
# Returns: {
#   'total_score': 1250,
#   'reputation_level': 'elite',
#   'spam_reports': 0,
#   'positive_interactions': 45,
#   'emails_sent': 320,
#   'emails_received': 450
# }

# Calculate trust percentage
trust = calculate_trust_percentage(user_email)
# Returns: 85 (out of 100)
```

### Database Tables

**reputation_scores**:
- Total score
- Category scores (email, verification, payment, trust)
- Spam reports
- Positive/negative interactions
- Email counts
- Reputation level
- NFT sync status

**reputation_events**:
- Event type and category
- Score change
- Description
- Metadata (JSONB)
- Timestamp

### Trust Percentage Algorithm

```
Base Trust = min(70%, (total_score / 1000) * 70%)
Verification Bonus = min(20%, (verification_score / 100) * 20%)
Spam Penalty = min(30%, spam_reports * 10%)
Interaction Bonus = (positive / total) * 10%

Trust % = Base + Verification + Interaction - Spam
```

---

## X402 Payment Protocol

### Networks (Mainnet Only)

- **Solana Mainnet**: USDC SPL token
- **Base Mainnet**: USDC ERC-20
- Default: `solana-mainnet`
- Default amount: `$0.01 USDC`

### Payment Flow

1. **Email Blocked**: Unknown sender to user with payment enabled
2. **402 Response**: SMTP returns payment URL
3. **Payment Page**: Sender visits URL or AI agent makes request
4. **Pay**: Send USDC on Solana or Base
5. **Verify**: Submit transaction hash
6. **Delivered**: Email released, sender whitelisted

### Service: `x402_service.py`

**Generate Payment Request**:
```python
payment_request = x402_service.generate_payment_request(
    sender_email="ai@agent.com",
    recipient_email="user@privra.xyz",
    consent_request_id=123,
    network="solana-mainnet",
    amount_usdc="0.01"
)
# Returns payment URL and requirement JSON
```

### Configuration

```bash
# .env
X402_SOLANA_ADDRESS=your-solana-wallet
X402_BASE_ADDRESS=your-evm-wallet
X402_DEFAULT_AMOUNT_USDC=0.01
X402_DEFAULT_NETWORK=solana-mainnet
```

---

## AI Email Categorization

### Categories

- 📌 **Priority**: Urgent, important, deadlines
- 👥 **Social**: Social media, mentions, tags
- 📰 **Updates**: Newsletters, notifications, alerts
- 🏷️ **Promotions**: Sales, discounts, offers
- 🚫 **Spam**: Unwanted, suspicious content
- 📥 **Inbox**: Default

### Service: `categorization_service.py`

Runs in background via supervisord:
- Checks every 60 seconds
- Processes last 100 emails per user
- Stores in `email_categories` table
- LLM-ready architecture

---

## Gateway Encryption

### How It Works

**Incoming (External → Privra)**:
```
1. External sender → Privra user
2. encrypt_filter.py intercepts
3. Lookup recipient's public key
4. Encrypt email body with RSA-2048
5. Add X-Privra-Encrypted header
6. Deliver to mailbox
```

**Outgoing (Privra → External)**:
```
1. Privra user → External recipient
2. decrypt_filter.py intercepts
3. Check if recipient is external
4. Decrypt with sender's private key
5. Remove encryption headers
6. Send plaintext to external
```

**Internal (Privra → Privra)**:
```
1. Encrypted in sender's browser
2. Server never sees plaintext
3. Decrypted in recipient's browser
4. True end-to-end encryption
```

---

## Consent & Pay-to-Send

### Admin Panel UI

**Per-User Settings**:
- ✅ Require consent
- ✅ Require payment
- ✅ Whitelist mode
- 💰 Payment amount (sats or USDC)

**Whitelist/Blacklist**:
- Add by email or domain
- Automatic management
- Shows in consent UI

### Policy Service: `consent_policy.py`

Postfix policy server that:
- Checks sender permissions
- Generates X402 payment requests
- Manages whitelist/blacklist
- Tracks consent requests

---

## Database Schema

### User Management
- `users` - Email accounts
- `domains` - Virtual domains
- `admin_users` - Admin accounts

### Profiles & Verification
- `user_profiles` - Extended user info
- `organization_profiles` - Organization details
- `user_wallets` - Solana wallet addresses
- `nft_verifications` - NFT badges
- `domain_verifications` - DNS TXT verification

### Reputation
- `reputation_scores` - Score tracking
- `reputation_events` - Audit trail

### Consent & Payments
- `consent_settings` - User preferences
- `sender_whitelist` - Approved senders
- `sender_blacklist` - Blocked senders
- `consent_requests` - Pending requests
- `payment_transactions` - Payment history
- `x402_payment_requests` - X402 payments

### Email Features
- `email_categories` - AI categorization

**Total**: 17 tables

---

## Remaining Work

### 🚧 To Implement

#### 1. **Solana RPC Blockchain Verification**
**File**: `postfix/nft_verification_service.py`

**Current**: Placeholder verification (always succeeds)

**Needed**:
```python
def verify_nft_ownership(user_email, nft_mint, wallet_address):
    # TODO: Implement actual Solana RPC call
    # 1. Query Solana for token accounts
    # 2. Verify wallet owns NFT with mint address
    # 3. Check NFT is from verified collection
    # 4. Return actual verification result

    # Use: @solana/web3.js or solana-py
    # RPC: https://api.mainnet-beta.solana.com
```

**Resources**:
- Solana Web3.js: https://solana-labs.github.io/solana-web3.js/
- Python SDK: https://github.com/michaelhly/solana-py
- Metaplex: Token metadata standard

#### 2. **NFT Metadata On-Chain Updates**
**File**: `postfix/nft_verification_service.py`

**Current**: Updates local database only

**Needed**:
```python
def update_nft_reputation(user_email):
    # TODO: Build Solana transaction to update NFT metadata
    # 1. Fetch current NFT metadata account
    # 2. Build update instruction
    # 3. Sign with authorized key
    # 4. Send transaction to network
    # 5. Wait for confirmation

    # Requires: Update authority key
```

**Challenge**: Need update authority for NFT metadata

#### 3. **Web3 Wallet Connect Integration**
**Needed**: Frontend wallet connection

```javascript
// TODO: Add to webmail
import { WalletAdapterNetwork } from '@solana/wallet-adapter-base';
import { PhantomWalletAdapter } from '@solana/wallet-adapter-phantom';

// User clicks "Connect Wallet"
// → Phantom/Solflare popup
// → Get wallet address
// → Verify signature
// → Store in database
```

**Libraries**:
- @solana/wallet-adapter-react
- @solana/wallet-adapter-wallets

#### 4. **X402 Payment Verification**
**File**: `postfix/x402_service.py`

**Current**: Accepts payment proof, logs txid, marks paid

**Needed**:
```python
def _verify_solana_payment(payment_data, network, expected_amount):
    # TODO: Verify actual blockchain transaction
    # 1. Parse transaction signature from payment_data
    # 2. Query Solana RPC for transaction
    # 3. Verify USDC SPL transfer
    # 4. Check amount matches expected
    # 5. Verify recipient address
    # 6. Return verified txid

def _verify_evm_payment(payment_data, network, expected_amount):
    # TODO: Verify EVM transaction
    # 1. Parse transaction hash
    # 2. Query Base RPC
    # 3. Verify USDC ERC-20 transfer
    # 4. Check amount and recipient
    # 5. Return verified txid
```

#### 5. **User Profile Routes in Webmail**
**File**: `webmail/app.py`

**Status**: Template created, routes not added yet

**Action**: Copy routes from `IMPLEMENTATION_GUIDE_PROFILES_NFT.md` lines 54-125

**Routes to Add**:
- `GET /profile` - Profile page
- `POST /profile` - Update profile
- `POST /profile/wallet/add` - Add wallet
- `POST /profile/verify-nft` - Set NFT as avatar
- `POST /profile/verify-domain` - Domain verification

#### 6. **Email Badge Display**
**Needed**: Show verification badge in email headers

```html
<!-- In webmail email view -->
<div class="email-sender">
  <img src="{{ sender_avatar }}" class="avatar">
  <div>
    <strong>{{ sender_name }}</strong>
    {% if sender_verified %}
      <span class="verified-badge">✓ Verified</span>
    {% endif %}
    <div class="reputation-level">{{ reputation_level }}</div>
  </div>
</div>
```

**Add to**: `webmail/app.py` - inbox view

#### 7. **Admin Dashboard Enhancements**
**Suggested Features**:
- 📊 System overview (total users, emails, reputation avg)
- 📈 Reputation distribution chart
- 🔍 User search and management
- 🎨 NFT verification management
- ⚙️ Manual reputation adjustments
- 📧 Email analytics

---

## Deployment

### 1. Database Migration

```bash
# Restart admin to create new tables
docker-compose restart admin

# Tables created automatically:
# - user_profiles
# - organization_profiles
# - user_wallets
# - nft_verifications
# - reputation_scores
# - reputation_events
# - domain_verifications
```

### 2. Add Profile Routes

```bash
# Copy from IMPLEMENTATION_GUIDE_PROFILES_NFT.md
# Add to webmail/app.py before if __name__ == '__main__':
```

### 3. Update Requirements

```bash
# Already updated:
# - webmail/requirements.txt: dnspython, requests
```

### 4. Configure Environment

```bash
# Update .env
X402_DEFAULT_NETWORK=solana-mainnet
X402_SOLANA_ADDRESS=your-wallet
X402_BASE_ADDRESS=your-wallet
PRIVRA_NFT_COLLECTION=your-collection
```

### 5. Rebuild & Deploy

```bash
docker-compose up -d --build

# Verify services:
docker-compose ps
docker-compose logs -f webmail
```

---

## Architecture Decisions

### Why NFT = Avatar?
- **Simpler UX**: One step instead of two
- **Clear ownership**: NFT image directly represents user
- **Like Gmail**: Familiar pattern for users
- **Flexible**: Can change NFT anytime

### Why DNS TXT Verification?
- **Industry standard**: Same as Google, Microsoft
- **Decentralized**: No central authority needed
- **Automated**: Easy to verify programmatically
- **Flexible**: Works for any domain

### Why Reputation On-Chain?
- **Portable**: Reputation tied to NFT, not server
- **Verifiable**: Anyone can check on-chain
- **Permanent**: Survives server migration
- **Privacy**: No PII in metadata, just scores

### Why Mainnet Only?
- **Production ready**: No test transactions
- **Real value**: Actual USDC payments
- **Trust**: Users know it's real
- **Simpler**: Less configuration options

---

## Support & Resources

- **Docs**: `/docs/` directory
- **Issues**: GitHub Issues
- **PortID**: https://github.com/Harboria-Labs/portid
- **X402**: https://x402.org
- **Solana**: https://solana.com

---

**Built with privacy, owned by you.** 🔐
