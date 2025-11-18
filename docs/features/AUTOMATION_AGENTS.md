# PRIORITY 4: AUTOMATION & AGENTS

**Timeline:** 4-6 weeks (after B2B, before or parallel to AI)
**Goal:** Make Privra agentic - AI that takes action, not just answers questions
**Deliverable:** v2.5 - "The Autopilot Email"

---

## Overview

While Priority 2 (AI Workspace) focuses on **intelligence** (RAG, personalization), Priority 4 focuses on **automation** - AI agents that ACT on your behalf.

**Key Difference:**
- Priority 2: "What was discussed in emails with John?" (passive)
- Priority 4: "Research this lead and draft a personalized email" (active)

---

## Feature 1: Privra Pipeline (Email Kanban)

### Overview
Treat emails as tasks. Kanban board view with drag-and-drop. Move emails through workflow stages.

### User Stories
1. **As a user**, I want to see emails as a kanban board, so that I can track what needs action.
2. **As a user**, I want to drag emails between columns, so that I can organize my workflow.
3. **As a sales rep**, I want to see all leads in "To-Do" column, so that I don't miss follow-ups.

### Technical Implementation

#### Database Schema
```sql
-- Add pipeline status to emails
ALTER TABLE emails ADD COLUMN pipeline_status VARCHAR(20) DEFAULT 'todo';
-- Values: 'todo', 'in_progress', 'waiting', 'done'

-- Pipeline configuration (custom columns per user)
CREATE TABLE pipeline_columns (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    column_name VARCHAR(100) NOT NULL,
    column_order INT NOT NULL,
    color VARCHAR(20),  -- UI color
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_email, column_order)
);

-- Default columns: To-Do, In Progress, Waiting, Done

-- Pipeline automation rules
CREATE TABLE pipeline_automation_rules (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,

    -- Trigger
    trigger_type VARCHAR(50) NOT NULL,  -- 'sender_is', 'subject_contains', 'body_contains'
    trigger_value TEXT NOT NULL,

    -- Action
    action_type VARCHAR(50) NOT NULL,  -- 'move_to_column', 'add_label', 'run_agent'
    action_value TEXT NOT NULL,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Pipeline Service
```python
# pipeline_service.py
class PipelineService:
    def get_pipeline_view(self, user_email: str) -> dict:
        """
        Get kanban board view of emails.

        Returns:
            {
                "columns": [
                    {
                        "name": "To-Do",
                        "emails": [...]
                    },
                    {
                        "name": "In Progress",
                        "emails": [...]
                    }
                ]
            }
        """
        conn = get_db_connection()
        cur = conn.cursor()

        # Get user's columns
        cur.execute("""
            SELECT column_name, column_order, color
            FROM pipeline_columns
            WHERE user_email = %s
            ORDER BY column_order
        """, (user_email,))

        columns = cur.fetchall()

        # If no custom columns, use defaults
        if not columns:
            columns = [
                ('To-Do', 1, '#3b82f6'),
                ('In Progress', 2, '#f59e0b'),
                ('Waiting', 3, '#8b5cf6'),
                ('Done', 4, '#10b981')
            ]

        # Get emails for each column
        pipeline_data = []

        for col_name, col_order, col_color in columns:
            cur.execute("""
                SELECT id, subject, sender, received_at
                FROM emails
                WHERE recipient = %s
                  AND pipeline_status = %s
                ORDER BY received_at DESC
                LIMIT 50
            """, (user_email, col_name.lower().replace(' ', '_')))

            emails = [
                {
                    'id': row[0],
                    'subject': row[1],
                    'sender': row[2],
                    'received_at': row[3].isoformat()
                }
                for row in cur.fetchall()
            ]

            pipeline_data.append({
                'name': col_name,
                'order': col_order,
                'color': col_color,
                'emails': emails,
                'count': len(emails)
            })

        return {'columns': pipeline_data}

    def move_email(self, email_id: int, to_column: str, user_email: str) -> bool:
        """Move email to different column"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE emails
            SET pipeline_status = %s
            WHERE id = %s AND recipient = %s
            RETURNING id
        """, (to_column, email_id, user_email))

        result = cur.fetchone()
        conn.commit()

        return result is not None

    def apply_automation_rules(self, email_id: int, user_email: str):
        """Apply automation rules to email"""
        conn = get_db_connection()
        cur = conn.cursor()

        # Get email details
        cur.execute("""
            SELECT subject, body, sender
            FROM emails WHERE id = %s
        """, (email_id,))

        subject, body, sender = cur.fetchone()

        # Get active rules
        cur.execute("""
            SELECT trigger_type, trigger_value, action_type, action_value
            FROM pipeline_automation_rules
            WHERE user_email = %s AND is_active = TRUE
        """, (user_email,))

        rules = cur.fetchall()

        for trigger_type, trigger_value, action_type, action_value in rules:
            # Check if trigger matches
            triggered = False

            if trigger_type == 'sender_is' and sender == trigger_value:
                triggered = True
            elif trigger_type == 'subject_contains' and trigger_value.lower() in subject.lower():
                triggered = True
            elif trigger_type == 'body_contains' and trigger_value.lower() in body.lower():
                triggered = True

            # Execute action
            if triggered:
                if action_type == 'move_to_column':
                    self.move_email(email_id, action_value, user_email)
                elif action_type == 'run_agent':
                    # Trigger agent (e.g., SDR Agent)
                    self._run_agent(action_value, email_id)

