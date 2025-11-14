# 🔐 Privra Mail Server

**Privacy-first, encrypted email server with zero-knowledge architecture**

A complete, self-hosted email solution built on Postfix, Dovecot, and modern cryptography.

---

## ✨ Key Features

### Core Mail Server
- **📧 Full Mail Server**: SMTP, IMAP, webmail, admin panel
- **🚀 Plug and Play**: Configure via `.env`, deploy with one command
- **🔐 Security First**: DKIM signing, SPF, DMARC, SSL/TLS

### Phase 3.3: Gateway Encryption
- **🔒 End-to-End Encryption**: Client-side encryption for Privra-to-Privra emails
- **🛡️ Gateway Encryption**: Automatic encryption of incoming external emails
- **🔓 Smart Decryption**: Automatic decryption of outgoing emails to external recipients
- **🔑 Zero-Knowledge Architecture**: Server never sees plaintext of encrypted emails

### Phase 4: AI Intelligence Layer
- **🤖 Automatic Categorization**: AI-powered email classification
- **📁 Smart Folders**: Priority, Social, Updates, Promotions, Spam
- **⚡ Real-time Processing**: Background service categorizes emails as they arrive
- **🎯 Rule-Based AI**: Keyword and pattern matching (LLM integration ready)

### Phase 5: Pay-to-Send Economic Layer
- **💰 Consent System**: Require consent from unknown senders
- **⚡ Lightning Payments**: Micropayments to reach your inbox (Bitcoin satoshis)
- **🤖 X402 Protocol**: HTTP 402 payments for AI agents (Solana & Base)
- **💵 USDC Micropayments**: Gasless payments as low as $0.01
- **✅ Whitelist/Blacklist**: Fine-grained sender control
- **🔒 Whitelist Mode**: Only accept emails from approved senders
- **🌐 Multi-Chain**: Supports Solana and Base (EVM) blockchains

### Advanced Features
- **🆔 PortID Ready**: Optional zero-knowledge authentication integration
- **📊 Admin Dashboard**: Complete user and consent management
- **🔄 Background Services**: Automatic categorization and encryption

---

## 🚀 Quick Start

### Prerequisites

- Linux server (2GB RAM minimum, 4GB recommended)
- Domain name with DNS access
- Ports 25, 80, 443, 587, 993 accessible

### 1. Clone Repository

```bash
git clone https://github.com/ticketguy/Privra.git
cd Privra
git checkout claude/mailserver-docker-setup-011CV39qytFpBVKqnHyJe8nM
```

### 2. Configure

```bash
cp .env.example .env
nano .env
```

Set your domain, passwords, and hostnames.

### 3. Get SSL Certificates

```bash
sudo certbot certonly --standalone \
  -d mail.yourdomain.com \
  -d admin.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Copy to project
sudo mkdir -p ./certs
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/mail.yourdomain.com/privkey.pem ./certs/
sudo chmod 644 ./certs/fullchain.pem
sudo chmod 600 ./certs/privkey.pem
```

### 4. Deploy

```bash
docker compose up -d

# Check logs for DKIM DNS record
docker compose logs postfix | grep "DKIM DNS Record"
```

### 5. Add DKIM DNS Record

Copy the DKIM record from logs and add it to your DNS.

**That's it!** Your encrypted mail server is ready.

---

## 📚 Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment instructions
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and encryption design
- **[Configuration](docs/CONFIGURATION.md)** - All configuration options explained
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[PortID Integration](docs/PORTID.md)** - Zero-knowledge authentication setup
- **[Development History](docs/HISTORY.md)** - Project phases and milestones

---

## 🔐 Security

- **DKIM Signing**: All outgoing emails signed automatically
- **SPF & DMARC**: Anti-spoofing protection
- **TLS/SSL**: All connections encrypted
- **At-Rest Encryption**: Email storage encrypted
- **Client-Side Encryption**: Zero-knowledge E2E encryption
- **Hidden Admin Panel**: Obscured URL for admin interface

