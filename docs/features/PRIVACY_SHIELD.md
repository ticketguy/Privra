# PRIORITY 1: PRIVACY SHIELD

**Timeline:** 6 weeks
**Goal:** Make Privra the most private email on the market
**Deliverable:** v1.0 MVP (revenue-ready)

---

## Feature 1: Dynamic Shield Aliasing

### Overview
Generate unlimited email aliases (`netflix.user@privra.xyz`) to isolate identity across services. Track which services leak/sell your data.

### User Stories
1. **As a privacy-conscious user**, I want to generate a unique email for each service, so that I can identify who leaked my data.
2. **As a user**, I want to see which aliases are actively receiving mail, so that I know which services are still contacting me.
3. **As a user**, I want to copy an alias to my clipboard quickly, so that I can use it during signup flows.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE email_aliases (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    alias VARCHAR(255) UNIQUE NOT NULL,
    service_name VARCHAR(255),  -- User-provided label
    description TEXT,  -- Optional notes
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,  -- Updated when email received
    email_count INT DEFAULT 0,  -- How many emails received
    is_active BOOLEAN DEFAULT TRUE,
    burned_at TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX idx_aliases_lookup ON email_aliases(alias) WHERE is_active = TRUE;
CREATE INDEX idx_aliases_user ON email_aliases(user_email);
```

#### Postfix Integration
```conf
# /etc/postfix/main.cf
virtual_alias_maps = pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# /etc/postfix/pgsql-virtual-alias-maps.cf
hosts = localhost
user = postfix_query
password = ***
dbname = privra_dockyard
query = SELECT user_email FROM email_aliases
        WHERE alias='%s' AND is_active=TRUE
        LIMIT 1
```

#### Backend Service
```python
# alias_service.py
import secrets
import string
import psycopg2
from typing import Optional

class AliasService:
    def generate_alias(self, user_email: str, service_name: str,
                       custom_prefix: Optional[str] = None) -> dict:
        """
        Generate a new email alias.

        Args:
            user_email: User's primary email
            service_name: Name of service (e.g., "Netflix")
            custom_prefix: Optional custom prefix (default: random)

        Returns:
            {
                "alias": "netflix.user@privra.xyz",
                "service_name": "Netflix",
                "created_at": "2025-11-18T..."
            }
        """
        # Extract username from user_email
        username = user_email.split('@')[0]

        # Generate alias
        if custom_prefix:
            prefix = custom_prefix.lower().replace(' ', '-')
        else:
            # Use service name + random suffix
            safe_service = service_name.lower().replace(' ', '-')[:20]
            random_suffix = ''.join(secrets.choice(string.ascii_lowercase)
                                   for _ in range(4))
            prefix = f"{safe_service}.{random_suffix}"

        alias = f"{prefix}.{username}@privra.xyz"

        # Check uniqueness
        if self._alias_exists(alias):
            # Collision: add random suffix
            alias = f"{prefix}.{secrets.token_hex(3)}.{username}@privra.xyz"

        # Insert into database
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO email_aliases (user_email, alias, service_name)
            VALUES (%s, %s, %s)
            RETURNING id, alias, created_at
        """, (user_email, alias, service_name))

        result = cur.fetchone()
        conn.commit()

        return {
            "id": result[0],
            "alias": result[1],
            "service_name": service_name,
            "created_at": result[2].isoformat()
        }

    def list_aliases(self, user_email: str, include_burned: bool = False) -> list:
        """Get all aliases for a user"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT id, alias, service_name, created_at,
                   last_used, email_count, is_active, burned_at
            FROM email_aliases
            WHERE user_email = %s
        """

        if not include_burned:
            query += " AND burned_at IS NULL"

        query += " ORDER BY created_at DESC"

        cur.execute(query, (user_email,))
        rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "alias": row[1],
                "service_name": row[2],
                "created_at": row[3].isoformat(),
                "last_used": row[4].isoformat() if row[4] else None,
                "email_count": row[5],
                "is_active": row[6],
                "burned_at": row[7].isoformat() if row[7] else None
            }
            for row in rows
        ]

    def update_alias_stats(self, alias: str):
        """Called by Postfix when email arrives"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE email_aliases
            SET last_used = NOW(),
                email_count = email_count + 1
            WHERE alias = %s
        """, (alias,))

        conn.commit()

    def _alias_exists(self, alias: str) -> bool:
        conn = self._get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM email_aliases WHERE alias = %s", (alias,))
        return cur.fetchone() is not None

alias_service = AliasService()
```

#### Flask Routes
```python
# webmail/app.py

@app.route('/aliases')
def aliases():
    """Alias management page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    aliases = alias_service.list_aliases(user_email)

    return render_template('aliases.html', aliases=aliases)


@app.route('/aliases/generate', methods=['POST'])
def generate_alias():
    """Generate a new alias"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']
    service_name = request.json.get('service_name', 'Unknown Service')
    custom_prefix = request.json.get('custom_prefix')

    try:
        result = alias_service.generate_alias(user_email, service_name, custom_prefix)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/aliases/<int:alias_id>', methods=['DELETE'])
def delete_alias(alias_id):
    """Delete an alias (different from burning)"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Implementation
    pass
```

#### UI Template
```html
<!-- webmail/templates/aliases.html -->
{% extends "base.html" %}

{% block content %}
<div class="aliases-container">
    <div class="aliases-header">
        <h1>Shield Aliases</h1>
        <p>Generate unique emails for each service. Track who leaks your data.</p>
        <button class="btn-primary" onclick="showGenerateModal()">
            + Generate New Alias
        </button>
    </div>

    <!-- Generate Modal -->
    <div id="generateModal" class="modal">
        <div class="modal-content glass-card">
            <h2>Generate Shield Alias</h2>
            <form id="generateForm">
                <div class="form-group">
                    <label>Service Name</label>
                    <input type="text" id="serviceName"
                           placeholder="e.g., Netflix, Amazon, LinkedIn"
                           required>
                </div>
                <div class="form-group">
                    <label>Custom Prefix (optional)</label>
                    <input type="text" id="customPrefix"
                           placeholder="e.g., my-custom-alias">
                    <small>Leave blank for auto-generated</small>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Generate</button>
                    <button type="button" class="btn-secondary"
                            onclick="closeGenerateModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Alias List -->
    <div class="alias-list">
        {% for alias in aliases %}
        <div class="alias-card">
            <div class="alias-info">
                <div class="alias-email">
                    {{ alias.alias }}
                    <button class="btn-copy"
                            onclick="copyToClipboard('{{ alias.alias }}')">
                        📋 Copy
                    </button>
                </div>
                <div class="alias-meta">
                    <span class="service-name">{{ alias.service_name }}</span>
                    <span class="email-count">{{ alias.email_count }} emails</span>
                    {% if alias.last_used %}
                    <span class="last-used">Last used: {{ alias.last_used }}</span>
                    {% endif %}
                </div>
            </div>
            <div class="alias-actions">
                <button class="btn-danger"
                        onclick="burnAlias({{ alias.id }})">
                    🔥 Burn Alias
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<script>
function showGenerateModal() {
    document.getElementById('generateModal').style.display = 'flex';
}

function closeGenerateModal() {
    document.getElementById('generateModal').style.display = 'none';
}

document.getElementById('generateForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const serviceName = document.getElementById('serviceName').value;
    const customPrefix = document.getElementById('customPrefix').value;

    const response = await fetch('/aliases/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ service_name: serviceName, custom_prefix: customPrefix })
    });

    const result = await response.json();

    if (response.ok) {
        alert(`Alias created: ${result.alias}`);
        location.reload();
    } else {
        alert(`Error: ${result.error}`);
    }
});

