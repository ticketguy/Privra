# FUTURE FEATURES & ENHANCEMENTS

**Status:** Post-MVP Backlog
**Timeline:** After core priorities (v4.0+)
**Purpose:** Feature requests, nice-to-haves, and polish items

These features are **not** part of the core 22-week roadmap but represent natural evolution paths for Privra after establishing market fit.

---

## 📱 MOBILE APPS

### iOS App
**Goal:** Native iOS experience for Privra

**Features:**
- Native email client (SwiftUI)
- Push notifications for new emails
- Biometric authentication (Face ID/Touch ID)
- Offline mode (sync when online)
- Widget for inbox preview
- Share extension (compose from any app)
- Siri shortcuts

**Technical Stack:**
- Swift + SwiftUI
- CoreData for local storage
- PortID SDK (Swift bindings needed)
- IMAP/SMTP libraries

**Estimated Time:** 8-12 weeks

**Priority:** High (mobile is 60%+ of email usage)

---

### Android App
**Goal:** Native Android experience

**Features:**
- Material Design 3 UI
- Push notifications (Firebase)
- Biometric authentication
- Offline mode
- Home screen widget
- Share intent support
- Android Auto support

**Technical Stack:**
- Kotlin + Jetpack Compose
- Room for local storage
- PortID SDK (Kotlin bindings needed)

**Estimated Time:** 8-12 weeks

**Priority:** High (Android market share)

---

## 🌐 BROWSER EXTENSION

### Chrome/Edge Extension
**Goal:** Compose emails from any website

**Features:**
- Compose modal overlay
- Right-click → "Send to Privra"
- Save webpage as email attachment
- Generate shield alias on any signup form
- Quick inbox preview (popup)
- Badge notification count

**Use Cases:**
- Shopping on Amazon → Generate `amazon.user@privra.xyz` alias
- Reading article → Share via email
- LinkedIn message → Copy to email

**Technical Stack:**
- TypeScript
- Chrome Extension Manifest V3
- WebExtension API (cross-browser)

**Estimated Time:** 4 weeks

**Priority:** Medium-High (conversion funnel: extension → paid user)

---

### Firefox Extension
**Goal:** Same as Chrome, Firefox-compatible

**Estimated Time:** 2 weeks (after Chrome version)

**Priority:** Medium

---

## 📅 CALENDAR INTEGRATION

### Privra Calendar
**Goal:** Built-in calendar like Google Calendar

**Features:**
- Event creation from emails ("Dinner on Friday 7pm" → auto-create event)
- Meeting invites (.ics support)
- Calendar sharing (org-wide)
- Availability checking
- Recurring events
- Reminders/notifications

**Database Schema:**
```sql
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    title VARCHAR(255),
    description TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location VARCHAR(255),
    attendees TEXT[],
    recurrence_rule TEXT,  -- RRULE format
    created_at TIMESTAMP
);
```

**Technical Stack:**
- iCal/CalDAV protocol
- Recurring events: RRULE parser
- UI: FullCalendar.js

**Estimated Time:** 6 weeks

**Priority:** Medium (nice-to-have, not core differentiator)

---

## 👥 CONTACTS MANAGEMENT

### Contact Book
**Goal:** Manage contacts with auto-enrichment

**Features:**
- Auto-create contacts from emails
- Contact enrichment (LinkedIn, company info)
- Tags and custom fields
- Contact notes
- Email history per contact
- Export/import (vCard)
- Contact sharing (org-wide)

**Database Schema:**
```sql
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    contact_email VARCHAR(255) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(255),
    job_title VARCHAR(255),
    phone VARCHAR(50),
    tags TEXT[],
    notes TEXT,
    last_contacted TIMESTAMP,
    created_at TIMESTAMP
);
```

**Estimated Time:** 4 weeks

**Priority:** Medium

---

## 📂 FILE STORAGE (PRIVRA DRIVE)

### Cloud Storage
**Goal:** Encrypted file storage like Google Drive