---

## 📊 What You Get

### Webmail (`https://mail.yourdomain.com/`)
- Send/receive encrypted emails
- Automatic encryption for Privra-to-Privra emails
- Visual encryption indicators
- Full email management

### Admin Panel (`https://admin.yourdomain.com/warofbest/`)
- Create/manage email accounts
- Automatic encryption key generation
- Consent & pay-to-send management
- Whitelist/blacklist configuration
- User management
- System monitoring

### Mail Server
- SMTP (port 25, 587)
- IMAP (port 993)
- Works with all email clients (iPhone, Thunderbird, etc.)

---

## 🎯 Email Encryption

### Privra → Privra
**🔒 End-to-End Encrypted**
- Encrypted in sender's browser
- Server never sees plaintext
- Decrypted in recipient's browser

### Privra → External (Gmail, etc.)
**📧 Standard Email**
- Compatible with all email providers
- Signed with DKIM
- Works like normal email

### External → Privra
**📨 Received Normally**
- Fully compatible with existing email
- Can be encrypted on receipt (optional gateway encryption)

---

## 🤖 X402 Payment Protocol

### What is X402?

X402 is an internet-native micropayment protocol built by Coinbase that uses **HTTP 402 (Payment Required)** for seamless transactions. Perfect for AI agents and spam prevention.

### How It Works for Email

1. **Unauthorized email arrives** → Consent system checks sender
2. **Payment required** → Returns HTTP 402 with payment details
3. **AI agent pays** → Sends USDC on Solana or Base
4. **Payment verified** → Email automatically delivered
5. **Sender approved** → Future emails pass through free

### Supported Networks

- **Solana Mainnet/Devnet** - USDC SPL token
- **Base Mainnet/Sepolia** - USDC ERC-20
- Gasless transactions (facilitator pays gas)
- Micropayments as low as $0.01

### AI Agent Integration

```javascript
// AI agent sends email
POST smtp://mail.privra.xyz
→ Returns: 402 Payment Required

// Agent receives payment URL
GET https://admin.privra.xyz/x402/pay/token
→ Returns: X402 payment requirement

// Agent pays via X402 protocol
POST /x402/verify/token
Headers: X-PAYMENT: base64(payment_proof)
→ Returns: Payment verified

// Email automatically delivered
```

### Configuration

Set up your payment addresses in `.env`:

```bash
X402_SOLANA_ADDRESS=your-solana-wallet
X402_BASE_ADDRESS=your-evm-wallet
X402_DEFAULT_AMOUNT_USDC=0.01
X402_DEFAULT_NETWORK=base-sepolia
```

Enable in admin panel:
- Navigate to user → Consent Settings
- Enable "Require payment"
- Set payment amount

---

## 🛠️ Tech Stack

- **Postfix** - SMTP server
- **Dovecot** - IMAP server
- **PostgreSQL** - User database
- **Redis** - Session storage
- **Nginx** - Reverse proxy & SSL termination
- **OpenDKIM** - Email signing
- **Python/Flask** - Admin & webmail interfaces
- **WebCrypto API** - Client-side encryption

---

## 📈 Mail-Tester Score

After deployment with proper DNS configuration:

- ✅ **DKIM**: Signed
- ✅ **SPF**: Pass
- ✅ **DMARC**: Pass
- **Score**: **8-10/10**

---

## 🤝 Contributing

This is part of the **Privra** privacy-focused ecosystem built by **Harboria Labs**.

- **Founder**: ticketguy
- **Related Projects**: [PortID](https://github.com/Harboria-Labs/portid)

---

## 📄 License

Open-source and customizable. Built with privacy in mind, owned by you.

---

## 🔗 Quick Links

- [Full Documentation](docs/)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [GitHub Issues](https://github.com/ticketguy/Privra/issues)

**Built with privacy, owned by you. 🔐**