function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
}
</script>
{% endblock %}
```

### Postfix Hook (Update Stats)
```python
# scripts/postfix_delivery_hook.py
# Called by Postfix after successful delivery

import sys
from alias_service import alias_service

def main():
    recipient = sys.argv[1]  # The alias that received email
    alias_service.update_alias_stats(recipient)

if __name__ == '__main__':
    main()
```

### Testing Checklist
- [ ] Generate alias with auto-generated prefix
- [ ] Generate alias with custom prefix
- [ ] Verify alias routes email to user
- [ ] Verify last_used updates on email receipt
- [ ] Verify email_count increments
- [ ] Verify uniqueness (no collisions)
- [ ] Copy to clipboard works
- [ ] UI responsive on mobile

---

## Feature 2: The Kill Switch

### Overview
One-click "Burn Alias" button. Sender immediately receives `550 User Unknown`. Irreversible.

### User Stories
1. **As a user**, I want to burn an alias instantly, so that spammers get hard bounces.
2. **As a user**, I want confirmation before burning, so that I don't accidentally delete important aliases.
3. **As a user**, I want to see burned aliases in a separate view, so that I can audit my actions.

### Technical Implementation

#### Backend Service
```python
# alias_service.py (add to existing)

def burn_alias(self, alias_id: int, user_email: str) -> bool:
    """
    Burn an alias. Irreversible. Sender gets 550 error.

    Returns:
        True if burned successfully, False if not found/unauthorized
    """
    conn = self._get_db_connection()
    cur = conn.cursor()

    # Verify ownership
    cur.execute("""
        UPDATE email_aliases
        SET is_active = FALSE,
            burned_at = NOW()
        WHERE id = %s AND user_email = %s AND burned_at IS NULL
        RETURNING alias
    """, (alias_id, user_email))

    result = cur.fetchone()

    if result:
        conn.commit()
        burned_alias = result[0]
        print(f"🔥 Burned alias: {burned_alias}")
        return True
    else:
        return False