**Features:**
- File upload/download
- Folder organization
- File sharing (with expiration links)
- End-to-end encryption
- Version history
- Email attachments → auto-save to Drive
- Quota management (5GB free, 100GB paid)

**Technical Stack:**
- S3-compatible storage (DigitalOcean Spaces)
- Client-side encryption (Web Crypto API)
- Chunked upload for large files

**Database Schema:**
```sql
CREATE TABLE drive_files (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    file_name VARCHAR(255),
    file_path TEXT,  -- S3 path
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    encrypted_key TEXT,  -- Encrypted with user's PortID key
    parent_folder_id INT REFERENCES drive_folders(id),
    uploaded_at TIMESTAMP
);
```

**Estimated Time:** 8 weeks

**Priority:** Low (not core to email, huge scope)

---

## 🎥 VIDEO CALLS (PRIVRA MEET)

### Video Conferencing
**Goal:** Privacy-first video calls (like Zoom, but encrypted)

**Features:**
- 1-on-1 and group calls (up to 50 participants)
- End-to-end encryption
- Screen sharing
- Recording (encrypted)
- Virtual backgrounds
- Breakout rooms
- Calendar integration (join from calendar event)

**Technical Stack:**
- WebRTC (peer-to-peer)
- Jitsi Meet (open-source base)
- TURN/STUN servers (DigitalOcean)

**Estimated Time:** 12+ weeks (very complex)

**Priority:** Low (huge engineering effort, competitive market)

---

## 🌍 MULTI-LANGUAGE SUPPORT

### Internationalization (i18n)
**Goal:** Support non-English users

**Languages (Priority Order):**
1. Spanish (LATAM market)
2. French (Europe)
3. German (Europe, B2B)
4. Portuguese (Brazil)
5. Japanese (Asia)
6. Chinese (Asia)

**Implementation:**
- Flask-Babel for backend
- i18next for frontend
- Translation files (JSON)
- Language switcher in settings
- Auto-detect browser language

**Estimated Time:** 4 weeks (initial), 1 week per language

**Priority:** Medium (expands TAM significantly)

---

## 🌙 DARK MODE TOGGLE

### Theme Switching
**Goal:** Dark mode option for UI

**Features:**
- Dark/Light/Auto (system preference)
- Smooth transition animation
- Persist preference in database
- Email rendering in dark mode (CSS filters)

**Implementation:**
- CSS custom properties (variables)
- `prefers-color-scheme` media query
- LocalStorage for quick loading

**Estimated Time:** 1 week

**Priority:** High (easy win, user-requested feature)

---

## ⌨️ KEYBOARD SHORTCUTS

### Power User Shortcuts
**Goal:** Gmail-like keyboard navigation

**Shortcuts:**
- `c` - Compose new email
- `r` - Reply
- `a` - Reply all
- `f` - Forward
- `#` - Delete
- `j` / `k` - Next/previous email
- `x` - Select email
- `*` + `a` - Select all
- `g` + `i` - Go to inbox
- `g` + `s` - Go to sent
- `/` - Search
- `?` - Show shortcuts help

**Implementation:**
- JavaScript event listeners
- Mousetrap.js library
- Shortcuts modal (`?` key)

**Estimated Time:** 3 days

**Priority:** High (power users love this)

---

## 📤 EMAIL SCHEDULING

### Send Later
**Goal:** Schedule emails for future delivery

**Features:**
- "Send at..." date/time picker
- Time zone support
- Cancel scheduled send
- Recurring emails (weekly reports)
- Smart suggestions ("Send Monday 9am")

**Database Schema:**
```sql
CREATE TABLE scheduled_emails (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    recipient TEXT,
    subject TEXT,
    body TEXT,
    scheduled_for TIMESTAMP,
    sent_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    recurrence_rule TEXT,  -- For recurring
    created_at TIMESTAMP
);
```

**Background Job:**
- Cron every minute
- Check `scheduled_emails` where `scheduled_for <= NOW()`
- Send emails
- Mark as sent

**Estimated Time:** 1 week

**Priority:** Medium-High (commonly requested)

---

## ✅ READ RECEIPTS

