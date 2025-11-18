# PRIORITY 2: AI WORKSPACE (Neural Sync)

**Timeline:** 8 weeks (LAST - after Privacy Shield + B2B)
**Goal:** Make Privra the smartest email client with personalized AI
**Deliverable:** v3.0 Full Vision

---

## Overview

The AI Workspace transforms Privra from a privacy-focused email client into an intelligent workspace that **learns from you** without compromising privacy.

**Key Innovation:** Multi-tenant LoRA adapters. One base AI model, thousands of personalized "souls" that hot-swap on each request.

---

## Architecture Summary

```
Single GPU Server:
├─ Base Model: Llama 3.1 8B (16GB VRAM, frozen)
├─ User Adapters: 50MB each (loaded on-demand)
├─ vLLM Engine: Hot-swaps adapters per request
└─ Background Trainer: Weekly fine-tuning jobs

Cost: ~$800/month for 1000+ users (vs. $5000+ for individual instances)
```

---

## Feature 1: LoRA Adapter Infrastructure

### Overview
Personal AI "souls" that learn your writing style, domain knowledge, and preferences.

### User Stories
1. **As a user**, I want the AI to know my writing style, so that drafts sound like me.
2. **As a medical professional**, I want the AI to understand medical terms, so that categorization is accurate.
3. **As a user**, I want the AI to remember my preferences across devices, so that it feels like "my" AI.

### Technical Implementation

See `ARCHITECTURE.md` for full details. Key components:

- `user_adapters` table
- `adapter_training_queue` table
- `vllm_client.py` - Inference with adapter loading
- `adapter_manager.py` - Adapter lifecycle
- `adapter_trainer/train_worker.py` - Background training

### Adapter Training Flow

```
Week 1 (User Registration):
1. User signs up
2. Create blank adapter (no-op weights)
3. Adapter does nothing yet (uses base model)

Week 2 (After 50 sent emails):
4. Background job detects 50+ emails
5. Queue training job
6. Worker collects user's sent emails
7. Format as prompt-completion pairs
8. Fine-tune LoRA adapter (3 epochs, ~10 min)
9. Save adapter to /adapters/user_123.safetensors

Week 3+ (Every Sunday):
10. If user has 50+ new emails since last training:
    - Retrain adapter with updated data
    - Adapter "learns" new patterns
```

### Adapter Usage Example

```python
# User asks AI to categorize email
vllm_client.generate(
    prompt="Categorize this email: [email text]",
    user_email="alice@privra.xyz"  # Loads alice's adapter
)

# Output: "work" (because Alice's adapter knows medical terms = work)
```

### Testing Checklist
- [ ] Adapter created on registration
- [ ] Training queue populated after 50 emails
- [ ] Worker trains adapter successfully
- [ ] vLLM loads adapter on inference
- [ ] Adapter improves categorization accuracy
- [ ] Adapter cache (LRU) works

---

## Feature 2: Local RAG (Chat with Your Email)

### Overview
Sidebar chat panel. Ask questions about your email history. AI searches embeddings and answers with citations.

### User Stories
1. **As a user**, I want to ask "What was the budget in John's emails?", so that I don't have to search manually.
2. **As a user**, I want citations, so that I can verify the AI's answer.
3. **As a user**, I want fast responses, so that it feels like a conversation.

### Technical Implementation

#### Database Schema
```sql
-- Using pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE email_embeddings (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    email_id VARCHAR(255) NOT NULL,  -- IMAP UID
    email_subject TEXT,
    email_sender VARCHAR(255),
    email_date TIMESTAMP,

    embedding vector(384),  -- Sentence-Transformer dimensions

    indexed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embeddings_user ON email_embeddings(user_email);
CREATE INDEX idx_embeddings_vector ON email_embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### RAG Service
```python
# rag_service.py
from sentence_transformers import SentenceTransformer
import psycopg2