```

#### Flask Route
```python
@app.route('/aliases/<int:alias_id>/burn', methods=['POST'])
def burn_alias(alias_id):
    """Burn an alias (irreversible)"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']
    success = alias_service.burn_alias(alias_id, user_email)

    if success:
        flash('Alias burned. Senders will now receive 550 errors.', 'success')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Alias not found or already burned'}), 404
```

#### UI Enhancement
```html
<!-- Add to aliases.html -->
<script>
function burnAlias(aliasId) {
    if (!confirm('⚠️ This is IRREVERSIBLE. Senders will get "User Unknown" errors. Continue?')) {
        return;
    }

    fetch(`/aliases/${aliasId}/burn`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('🔥 Alias burned successfully.');
            location.reload();
        } else {
            alert(`Error: ${data.error}`);
        }
    });
}
</script>
```

#### Postfix Behavior
When alias is burned (`is_active = FALSE`), Postfix query returns NULL:
```
550 5.1.1 <burned-alias@privra.xyz>: Recipient address rejected: User unknown in virtual alias table
```

### Testing Checklist
- [ ] Burn alias → immediate 550 error
- [ ] Cannot burn already-burned alias
- [ ] Cannot burn another user's alias
- [ ] Confirmation modal appears
- [ ] Burned aliases shown in separate section

---

## Feature 3: Active Sanitization

### Overview
Strip tracking pixels, rewrite suspicious links through safe proxy before rendering email.

### User Stories
1. **As a user**, I want tracking pixels removed, so that marketers can't track when I read emails.
2. **As a user**, I want suspicious links rewritten, so that I'm protected from phishing.
3. **As a user**, I want to see which sanitizations were applied, so that I know the system is working.

### Technical Implementation

#### Backend Service
```python
# email_sanitizer.py
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

class EmailSanitizer:
    TRACKING_PIXEL_PATTERNS = [
        r'width=["\']?1["\']?.*height=["\']?1["\']?',
        r'height=["\']?1["\']?.*width=["\']?1["\']?',
        r'\.gif\?.*campaign',
        r'tracking\..*\.png',
        r'open\..*\.jpg'
    ]

    SUSPICIOUS_DOMAINS = [
        'bit.ly', 'tinyurl.com', 'goo.gl', 't.co',
        'ow.ly', 'buff.ly', 'is.gd'
    ]

    def sanitize_html(self, html_content: str, user_email: str) -> dict:
        """
        Sanitize email HTML.

        Returns:
            {
                "sanitized_html": str,
                "removed_pixels": int,
                "rewritten_links": int,
                "warnings": list
            }
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        removed_pixels = 0
        rewritten_links = 0
        warnings = []

        # Remove tracking pixels
        for img in soup.find_all('img'):
            if self._is_tracking_pixel(img):
                img.decompose()
                removed_pixels += 1

        # Rewrite suspicious links
        for link in soup.find_all('a'):
            href = link.get('href', '')

            if self._is_suspicious_link(href):
                safe_url = f"https://click.privra.xyz/safe?url={quote(href)}&user={user_email}"
                link['href'] = safe_url
                link['data-original-url'] = href
                link['class'] = link.get('class', []) + ['sanitized-link']
                rewritten_links += 1
                warnings.append(f"Suspicious link: {href}")

        # Remove external stylesheets (can be used for tracking)
        for style_link in soup.find_all('link', rel='stylesheet'):
            if 'http' in style_link.get('href', ''):
                style_link.decompose()

        return {
            "sanitized_html": str(soup),
            "removed_pixels": removed_pixels,
            "rewritten_links": rewritten_links,
            "warnings": warnings
        }

    def _is_tracking_pixel(self, img_tag) -> bool:
        """Detect 1x1 tracking images"""
        width = img_tag.get('width', '')
        height = img_tag.get('height', '')
        src = img_tag.get('src', '')

        # 1x1 dimensions
        if (width in ['1', '0'] and height in ['1', '0']):
            return True

        # Pattern matching
        for pattern in self.TRACKING_PIXEL_PATTERNS:
            if re.search(pattern, str(img_tag), re.IGNORECASE):
                return True

        # Suspicious tracking URLs
        if any(keyword in src.lower() for keyword in ['track', 'pixel', 'beacon', 'analytics']):
            return True

        return False

    def _is_suspicious_link(self, url: str) -> bool:
        """Detect phishing/suspicious links"""
        for domain in self.SUSPICIOUS_DOMAINS:
            if domain in url:
                return True

        # Check for URL shorteners
        if len(url) < 30 and 'http' in url:
            return True

        return False