### Track Email Opens
**Goal:** Know when recipient opens email

**Features:**
- Enable/disable per email
- Tracking pixel (1x1 transparent image)
- Open time + location
- Multiple opens tracking
- Privacy toggle (disable for personal emails)

**Ethical Considerations:**
- **Controversial feature** (conflicts with privacy mission)
- Only enable for business emails?
- Full transparency to users

**Database Schema:**
```sql
CREATE TABLE email_read_receipts (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255),
    sender_email VARCHAR(255),
    recipient_email VARCHAR(255),
    opened_at TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

**Estimated Time:** 3 days

**Priority:** Low (conflicts with privacy ethos)

---

## 📝 EMAIL TEMPLATES

### Canned Responses
**Goal:** Save and reuse common email templates

**Features:**
- Create templates
- Variables ({{name}}, {{company}})
- Categories (Sales, Support, Personal)
- Keyboard shortcut to insert
- Org-wide templates (B2B)
- Template analytics (which are used most)

**Database Schema:**
```sql
CREATE TABLE email_templates (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    org_id INT REFERENCES organizations(id),  -- NULL for personal
    template_name VARCHAR(255),
    subject_template TEXT,
    body_template TEXT,
    category VARCHAR(100),
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP
);
```

**UI:**
- Compose modal → "Insert template" button
- Variables auto-filled from context

**Estimated Time:** 1 week

**Priority:** Medium

---

## ✍️ SIGNATURE MANAGEMENT

### Email Signatures
**Goal:** Professional email signatures

**Features:**
- Rich text editor
- Image upload (company logo)
- Multiple signatures (Work, Personal)
- Auto-select based on sender alias
- HTML export
- Social media links

**Database Schema:**
```sql
CREATE TABLE email_signatures (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email),
    signature_name VARCHAR(100),
    html_content TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);