pipeline_service = PipelineService()
```

#### UI Template
```html
<!-- webmail/templates/pipeline.html -->
{% extends "base.html" %}

{% block content %}
<div class="pipeline-container">
    <div class="pipeline-header">
        <h1>Email Pipeline</h1>
        <button class="btn-primary" onclick="showAutomationModal()">
            ⚙️ Automation Rules
        </button>
    </div>

    <!-- Kanban Board -->
    <div class="pipeline-board">
        {% for column in columns %}
        <div class="pipeline-column" style="border-top: 3px solid {{ column.color }}">
            <div class="column-header">
                <h3>{{ column.name }}</h3>
                <span class="column-count">{{ column.count }}</span>
            </div>

            <div class="column-emails"
                 data-column="{{ column.name }}"
                 ondrop="drop(event)"
                 ondragover="allowDrop(event)">

                {% for email in column.emails %}
                <div class="pipeline-email-card"
                     draggable="true"
                     ondragstart="drag(event)"
                     data-email-id="{{ email.id }}">
                    <div class="email-subject">{{ email.subject }}</div>
                    <div class="email-sender">{{ email.sender }}</div>
                    <div class="email-date">{{ email.received_at }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<script>
function allowDrop(ev) {
    ev.preventDefault();
}

function drag(ev) {
    ev.dataTransfer.setData("emailId", ev.target.dataset.emailId);
}

async function drop(ev) {
    ev.preventDefault();
    const emailId = ev.dataTransfer.getData("emailId");
    const toColumn = ev.currentTarget.dataset.column;

    // Move email via API
    const response = await fetch('/pipeline/move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ email_id: emailId, to_column: toColumn })
    });

    if (response.ok) {
        location.reload();
    }
}
</script>
{% endblock %}
```

#### Flask Routes
```python
@app.route('/pipeline')
def pipeline():
    """Pipeline kanban view"""
    if 'email' not in session:
        return redirect(url_for('login'))

    pipeline_data = pipeline_service.get_pipeline_view(session['email'])

    return render_template('pipeline.html', columns=pipeline_data['columns'])