email_sanitizer = EmailSanitizer()
```

#### Integration with Email Display
```python
# webmail/app.py (modify existing get_email_body)

def get_email_body(msg):
    """Extract and sanitize email body"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode(errors='ignore')
                break
            elif part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors='ignore')
    else:
        body = msg.get_payload(decode=True).decode(errors='ignore')

    # Sanitize HTML
    if '<html' in body.lower():
        user_email = session.get('email', '')
        sanitization_result = email_sanitizer.sanitize_html(body, user_email)

        # Store sanitization stats in session for display
        session['last_sanitization'] = {
            'removed_pixels': sanitization_result['removed_pixels'],
            'rewritten_links': sanitization_result['rewritten_links']
        }

        return sanitization_result['sanitized_html']

    return body
```

#### UI Indicator
```html
<!-- Show sanitization badge in email view -->
{% if session.last_sanitization %}
<div class="sanitization-badge">
    🛡️ Protected:
    {{ session.last_sanitization.removed_pixels }} trackers blocked,
    {{ session.last_sanitization.rewritten_links }} links secured
</div>
{% endif %}
```

### Testing Checklist
- [ ] 1x1 images removed
- [ ] Tracking pixels in email signatures removed
- [ ] Bit.ly links rewritten through proxy
- [ ] External stylesheets removed
- [ ] Sanitization stats displayed
- [ ] Original links preserved in data attribute

---

## Feature 4: Gatekeeper Agent (AI Bouncer)

### Overview
AI-powered bouncer that intercepts unknown senders. Challenges suspicious senders, auto-unsubscribes from spam.

### User Stories
1. **As a user**, I want unknown senders to be challenged, so that spammers are blocked automatically.
2. **As a user**, I want to manage my trusted senders, so that I can control who reaches my inbox.
3. **As a user**, I want the system to auto-unsubscribe from spam, so that I don't have to do it manually.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE sender_challenges (
    id SERIAL PRIMARY KEY,
    sender_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    challenge_code VARCHAR(10) NOT NULL,
    challenge_type VARCHAR(50) DEFAULT 'code',  -- 'code', 'captcha', 'question'
    challenge_sent_at TIMESTAMP DEFAULT NOW(),
    challenge_passed BOOLEAN DEFAULT FALSE,
    passed_at TIMESTAMP,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3
);

CREATE TABLE trusted_senders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    sender_email VARCHAR(255) NOT NULL,
    trust_level VARCHAR(20) DEFAULT 'manual',  -- 'auto', 'manual', 'org'
    added_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(50),  -- 'user', 'gatekeeper', 'system'
    UNIQUE(user_email, sender_email)
);

CREATE TABLE quarantined_emails (
    id SERIAL PRIMARY KEY,
    recipient_email VARCHAR(255) REFERENCES users(email),
    sender_email VARCHAR(255),
    subject TEXT,
    body_preview TEXT,
    quarantined_at TIMESTAMP DEFAULT NOW(),
    reason TEXT,
    released_at TIMESTAMP
);
```

#### Gatekeeper Service
```python
# gatekeeper_agent.py
import secrets
import string
from email.mime.text import MIMEText
import smtplib

class GatekeeperAgent:
    def __init__(self):
        self.spam_keywords = [
            'viagra', 'casino', 'lottery', 'prince', 'inheritance',
            'click here', 'act now', 'limited time', 'make money fast'
        ]

    def should_challenge(self, sender_email: str, recipient_email: str,
                         subject: str, body: str) -> tuple[bool, str]:
        """
        Determine if sender should be challenged.

        Returns:
            (should_challenge: bool, reason: str)
        """
        # Check if sender is trusted
        if self._is_trusted(sender_email, recipient_email):
            return (False, "Trusted sender")

        # Check if sender has passed challenge
        if self._has_passed_challenge(sender_email, recipient_email):
            return (False, "Challenge already passed")

        # Check spam indicators
        spam_score = self._calculate_spam_score(subject, body)

        if spam_score > 5:
            return (True, f"Spam score: {spam_score}")

        # Unknown sender → challenge
        return (True, "Unknown sender")

    def send_challenge(self, sender_email: str, recipient_email: str) -> str:
        """
        Send challenge email to sender.

        Returns:
            challenge_code
        """
        challenge_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits)
                                for _ in range(6))

        # Store challenge in database
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO sender_challenges (sender_email, recipient_email, challenge_code)
            VALUES (%s, %s, %s)
        """, (sender_email, recipient_email, challenge_code))

        conn.commit()

        # Send challenge email
        msg = MIMEText(f"""
        Hello,

        You attempted to send an email to {recipient_email}.

        To prove you are human and deliver your message, please reply to this email
        with the following code in the subject line:

        {challenge_code}

        This is a one-time verification. Once verified, your future emails will be delivered automatically.

        If you believe this is an error, please contact support@privra.xyz.

        Best regards,
        Privra Gatekeeper
        """)

        msg['Subject'] = f"[Privra] Verification Required - Code: {challenge_code}"
        msg['From'] = "gatekeeper@privra.xyz"
        msg['To'] = sender_email

        # Send via SMTP
        smtp = smtplib.SMTP('localhost', 25)
        smtp.send_message(msg)
        smtp.quit()

        return challenge_code

    def verify_challenge(self, sender_email: str, recipient_email: str,
                         submitted_code: str) -> bool:
        """Verify challenge response"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, challenge_code, attempts, max_attempts
            FROM sender_challenges
            WHERE sender_email = %s
              AND recipient_email = %s
              AND challenge_passed = FALSE
            ORDER BY challenge_sent_at DESC
            LIMIT 1
        """, (sender_email, recipient_email))

        challenge = cur.fetchone()

        if not challenge:
            return False

        challenge_id, correct_code, attempts, max_attempts = challenge

        # Check if max attempts exceeded
        if attempts >= max_attempts:
            return False

        # Verify code
        if submitted_code.strip().upper() == correct_code.upper():
            # Mark as passed
            cur.execute("""
                UPDATE sender_challenges
                SET challenge_passed = TRUE, passed_at = NOW()
                WHERE id = %s
            """, (challenge_id,))

            # Add to trusted senders
            cur.execute("""
                INSERT INTO trusted_senders (user_email, sender_email, added_by)
                VALUES (%s, %s, 'gatekeeper')
                ON CONFLICT (user_email, sender_email) DO NOTHING
            """, (recipient_email, sender_email))

            conn.commit()
            return True
        else:
            # Increment attempts
            cur.execute("""
                UPDATE sender_challenges
                SET attempts = attempts + 1
                WHERE id = %s
            """, (challenge_id,))

            conn.commit()
            return False

    def _calculate_spam_score(self, subject: str, body: str) -> int:
        """Calculate spam score (0-10)"""
        score = 0
        text = (subject + ' ' + body).lower()

        # Keyword matching
        for keyword in self.spam_keywords:
            if keyword in text:
                score += 2

        # ALL CAPS subject
        if subject.isupper() and len(subject) > 10:
            score += 2

        # Excessive exclamation marks
        if text.count('!') > 3:
            score += 1

        # Suspicious URLs
        if 'bit.ly' in text or 'tinyurl' in text:
            score += 2

        return min(score, 10)

    def _is_trusted(self, sender: str, recipient: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM trusted_senders
            WHERE user_email = %s AND sender_email = %s
        """, (recipient, sender))
        return cur.fetchone() is not None

    def _has_passed_challenge(self, sender: str, recipient: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM sender_challenges
            WHERE sender_email = %s
              AND recipient_email = %s
              AND challenge_passed = TRUE
        """, (sender, recipient))
        return cur.fetchone() is not None