class LocalRAG:
    def __init__(self, user_email: str):
        self.user = user_email
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vllm_client = vllm_client

    def query(self, question: str, top_k: int = 5) -> dict:
        """
        Query user's email with RAG.

        Returns:
            {
                "answer": str,
                "sources": [
                    {"email_id": "123", "subject": "...", "snippet": "..."}
                ]
            }
        """
        # 1. Generate question embedding
        query_embedding = self.embedding_model.encode(question)

        # 2. Search similar emails (pgvector)
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT email_id, email_subject, email_sender,
                   1 - (embedding <=> %s::vector) as similarity
            FROM email_embeddings
            WHERE user_email = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding.tolist(), self.user,
              query_embedding.tolist(), top_k))

        results = cur.fetchall()

        # 3. Fetch full email bodies
        email_contexts = []
        sources = []

        for row in results:
            email_id, subject, sender, similarity = row

            # Fetch email body
            body = self._fetch_email_body(email_id)

            email_contexts.append(f"""
            From: {sender}
            Subject: {subject}
            Body: {body[:500]}
            """)

            sources.append({
                "email_id": email_id,
                "subject": subject,
                "sender": sender,
                "relevance": round(similarity, 3)
            })

        # 4. Build RAG prompt
        context = "\n\n---\n\n".join(email_contexts)

        prompt = f"""You are an AI assistant with access to the user's email history.

Context from relevant emails:
{context}

User question: {question}

Answer the question based ONLY on the context above. Include specific details (names, dates, numbers).
If the answer is not in the context, say "I don't have enough information to answer that."

Answer:"""

        # 5. Generate answer with user's adapter
        answer = self.vllm_client.generate(
            prompt=prompt,
            user_email=self.user,
            max_tokens=300,
            temperature=0.3
        )

        return {
            "answer": answer,
            "sources": sources
        }

    def _fetch_email_body(self, email_id: str) -> str:
        """Fetch email body from IMAP"""
        # Connect to IMAP, fetch email by ID
        # Return body text
        pass

local_rag = LocalRAG
```

#### Background Email Indexing
```python
# scripts/email_indexer.py
# Runs every hour, indexes new emails

def index_new_emails():
    """Index unindexed emails for all users"""
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    for user in get_all_users():
        # Fetch new emails (not yet indexed)
        new_emails = fetch_new_emails(user.email)

        for email in new_emails:
            # Generate embedding (subject + body)
            text = f"{email.subject} {email.body}"
            embedding = embedding_model.encode(text)

            # Store in database
            save_embedding(
                user_email=user.email,
                email_id=email.id,
                email_subject=email.subject,
                email_sender=email.sender,
                email_date=email.date,
                embedding=embedding
            )

    print(f"Indexed {len(new_emails)} emails")
```

#### UI: Chat Sidebar
```html
<!-- Right sidebar in inbox view -->
<div class="rag-chat-sidebar">
    <div class="chat-header">
        <h3>💬 Chat with your email</h3>
    </div>

    <div class="chat-messages" id="chatMessages">
        <!-- Messages appear here -->
    </div>

    <div class="chat-input">
        <input type="text" id="ragQuery"
               placeholder="Ask about your emails..."
               onkeypress="handleRAGEnter(event)">
        <button onclick="sendRAGQuery()">Send</button>
    </div>
</div>

<script>
async function sendRAGQuery() {
    const query = document.getElementById('ragQuery').value;

    const response = await fetch('/api/rag/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ query })
    });

    const result = await response.json();

    // Display answer + sources
    displayRAGResult(result.answer, result.sources);
}
</script>
```

#### Flask Route
```python
@app.route('/api/rag/query', methods=['POST'])
def rag_query():
    """RAG query endpoint"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']
    question = request.json['query']

    rag = LocalRAG(user_email)
    result = rag.query(question)

    return jsonify(result)
```

### Testing Checklist
- [ ] Emails indexed with embeddings
- [ ] Similarity search returns relevant emails
- [ ] RAG prompt includes context
- [ ] Answer includes citations
- [ ] Chat sidebar UI functional
- [ ] Fast response (<3 seconds)

---

## Feature 3: Living Docs (Auto-Updating Documents)

### Overview
Convert messy email threads into structured Markdown documents. Auto-update when new replies arrive.

### User Stories
1. **As a user**, I want to convert a thread into a requirements doc, so that I have a single source of truth.
2. **As a user**, I want the doc to auto-update, so that it stays current.
3. **As a user**, I want to edit the doc, so that I can add my own notes.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE living_docs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,

    thread_id VARCHAR(255) NOT NULL,  -- Email thread identifier
    doc_title VARCHAR(255) NOT NULL,
    markdown_content TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP,

    auto_update BOOLEAN DEFAULT TRUE,  -- Auto-update on new replies

    -- Version history
    version INT DEFAULT 1
);

CREATE TABLE living_doc_versions (
    id SERIAL PRIMARY KEY,
    doc_id INT REFERENCES living_docs(id) ON DELETE CASCADE,

    version INT,
    markdown_content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Living Docs Service
```python
# living_docs_service.py
class LivingDocsService:
    def generate_living_doc(self, user_email: str,
                           thread_id: str) -> dict:
        """
        Generate a Living Doc from an email thread.

        Returns:
            {
                "doc_id": 123,
                "title": "Project X Requirements",
                "markdown": "# Requirements\n\n..."
            }
        """
        # 1. Fetch all emails in thread
        thread_emails = self._fetch_thread_emails(user_email, thread_id)

        # 2. Build conversation context
        conversation = ""
        for email in thread_emails:
            conversation += f"""