```

**UI:**
- Settings → Signatures
- WYSIWYG editor (TinyMCE or Quill)

**Estimated Time:** 3 days

**Priority:** High (professional users need this)

---

## 🔍 ADVANCED SEARCH

### Power Search
**Goal:** Google-like search operators

**Features:**
- `from:alice@example.com` - Emails from Alice
- `to:bob@example.com` - Emails to Bob
- `subject:invoice` - Subject contains "invoice"
- `has:attachment` - Has attachments
- `after:2025-01-01` - Date range
- `before:2025-12-31` - Date range
- `is:unread` - Unread only
- `is:starred` - Starred only
- Combine operators: `from:alice has:attachment after:2025-11-01`

**Implementation:**
- Parse search query
- Build PostgreSQL query dynamically
- Full-text search (tsvector)

**Estimated Time:** 1 week

**Priority:** High (power users expect this)

---

## 📊 EMAIL ANALYTICS

### Usage Insights
**Goal:** Track email patterns

**Features:**
- Emails sent/received per day (graph)
- Top senders/recipients
- Response time average
- Email volume by hour (heatmap)
- Most used aliases
- Shield alias leak detection

**UI:**
- Dashboard with charts (Chart.js)
- Export reports (PDF)

**Estimated Time:** 2 weeks

**Priority:** Medium (nice-to-have)

---

## 🔐 TWO-FACTOR AUTHENTICATION (2FA)

### Enhanced Security
**Goal:** Add 2FA to login

**Features:**
- TOTP (Google Authenticator, Authy)
- SMS backup codes
- Recovery codes (download PDF)
- Enforce 2FA for org admins

**Implementation:**
- pyotp library
- QR code generation
- Store 2FA secret encrypted

**Estimated Time:** 1 week

**Priority:** High (security best practice)

---

## 🎨 CUSTOM THEMES

### Personalization
**Goal:** Let users customize UI

**Features:**
- Color scheme picker
- Custom accent colors
- Font size adjustment
- Compact/Comfortable/Cozy density
- Custom CSS (power users)

**Estimated Time:** 1 week

**Priority:** Low (polish)

---

## 📦 BULK OPERATIONS

### Mass Actions
**Goal:** Perform actions on multiple emails

**Features:**
- Select all (with filters)
- Bulk delete
- Bulk mark as read/unread
- Bulk move to folder
- Bulk apply labels
- Bulk export

**Implementation:**
- Checkbox selection
- Action bar when items selected
- PostgreSQL batch updates

**Estimated Time:** 3 days

**Priority:** Medium-High

---

## 🔔 SMART NOTIFICATIONS

### Intelligent Alerts
**Goal:** Only notify for important emails

**Features:**
- AI determines importance
- VIP senders (always notify)
- Quiet hours (9pm - 8am)
- Digest mode (summary at 9am)
- Desktop notifications (Web Push API)
- Email notifications (yes, email about email!)

**Estimated Time:** 1 week

**Priority:** Medium

---

## 💳 BILLING & SUBSCRIPTIONS

### Payment Management
**Goal:** Self-service billing

**Features:**
- Stripe integration
- Credit card management
- Invoices/receipts
- Usage-based billing (for orgs)
- Annual discount (20% off)
- Referral credits

**Estimated Time:** 2 weeks

**Priority:** Critical before launch

---

## 📖 USER ONBOARDING

### First-Time User Experience
**Goal:** Smooth onboarding

**Features:**
- Welcome wizard (5 steps)
- Sample emails with tutorials
- Video tutorials
- Interactive tooltips (Intro.js)
- Checklist (5 tasks to get started)

**Estimated Time:** 1 week

**Priority:** High (reduces churn)

---

## 🤝 INTEGRATIONS

### Third-Party Integrations
**Goal:** Connect to other tools

**Priority List:**
1. **Slack** - Email → Slack channel
2. **Zapier** - 1000+ app integrations
3. **Make (Integromat)** - Visual automation
4. **Notion** - Save emails as Notion pages
5. **Google Workspace** - Import contacts/calendar
6. **Microsoft 365** - Import from Outlook
7. **Salesforce** - CRM integration
8. **HubSpot** - Marketing automation
9. **Stripe** - Payment notifications
10. **GitHub** - Issue notifications

**Implementation:**
- Webhooks API
- OAuth for third-party auth
- Zapier/Make templates

**Estimated Time:** 2 weeks per integration

**Priority:** High (Zapier especially)

---

## 🎯 PRIORITIZATION FRAMEWORK

### How to Decide What to Build Next

After completing the core roadmap (22 weeks), use this framework:

**Impact × Ease Matrix:**

| Feature | Impact (1-10) | Ease (1-10) | Score | Priority |
|---------|---------------|-------------|-------|----------|
| Dark Mode | 7 | 9 | 63 | HIGH |
| Keyboard Shortcuts | 8 | 9 | 72 | HIGH |
| Email Signatures | 9 | 9 | 81 | **CRITICAL** |
| 2FA | 10 | 8 | 80 | **CRITICAL** |
| Email Scheduling | 7 | 8 | 56 | MEDIUM |
| Browser Extension | 9 | 6 | 54 | MEDIUM |
| Mobile Apps | 10 | 4 | 40 | LOW (high impact, hard) |
| Video Calls | 6 | 2 | 12 | LOW (medium impact, very hard) |

**Decision Rule:**
- Score 70+: Build immediately
- Score 50-69: Build within 6 months
- Score <50: Backlog

---

## 📝 USER-REQUESTED FEATURES

### Feedback Collection
- In-app feedback widget
- /feedback route
- Upvote/downvote features
- Public roadmap (like Linear)

---

## 🚀 RELEASE STRATEGY

### How to Ship These Features

**Don't:**
- ❌ Wait for perfection
- ❌ Build everything before shipping
- ❌ Ignore user feedback

**Do:**
- ✅ Ship MVPs (80% done is shippable)
- ✅ Beta features flag (opt-in)
- ✅ Gradual rollout (10% → 50% → 100%)
- ✅ Measure adoption (analytics)
- ✅ Iterate based on usage

---

**These features represent the evolution of Privra beyond the core vision. Prioritize based on user demand and business impact.**