@app.route('/pipeline/move', methods=['POST'])
def pipeline_move():
    """Move email to different column"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    email_id = request.json['email_id']
    to_column = request.json['to_column']

    success = pipeline_service.move_email(email_id, to_column, session['email'])

    return jsonify({'success': success})
```

### Testing Checklist
- [ ] Kanban board displays emails
- [ ] Drag-and-drop works
- [ ] Emails move between columns
- [ ] Custom columns configurable
- [ ] Automation rules trigger correctly
- [ ] Mobile responsive (touch drag)

---

## Feature 2: SDR Agent (Sales Development Rep)

### Overview
AI agent that researches leads and drafts personalized cold emails. For B2B sales teams.

### User Stories
1. **As a sales rep**, I want the AI to research a lead's company, so that I can personalize outreach.
2. **As a sales rep**, I want auto-drafted emails, so that I can review and send quickly.
3. **As a manager**, I want to see which leads were researched, so that I can track sales activity.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE sdr_agent_leads (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,

    lead_email VARCHAR(255) NOT NULL,
    lead_name VARCHAR(255),
    company_name VARCHAR(255),
    company_domain VARCHAR(255),

    -- Research data
    research_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'researching', 'completed', 'failed'
    research_data JSONB,  -- Company info, LinkedIn profile, recent news
    researched_at TIMESTAMP,

    -- Draft email
    draft_subject TEXT,
    draft_body TEXT,
    drafted_at TIMESTAMP,

    -- Actions
    sent_at TIMESTAMP,
    replied_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sdr_agent_research_sources (
    id SERIAL PRIMARY KEY,
    lead_id INT REFERENCES sdr_agent_leads(id) ON DELETE CASCADE,

    source_type VARCHAR(50),  -- 'linkedin', 'company_website', 'news', 'crunchbase'
    source_url TEXT,
    data JSONB,

    fetched_at TIMESTAMP DEFAULT NOW()
);
```

#### SDR Agent Service
```python
# sdr_agent.py
import requests
from bs4 import BeautifulSoup
import json

class SDRAgent:
    """
    AI-powered Sales Development Rep.
    Researches leads and drafts personalized cold emails.
    """

    def research_lead(self, lead_email: str, user_email: str) -> dict:
        """
        Research a lead and draft personalized email.

        Steps:
        1. Extract company domain from email
        2. Scrape company website
        3. Search for LinkedIn profile
        4. Search for recent news
        5. Generate personalized email draft

        Returns:
            {
                "company_info": {...},
                "linkedin_profile": {...},
                "draft_email": {...}
            }
        """
        # 1. Extract domain
        domain = lead_email.split('@')[1]

        # 2. Research company
        company_info = self._research_company(domain)

        # 3. Search LinkedIn (if API available)
        linkedin_profile = self._search_linkedin(lead_email)

        # 4. Recent news
        news = self._search_news(domain)

        # 5. Store research
        research_data = {
            "company": company_info,
            "linkedin": linkedin_profile,
            "news": news
        }

        lead_id = self._save_lead(user_email, lead_email, research_data)

        # 6. Draft personalized email
        draft = self._draft_email(research_data, user_email)

        # Save draft
        self._save_draft(lead_id, draft)

        return {
            "lead_id": lead_id,
            "research": research_data,
            "draft": draft
        }

    def _research_company(self, domain: str) -> dict:
        """Scrape company website for info"""
        try:
            # Fetch homepage
            response = requests.get(f"https://{domain}", timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract company name
            company_name = soup.find('title').text if soup.find('title') else domain

            # Extract description (meta tag)
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')

            # Extract industry keywords
            body_text = soup.get_text()[:1000]  # First 1000 chars

            return {
                "name": company_name,
                "domain": domain,
                "description": description,
                "industry_keywords": self._extract_keywords(body_text)
            }
        except Exception as e:
            return {"error": str(e), "domain": domain}

    def _search_linkedin(self, email: str) -> dict:
        """
        Search for LinkedIn profile.
        (In production: Use LinkedIn API or Sales Navigator)
        """
        # Placeholder - requires LinkedIn API access
        return {
            "name": email.split('@')[0].title(),
            "profile_url": f"https://linkedin.com/search/results/people/?keywords={email}"
        }

    def _search_news(self, domain: str) -> list:
        """Search for recent company news"""
        # Use DuckDuckGo or News API
        try:
            query = f"{domain} news"
            # Simplified - in production use proper news API
            response = requests.get(
                f"https://api.duckduckgo.com/?q={query}&format=json",
                timeout=5
            )
            data = response.json()

            return [
                {
                    "title": item.get('Text', ''),
                    "url": item.get('FirstURL', '')
                }
                for item in data.get('RelatedTopics', [])[:3]
            ]
        except:
            return []

    def _draft_email(self, research_data: dict, user_email: str) -> dict:
        """Generate personalized cold email using AI"""
        company_name = research_data['company'].get('name', 'your company')
        company_desc = research_data['company'].get('description', '')

        prompt = f"""You are a sales development rep for Privra (privacy-focused email + AI workspace).