From: {email.sender}
Date: {email.date}
Subject: {email.subject}

{email.body}

---
"""

        # 3. Prompt AI to extract structure
        prompt = f"""You are a document generator. Parse the following email thread and create a structured Markdown document.

Include these sections:
- # Summary
- ## Requirements
- ## Action Items
- ## Decisions Made
- ## Open Questions

Email Thread:
{conversation}

Generate Markdown document:"""

        markdown = vllm_client.generate(
            prompt=prompt,
            user_email=user_email,
            max_tokens=1000,
            temperature=0.5
        )

        # 4. Save to database
        conn = get_db_connection()
        cur = conn.cursor()

        # Extract title from first line of markdown
        doc_title = markdown.split('\n')[0].replace('# ', '')

        cur.execute("""
            INSERT INTO living_docs
            (user_email, thread_id, doc_title, markdown_content)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_email, thread_id, doc_title, markdown))

        doc_id = cur.fetchone()[0]
        conn.commit()

        return {
            "doc_id": doc_id,
            "title": doc_title,
            "markdown": markdown
        }

    def auto_update_doc(self, doc_id: int):
        """
        Auto-update Living Doc when new email arrives in thread.
        (Triggered by background job)
        """
        conn = get_db_connection()
        cur = conn.cursor()

        # Get doc
        cur.execute("""
            SELECT user_email, thread_id, markdown_content
            FROM living_docs
            WHERE id = %s AND auto_update = TRUE
        """, (doc_id,))

        user_email, thread_id, current_markdown = cur.fetchone()

        # Check if thread has new emails
        new_emails = self._fetch_new_thread_emails(user_email, thread_id)

        if not new_emails:
            return  # No updates

        # Prompt AI to update doc
        prompt = f"""You are updating a document based on new information from an email thread.

Current Document:
{current_markdown}

New Emails:
{self._format_emails(new_emails)}

Update the document to incorporate the new information. Keep the same structure. Mark new items with [NEW].

Updated Markdown:"""

        updated_markdown = vllm_client.generate(
            prompt=prompt,
            user_email=user_email,
            max_tokens=1200
        )

        # Save new version
        cur.execute("""
            UPDATE living_docs
            SET markdown_content = %s,
                last_updated = NOW(),
                version = version + 1
            WHERE id = %s
        """, (updated_markdown, doc_id))

        # Archive old version
        cur.execute("""
            INSERT INTO living_doc_versions
            (doc_id, version, markdown_content)
            VALUES (%s, (SELECT version - 1 FROM living_docs WHERE id = %s), %s)
        """, (doc_id, doc_id, current_markdown))

        conn.commit()

living_docs_service = LivingDocsService()
```

#### Flask Routes
```python
@app.route('/living-docs')
def living_docs():
    """View all Living Docs"""
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, doc_title, last_updated, auto_update
        FROM living_docs
        WHERE user_email = %s
        ORDER BY last_updated DESC
    """, (session['email'],))

    docs = cur.fetchall()

    return render_template('living_docs.html', docs=docs)


@app.route('/living-docs/<int:doc_id>')
def view_living_doc(doc_id):
    """View specific Living Doc"""
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT doc_title, markdown_content, version, last_updated
        FROM living_docs
        WHERE id = %s AND user_email = %s
    """, (doc_id, session['email']))

    doc = cur.fetchone()

    if not doc:
        flash('Document not found', 'error')
        return redirect(url_for('living_docs'))

    return render_template('living_doc_view.html',
                         title=doc[0],
                         markdown=doc[1],
                         version=doc[2],
                         updated=doc[3])