gatekeeper_agent = GatekeeperAgent()
```

#### Postfix Content Filter
```python
# scripts/gatekeeper_daemon.py
# Runs as daemon on port 10025

import asyncore
import smtpd
from email import message_from_bytes

class GatekeeperSMTPServer(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        msg = message_from_bytes(data)

        subject = msg['Subject'] or ''
        body = self._get_body(msg)

        for recipient in rcpttos:
            should_challenge, reason = gatekeeper_agent.should_challenge(
                mailfrom, recipient, subject, body
            )

            if should_challenge:
                print(f"Challenging {mailfrom} → {recipient}: {reason}")
                gatekeeper_agent.send_challenge(mailfrom, recipient)
                # Hold email (don't deliver)
                return '250 OK (held for challenge)'
            else:
                # Forward to Dovecot for delivery
                self._forward_email(mailfrom, recipient, data)

        return '250 OK'

    def _forward_email(self, mailfrom, rcptto, data):
        """Forward to Dovecot for final delivery"""
        smtp = smtplib.SMTP('localhost', 10026)  # Dovecot LMTP
        smtp.sendmail(mailfrom, rcptto, data)
        smtp.quit()

if __name__ == '__main__':
    server = GatekeeperSMTPServer(('127.0.0.1', 10025), None)
    print("Gatekeeper daemon listening on port 10025...")
    asyncore.loop()
```

### Testing Checklist
- [ ] Unknown sender triggered challenge
- [ ] Challenge email sent with code
- [ ] Correct code → email delivered
- [ ] Incorrect code → attempt incremented
- [ ] Max attempts → permanently blocked
- [ ] Trusted senders bypass gatekeeper
- [ ] Spam keywords detected

---

## Implementation Timeline

### Week 1-2: Dynamic Aliasing
- Database schema
- Alias generation service
- Postfix integration
- UI implementation
- Testing

### Week 2: Kill Switch
- Burn alias endpoint
- UI confirmation modal
- Postfix verification
- Testing

### Week 3: Active Sanitization
- Sanitizer service
- Integration with email display
- UI indicators
- Testing

### Week 4-6: Gatekeeper Agent
- Database schema
- Gatekeeper service
- Challenge email templates
- Postfix content filter
- Daemon setup
- Testing

---

## Success Metrics
- [ ] 90%+ of users create at least 1 alias
- [ ] Average 5 aliases per user
- [ ] Alias burn rate: 10-15% (shows feature is used)
- [ ] Tracking pixel removal: 50+ per user per week
- [ ] Gatekeeper blocks 80%+ of spam
- [ ] Challenge pass rate: <10% (most spam fails)

---

**This completes Priority 1: Privacy Shield documentation.**