Draft a personalized cold email to a lead at this company:

Company: {company_name}
Description: {company_desc}
Industry: {research_data['company'].get('industry_keywords', '')}

Recent news: {research_data.get('news', [])}

Email requirements:
- Subject line (personalized, not spammy)
- Body: 3-4 sentences max
- Mention specific detail about their company
- Clear value prop for Privra
- Soft CTA (not pushy)

Format as JSON:
{{
  "subject": "...",
  "body": "..."
}}
"""

        # Generate with vLLM (user's adapter)
        response = vllm_client.generate(
            prompt=prompt,
            user_email=user_email,
            max_tokens=300,
            temperature=0.7
        )

        # Parse JSON
        try:
            draft = json.loads(response)
        except:
            # Fallback if JSON parsing fails
            draft = {
                "subject": f"Quick question about {company_name}",
                "body": response
            }

        return draft

    def _save_lead(self, user_email: str, lead_email: str, research_data: dict) -> int:
        """Save lead to database"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO sdr_agent_leads
            (user_email, lead_email, company_name, company_domain,
             research_status, research_data, researched_at)
            VALUES (%s, %s, %s, %s, 'completed', %s::jsonb, NOW())
            RETURNING id
        """, (user_email, lead_email,
              research_data['company'].get('name'),
              research_data['company'].get('domain'),
              json.dumps(research_data)))

        lead_id = cur.fetchone()[0]
        conn.commit()

        return lead_id

    def _save_draft(self, lead_id: int, draft: dict):
        """Save email draft"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE sdr_agent_leads
            SET draft_subject = %s, draft_body = %s, drafted_at = NOW()
            WHERE id = %s
        """, (draft['subject'], draft['body'], lead_id))

        conn.commit()

sdr_agent = SDRAgent()
```

#### Flask Routes
```python
@app.route('/agents/sdr')
def sdr_agent_page():
    """SDR Agent UI"""
    if 'email' not in session:
        return redirect(url_for('login'))

    # Get recent leads
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, lead_email, company_name, draft_subject, researched_at
        FROM sdr_agent_leads
        WHERE user_email = %s
        ORDER BY researched_at DESC
        LIMIT 50
    """, (session['email'],))

    leads = cur.fetchall()

    return render_template('sdr_agent.html', leads=leads)


@app.route('/agents/sdr/research', methods=['POST'])
def sdr_research():
    """Research a lead"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    lead_email = request.json['lead_email']

    # Run research (async in production)
    result = sdr_agent.research_lead(lead_email, session['email'])

    return jsonify(result)
```

### Testing Checklist
- [ ] Company website scraping works
- [ ] Email draft generated
- [ ] Draft is personalized (mentions company)
- [ ] Research data stored in database
- [ ] UI shows recent leads
- [ ] Send drafted email

---

## Feature 3: Invoice Droid (PDF → CSV Automation)

### Overview
AI agent that extracts data from PDF invoices and exports to CSV. For accounting/finance teams.

### User Stories
1. **As an accountant**, I want to forward invoice PDFs, so that they're auto-extracted.
2. **As a user**, I want invoices exported to CSV, so that I can import to QuickBooks.
3. **As a manager**, I want to see invoice totals, so that I can track expenses.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE invoice_agent_invoices (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,

    -- Source
    email_id VARCHAR(255),  -- Email that contained invoice
    pdf_path TEXT,

    -- Extracted data
    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    vendor_name VARCHAR(255),
    vendor_address TEXT,

    total_amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',

    line_items JSONB,  -- Array of line items

    -- Processing
    processing_status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Invoice Agent Service
```python
# invoice_agent.py
import PyPDF2
import re
import json

class InvoiceAgent:
    """
    AI agent that extracts data from PDF invoices.
    Uses OCR + LLM for extraction.
    """

    def process_invoice(self, pdf_path: str, user_email: str) -> dict:
        """
        Extract invoice data from PDF.

        Returns:
            {
                "invoice_number": "INV-001",
                "date": "2025-11-18",
                "vendor": "Acme Corp",
                "total": 1500.00,
                "line_items": [...]
            }
        """
        # 1. Extract text from PDF
        text = self._extract_pdf_text(pdf_path)

        # 2. Use LLM to extract structured data
        prompt = f"""Extract invoice data from the following text and return as JSON.