@app.route('/api/living-docs/generate', methods=['POST'])
def generate_living_doc():
    """Generate Living Doc from thread"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    thread_id = request.json['thread_id']

    result = living_docs_service.generate_living_doc(
        user_email=session['email'],
        thread_id=thread_id
    )

    return jsonify(result)
```

### Testing Checklist
- [ ] Generate doc from thread
- [ ] Markdown properly structured
- [ ] Auto-update triggers on new email
- [ ] Version history preserved
- [ ] Edit doc manually
- [ ] Disable auto-update

---

## Feature 4: Neural Sync (Memory Blobs)

### Overview
AI "remembers" you across devices. Encrypted memory blob synced via PortID.

### User Stories
1. **As a user**, I want my AI to remember my preferences, so that I don't have to retrain it on new devices.
2. **As a user**, I want the memory encrypted, so that the server can't read my preferences.
3. **As a user**, I want seamless cross-device sync, so that mobile and desktop feel the same.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE ai_memory_blobs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,

    blob_version INT NOT NULL,
    encrypted_blob TEXT NOT NULL,  -- Encrypted JSON

    created_at TIMESTAMP DEFAULT NOW(),
    synced_to_portid BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP
);
```

#### Neural Sync Service
```python
# neural_sync_service.py
import json
from cryptography.fernet import Fernet

class NeuralSyncService:
    """
    Periodically summarize user's AI preferences and sync to PortID.
    """

    def generate_memory_blob(self, user_email: str) -> dict:
        """
        Generate AI memory blob from user's data.

        Contains:
        - Writing style preferences
        - Frequently used phrases
        - Domain-specific knowledge
        - Categorization patterns
        """
        # 1. Analyze user's sent emails
        writing_patterns = self._analyze_writing_style(user_email)

        # 2. Get user preferences
        preferences = self._get_user_preferences(user_email)

        # 3. Get categorization history
        category_patterns = self._analyze_categorization(user_email)

        # 4. Build memory blob
        memory_blob = {
            "version": 1,
            "generated_at": datetime.now().isoformat(),
            "writing_style": writing_patterns,
            "preferences": preferences,
            "category_patterns": category_patterns
        }

        # 5. Encrypt with user's PortID key
        encryption_key = self._get_user_portid_key(user_email)
        encrypted_blob = self._encrypt_blob(memory_blob, encryption_key)

        # 6. Save to database
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ai_memory_blobs
            (user_email, blob_version, encrypted_blob)
            VALUES (%s, 1, %s)
            RETURNING id
        """, (user_email, encrypted_blob))

        blob_id = cur.fetchone()[0]
        conn.commit()

        return {
            "blob_id": blob_id,
            "encrypted_blob": encrypted_blob
        }

    def sync_to_portid(self, user_email: str, blob_id: int):
        """Sync memory blob to PortID network"""
        # Use PortID SDK to sync encrypted blob
        portid_service.sync_memory_blob(user_email, blob_id)

        # Mark as synced
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE ai_memory_blobs
            SET synced_to_portid = TRUE, synced_at = NOW()
            WHERE id = %s
        """, (blob_id,))

        conn.commit()

    def restore_from_portid(self, user_email: str) -> dict:
        """Restore AI memory on new device login"""
        # Fetch from PortID
        encrypted_blob = portid_service.fetch_memory_blob(user_email)

        if not encrypted_blob:
            return None

        # Decrypt with user's key
        decryption_key = self._get_user_portid_key(user_email)
        memory_blob = self._decrypt_blob(encrypted_blob, decryption_key)

        # Apply preferences
        self._apply_memory_blob(user_email, memory_blob)

        return memory_blob

neural_sync = NeuralSyncService()
```

#### Weekly Sync Job
```python
# scripts/neural_sync_job.py
# Runs every Sunday

def sync_all_users():
    """Generate and sync memory blobs for all active users"""
    for user in get_active_users():
        try:
            blob = neural_sync.generate_memory_blob(user.email)
            neural_sync.sync_to_portid(user.email, blob['blob_id'])
            print(f"✅ Synced {user.email}")
        except Exception as e:
            print(f"❌ Failed to sync {user.email}: {e}")
```

### Testing Checklist
- [ ] Memory blob generated
- [ ] Blob encrypted
- [ ] Synced to PortID
- [ ] Restored on new device
- [ ] Preferences applied correctly

---

## Implementation Timeline

### Week 15-16: AI Infrastructure
- [ ] Provision GPU droplet (NVIDIA A10G)
- [ ] Install vLLM + Llama 3.1 8B
- [ ] Install pgvector extension
- [ ] Docker GPU configuration
- [ ] Test basic inference

### Week 17-19: LoRA Adapters
- [ ] Database schema
- [ ] `vllm_client.py`
- [ ] `adapter_manager.py`
- [ ] `adapter_trainer/train_worker.py`
- [ ] Adapter creation on registration
- [ ] Weekly training jobs
- [ ] Test adapter loading/switching

### Week 20: Local RAG
- [ ] Email embedding indexer
- [ ] `rag_service.py`
- [ ] Chat sidebar UI
- [ ] `/api/rag/query` route
- [ ] Citation display
- [ ] Test query accuracy

### Week 21-22: Living Docs + Neural Sync
- [ ] `living_docs_service.py`
- [ ] Living Docs UI
- [ ] Auto-update mechanism
- [ ] `neural_sync_service.py`
- [ ] PortID integration
- [ ] Weekly sync job

---

## Success Metrics
- [ ] 50%+ users enable AI features
- [ ] 1000+ RAG queries per day
- [ ] Adapter accuracy >80%
- [ ] Neural Sync restores 95%+ preferences
- [ ] Living Doc auto-update works
- [ ] User retention increases 20%

---

**This completes Priority 2: AI Workspace documentation.**
**Implementation: LAST (after Privacy Shield + B2B).**