Invoice Text:
{text}

Return JSON with these fields:
{{
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "vendor_name": "...",
  "vendor_address": "...",
  "total_amount": 0.00,
  "currency": "USD",
  "line_items": [
    {{"description": "...", "quantity": 1, "unit_price": 0.00, "total": 0.00}}
  ]
}}

JSON:"""

        response = vllm_client.generate(
            prompt=prompt,
            user_email=user_email,
            max_tokens=500,
            temperature=0.1  # Low temp for structured extraction
        )

        # Parse JSON
        try:
            invoice_data = json.loads(response)
        except:
            # Fallback: Use regex extraction
            invoice_data = self._regex_fallback_extraction(text)

        # 3. Save to database
        invoice_id = self._save_invoice(user_email, pdf_path, invoice_data)

        return {
            "invoice_id": invoice_id,
            **invoice_data
        }

    def export_to_csv(self, user_email: str, start_date=None, end_date=None) -> str:
        """Export invoices to CSV"""
        import csv
        from io import StringIO

        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT invoice_number, invoice_date, vendor_name,
                   total_amount, currency
            FROM invoice_agent_invoices
            WHERE user_email = %s
        """

        params = [user_email]

        if start_date:
            query += " AND invoice_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND invoice_date <= %s"
            params.append(end_date)

        query += " ORDER BY invoice_date DESC"

        cur.execute(query, params)
        invoices = cur.fetchall()

        # Write CSV
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(['Invoice Number', 'Date', 'Vendor', 'Amount', 'Currency'])

        for inv in invoices:
            writer.writerow(inv)

        return output.getvalue()

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        with open(pdf_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf.pages:
                text += page.extract_text()

        return text

    def _save_invoice(self, user_email: str, pdf_path: str, data: dict) -> int:
        """Save invoice to database"""
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO invoice_agent_invoices
            (user_email, pdf_path, invoice_number, invoice_date,
             due_date, vendor_name, vendor_address, total_amount,
             currency, line_items, processing_status, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'completed', NOW())
            RETURNING id
        """, (user_email, pdf_path, data.get('invoice_number'),
              data.get('invoice_date'), data.get('due_date'),
              data.get('vendor_name'), data.get('vendor_address'),
              data.get('total_amount'), data.get('currency', 'USD'),
              json.dumps(data.get('line_items', []))))

        invoice_id = cur.fetchone()[0]
        conn.commit()

        return invoice_id

invoice_agent = InvoiceAgent()
```

### Testing Checklist
- [ ] PDF text extraction works
- [ ] LLM extracts invoice data correctly
- [ ] CSV export includes all fields
- [ ] Line items parsed correctly
- [ ] Auto-process emails with invoice PDFs
- [ ] QuickBooks import compatible

---

## Implementation Timeline

### Week 1-2: Privra Pipeline
- [ ] Database schema
- [ ] Pipeline service
- [ ] Kanban UI
- [ ] Drag-and-drop
- [ ] Automation rules

### Week 3-4: SDR Agent
- [ ] Company research scraper
- [ ] LinkedIn integration (basic)
- [ ] Email draft generation
- [ ] SDR Agent UI
- [ ] Lead tracking

### Week 5-6: Invoice Droid
- [ ] PDF extraction
- [ ] LLM data extraction
- [ ] CSV export
- [ ] Email auto-processing
- [ ] Invoice dashboard

---

## Success Metrics
- [ ] 40%+ of users use Pipeline view
- [ ] Average 3 columns per user
- [ ] SDR Agent: 80%+ drafts are sent (shows quality)
- [ ] Invoice Droid: 90%+ extraction accuracy
- [ ] Time saved: 5+ hours per week per user

---

**This completes Priority 4: Automation & Agents documentation.**
**Can be implemented before or parallel to Priority 2 (AI), as it's less infrastructure-heavy.**
