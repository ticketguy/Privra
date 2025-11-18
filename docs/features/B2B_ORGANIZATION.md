# PRIORITY 3: B2B/ORGANIZATION FEATURES

**Timeline:** 8 weeks (after Privacy Shield)
**Goal:** Open the enterprise market. 10x revenue potential.
**Deliverable:** v2.0 Enterprise-Ready

---

## Feature 1: Organization Registration & Management

### Overview
Separate registration flow for organizations. Create org-level accounts with admin controls.

### User Stories
1. **As an organization admin**, I want to register my company, so that I can manage employee access.
2. **As an admin**, I want to invite employees via digital badges, so that onboarding is seamless.
3. **As an employee**, I want to use my personal PortID, so that I maintain sovereignty even within org.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    org_did VARCHAR(255) UNIQUE NOT NULL,  -- did:privra:org:acme-corp
    org_name VARCHAR(255) NOT NULL,
    org_domain VARCHAR(255),  -- @acme-law.privra.xyz
    admin_email VARCHAR(255) REFERENCES users(email),

    -- Subscription
    subscription_tier VARCHAR(50) DEFAULT 'starter',  -- 'starter', 'growth', 'enterprise'
    max_employees INT DEFAULT 10,
    price_per_seat DECIMAL(10,2) DEFAULT 20.00,

    -- Billing
    billing_email VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    subscription_status VARCHAR(50) DEFAULT 'active',

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE org_members (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id) ON DELETE CASCADE,
    user_email VARCHAR(255) REFERENCES users(email) ON DELETE CASCADE,
    badge_id INT REFERENCES digital_badges(id),

    role VARCHAR(50) DEFAULT 'member',  -- 'admin', 'member', 'contractor'
    department VARCHAR(100),  -- 'Finance', 'Legal', 'Engineering'

    joined_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP,

    UNIQUE(org_id, user_email)
);

CREATE TABLE org_invitations (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id) ON DELETE CASCADE,
    invitee_email VARCHAR(255) NOT NULL,
    invited_by VARCHAR(255) REFERENCES users(email),

    role VARCHAR(50) DEFAULT 'member',
    department VARCHAR(100),

    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP,

    accepted_at TIMESTAMP,
    declined_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Organization DID Generation
```python
# org_did_service.py
import hashlib
import secrets

class OrgDIDService:
    """
    Generate W3C-compliant DIDs for organizations.
    Format: did:privra:org:<org-identifier>
    """

    def generate_org_did(self, org_name: str) -> str:
        """
        Generate organization DID.

        Example:
            "Acme Corp" → "did:privra:org:acme-corp-a3f2"
        """
        # Normalize org name
        normalized = org_name.lower().replace(' ', '-')
        normalized = ''.join(c for c in normalized if c.isalnum() or c == '-')

        # Add random suffix for uniqueness
        suffix = secrets.token_hex(2)

        org_id = f"{normalized}-{suffix}"

        return f"did:privra:org:{org_id}"

    def verify_org_did(self, org_did: str) -> bool:
        """Verify DID format"""
        return org_did.startswith('did:privra:org:')

org_did_service = OrgDIDService()
```

#### Organization Service
```python
# org_service.py
from typing import Optional
import psycopg2

class OrganizationService:
    def create_organization(self, org_name: str, admin_email: str,
                           org_domain: Optional[str] = None,
                           subscription_tier: str = 'starter') -> dict:
        """
        Create a new organization.

        Args:
            org_name: Company name
            admin_email: Admin user email (must exist)
            org_domain: Custom domain (e.g., @acme.privra.xyz)
            subscription_tier: 'starter', 'growth', 'enterprise'

        Returns:
            Organization details
        """
        # Generate org DID
        org_did = org_did_service.generate_org_did(org_name)

        # Set domain
        if not org_domain:
            org_slug = org_name.lower().replace(' ', '-')[:20]
            org_domain = f"@{org_slug}.privra.xyz"

        # Determine pricing
        pricing = {
            'starter': {'max_employees': 10, 'price_per_seat': 20.00},
            'growth': {'max_employees': 50, 'price_per_seat': 18.00},
            'enterprise': {'max_employees': 500, 'price_per_seat': 15.00}
        }

        tier_config = pricing[subscription_tier]

        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO organizations
            (org_did, org_name, org_domain, admin_email, subscription_tier,
             max_employees, price_per_seat)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, org_did, created_at
        """, (org_did, org_name, org_domain, admin_email, subscription_tier,
              tier_config['max_employees'], tier_config['price_per_seat']))

        result = cur.fetchone()
        org_id, org_did, created_at = result

        # Add admin as first member
        cur.execute("""
            INSERT INTO org_members (org_id, user_email, role)
            VALUES (%s, %s, 'admin')
        """, (org_id, admin_email))

        conn.commit()

        return {
            'id': org_id,
            'org_did': org_did,
            'org_name': org_name,
            'org_domain': org_domain,
            'subscription_tier': subscription_tier,
            'created_at': created_at.isoformat()
        }

    def invite_member(self, org_id: int, invitee_email: str,
                     invited_by: str, role: str = 'member',
                     department: Optional[str] = None) -> dict:
        """Send organization invitation"""
        import secrets
        from datetime import datetime, timedelta

        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)

        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO org_invitations
            (org_id, invitee_email, invited_by, role, department,
             invitation_token, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (org_id, invitee_email, invited_by, role, department,
              invitation_token, expires_at))

        invitation_id = cur.fetchone()[0]
        conn.commit()

        # Send invitation email
        invitation_url = f"https://privra.xyz/org/join?token={invitation_token}"

        self._send_invitation_email(
            to_email=invitee_email,
            org_name=self._get_org_name(org_id),
            invitation_url=invitation_url
        )

        return {
            'invitation_id': invitation_id,
            'invitation_url': invitation_url,
            'expires_at': expires_at.isoformat()
        }

    def accept_invitation(self, invitation_token: str, user_email: str) -> bool:
        """Accept organization invitation"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        # Verify invitation
        cur.execute("""
            SELECT org_id, role, department, expires_at
            FROM org_invitations
            WHERE invitation_token = %s
              AND invitee_email = %s
              AND accepted_at IS NULL
              AND declined_at IS NULL
        """, (invitation_token, user_email))

        invitation = cur.fetchone()

        if not invitation:
            return False

        org_id, role, department, expires_at = invitation

        # Check expiration
        from datetime import datetime
        if datetime.now() > expires_at:
            return False

        # Add to org members
        cur.execute("""
            INSERT INTO org_members (org_id, user_email, role, department)
            VALUES (%s, %s, %s, %s)
        """, (org_id, user_email, role, department))

        # Mark invitation as accepted
        cur.execute("""
            UPDATE org_invitations
            SET accepted_at = NOW()
            WHERE invitation_token = %s
        """, (invitation_token,))

        conn.commit()
        return True

    def get_org_members(self, org_id: int) -> list:
        """Get all members of an organization"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT om.user_email, om.role, om.department, om.joined_at,
                   u.email
            FROM org_members om
            JOIN users u ON om.user_email = u.email
            WHERE om.org_id = %s AND om.removed_at IS NULL
            ORDER BY om.joined_at
        """, (org_id,))

        members = []
        for row in cur.fetchall():
            members.append({
                'email': row[0],
                'role': row[1],
                'department': row[2],
                'joined_at': row[3].isoformat()
            })

        return members

org_service = OrganizationService()
```

#### Flask Routes
```python
# webmail/app.py

@app.route('/org/register', methods=['GET', 'POST'])
def org_register():
    """Organization registration"""
    if request.method == 'GET':
        return render_template('org_register.html')

    # POST: Create organization
    org_name = request.form['org_name']
    admin_email = session.get('email')

    if not admin_email:
        flash('You must be logged in to create an organization', 'error')
        return redirect(url_for('login'))

    try:
        org = org_service.create_organization(
            org_name=org_name,
            admin_email=admin_email,
            subscription_tier=request.form.get('tier', 'starter')
        )

        flash(f"Organization '{org_name}' created successfully!", 'success')
        return redirect(url_for('org_dashboard'))

    except Exception as e:
        flash(f"Error creating organization: {str(e)}", 'error')
        return redirect(url_for('org_register'))


@app.route('/org/dashboard')
def org_dashboard():
    """Organization admin dashboard"""
    if 'email' not in session:
        return redirect(url_for('login'))

    # Get user's organizations (where they are admin)
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, org_name, org_domain, subscription_tier, max_employees
        FROM organizations
        WHERE admin_email = %s
    """, (session['email'],))

    orgs = cur.fetchall()

    if not orgs:
        flash('You are not an admin of any organization', 'info')
        return redirect(url_for('org_register'))

    # For now, show first org (multi-org support later)
    org = {
        'id': orgs[0][0],
        'name': orgs[0][1],
        'domain': orgs[0][2],
        'tier': orgs[0][3],
        'max_employees': orgs[0][4]
    }

    # Get members
    members = org_service.get_org_members(org['id'])

    return render_template('org_dashboard.html', org=org, members=members)


@app.route('/org/invite', methods=['POST'])
def org_invite():
    """Invite member to organization"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = request.json['org_id']
    invitee_email = request.json['invitee_email']
    role = request.json.get('role', 'member')

    result = org_service.invite_member(
        org_id=org_id,
        invitee_email=invitee_email,
        invited_by=session['email'],
        role=role
    )

    return jsonify(result)


@app.route('/org/join')
def org_join():
    """Accept organization invitation"""
    token = request.args.get('token')

    if 'email' not in session:
        # Store token and redirect to login
        session['pending_org_token'] = token
        flash('Please log in to accept the invitation', 'info')
        return redirect(url_for('login'))

    success = org_service.accept_invitation(token, session['email'])

    if success:
        flash('You have joined the organization!', 'success')
        return redirect(url_for('inbox'))
    else:
        flash('Invalid or expired invitation', 'error')
        return redirect(url_for('inbox'))
```

### Testing Checklist
- [ ] Org registration creates DID
- [ ] Admin can invite members
- [ ] Invitation email sent with link
- [ ] Member can accept invitation
- [ ] Expired invitations rejected
- [ ] Org dashboard shows members
- [ ] Role-based access control

---

## Feature 2: Digital Badge System (Verifiable Credentials)

### Overview
W3C Verifiable Credentials for employee access. Passwordless, time-limited, revocable.

### User Stories
1. **As an admin**, I want to issue badges to employees, so that they can access org resources.
2. **As an admin**, I want to issue time-limited badges for contractors, so that access auto-expires.
3. **As an admin**, I want to revoke badges instantly, so that terminated employees lose access immediately.
4. **As an employee**, I want to use my personal PortID, so that I don't need org passwords.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE digital_badges (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id) ON DELETE CASCADE,
    employee_portid VARCHAR(255) NOT NULL,  -- Employee's personal DID

    -- Badge credential (signed JWT)
    badge_credential TEXT NOT NULL,  -- JSON Web Token

    -- Permissions
    role VARCHAR(50) DEFAULT 'member',  -- 'admin', 'member', 'contractor'
    permissions JSONB DEFAULT '[]',  -- ['read_email', 'send_internal', 'access_company_brain']

    -- Expiration (for contractors)
    issued_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- NULL = permanent

    -- Revocation
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(255),
    revocation_reason TEXT,

    -- Metadata
    issuer_did VARCHAR(255),  -- Org DID
    credential_hash VARCHAR(255) UNIQUE,  -- SHA256 of credential
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_badges_portid ON digital_badges(employee_portid);
CREATE INDEX idx_badges_org ON digital_badges(org_id);
```

#### Badge Service (W3C Verifiable Credentials)
```python
# badge_service.py
import jwt
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

class BadgeService:
    """
    Issue and verify W3C Verifiable Credentials for employee access.
    Uses JWT format for simplicity (not full JSON-LD).
    """

    def __init__(self):
        # In production: Load from secure key storage
        self.signing_key = self._load_org_signing_key()

    def issue_badge(self, org_id: int, employee_portid: str,
                   role: str = 'member',
                   permissions: list = None,
                   expires_in_days: Optional[int] = None) -> dict:
        """
        Issue a digital badge (Verifiable Credential).

        Args:
            org_id: Organization ID
            employee_portid: Employee's personal PortID
            role: 'admin', 'member', 'contractor'
            permissions: List of permissions
            expires_in_days: Expiration (e.g., 30 for contractors)

        Returns:
            Badge credential (JWT)
        """
        # Get org DID
        org_did = self._get_org_did(org_id)

        # Default permissions by role
        if not permissions:
            permissions = self._get_default_permissions(role)

        # Build credential
        now = datetime.utcnow()
        issued_at = now
        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

        credential = {
            # W3C VC standard fields
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "PrivraBadge"],
            "issuer": org_did,
            "issuanceDate": issued_at.isoformat(),

            "credentialSubject": {
                "id": employee_portid,
                "role": role,
                "permissions": permissions,
                "orgId": org_id
            }
        }

        if expires_at:
            credential["expirationDate"] = expires_at.isoformat()

        # Sign credential (JWT)
        badge_jwt = jwt.encode(
            credential,
            self.signing_key,
            algorithm='HS256'
        )

        # Hash for revocation checking
        credential_hash = hashlib.sha256(badge_jwt.encode()).hexdigest()

        # Store in database
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO digital_badges
            (org_id, employee_portid, badge_credential, role,
             permissions, issued_at, expires_at, issuer_did, credential_hash)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            RETURNING id
        """, (org_id, employee_portid, badge_jwt, role,
              json.dumps(permissions), issued_at, expires_at, org_did, credential_hash))

        badge_id = cur.fetchone()[0]
        conn.commit()

        return {
            'badge_id': badge_id,
            'credential': badge_jwt,
            'issued_at': issued_at.isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None
        }

    def verify_badge(self, badge_jwt: str) -> tuple[bool, Optional[dict]]:
        """
        Verify badge validity.

        Returns:
            (is_valid: bool, credential: dict)
        """
        try:
            # Decode JWT
            credential = jwt.decode(
                badge_jwt,
                self.signing_key,
                algorithms=['HS256']
            )

            # Check revocation
            credential_hash = hashlib.sha256(badge_jwt.encode()).hexdigest()
            if self._is_revoked(credential_hash):
                return (False, None)

            # Check expiration
            if 'expirationDate' in credential:
                expires_at = datetime.fromisoformat(credential['expirationDate'])
                if datetime.utcnow() > expires_at:
                    return (False, None)

            return (True, credential)

        except jwt.InvalidTokenError:
            return (False, None)

    def revoke_badge(self, badge_id: int, revoked_by: str,
                    reason: str = "Access terminated") -> bool:
        """Revoke a badge (immediate effect)"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE digital_badges
            SET revoked_at = NOW(),
                revoked_by = %s,
                revocation_reason = %s
            WHERE id = %s AND revoked_at IS NULL
            RETURNING credential_hash
        """, (revoked_by, reason, badge_id))

        result = cur.fetchone()

        if result:
            conn.commit()
            print(f"🔴 Badge {badge_id} revoked by {revoked_by}")
            return True
        else:
            return False

    def _get_default_permissions(self, role: str) -> list:
        """Default permissions by role"""
        permissions = {
            'admin': [
                'read_email', 'send_email', 'manage_members',
                'access_company_brain', 'view_traffic_tower',
                'issue_badges', 'revoke_badges'
            ],
            'member': [
                'read_email', 'send_email', 'access_company_brain'
            ],
            'contractor': [
                'read_email', 'send_email'
            ]
        }
        return permissions.get(role, [])

    def _is_revoked(self, credential_hash: str) -> bool:
        """Check if credential is revoked"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 1 FROM digital_badges
            WHERE credential_hash = %s AND revoked_at IS NOT NULL
        """, (credential_hash,))

        return cur.fetchone() is not None

badge_service = BadgeService()
```

#### Flask Routes
```python
@app.route('/org/badges')
def org_badges():
    """Badge management page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    # Get user's org
    org_id = get_user_org_id(session['email'])

    # Get all badges
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, employee_portid, role, issued_at, expires_at,
               revoked_at, revoked_by
        FROM digital_badges
        WHERE org_id = %s
        ORDER BY issued_at DESC
    """, (org_id,))

    badges = cur.fetchall()

    return render_template('org_badges.html', badges=badges)


@app.route('/org/badges/issue', methods=['POST'])
def issue_badge():
    """Issue a new badge"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = get_user_org_id(session['email'])
    employee_portid = request.json['employee_portid']
    role = request.json.get('role', 'member')
    expires_in_days = request.json.get('expires_in_days')  # For contractors

    result = badge_service.issue_badge(
        org_id=org_id,
        employee_portid=employee_portid,
        role=role,
        expires_in_days=expires_in_days
    )

    return jsonify(result)


@app.route('/org/badges/<int:badge_id>/revoke', methods=['POST'])
def revoke_badge(badge_id):
    """Revoke a badge"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    reason = request.json.get('reason', 'Access terminated')

    success = badge_service.revoke_badge(
        badge_id=badge_id,
        revoked_by=session['email'],
        reason=reason
    )

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Badge not found or already revoked'}), 404
```

### Testing Checklist
- [ ] Issue permanent badge (member)
- [ ] Issue time-limited badge (contractor, 30 days)
- [ ] Badge verification succeeds
- [ ] Revoked badge fails verification
- [ ] Expired badge fails verification
- [ ] Admin can see all org badges
- [ ] Revocation is immediate

---

## Feature 3: Company Brain (Shared Knowledge Base)

### Overview
Upload PDFs, handbooks, Slack exports. All employees' AI can query org knowledge.

### User Stories
1. **As an admin**, I want to upload company docs, so that all employees can query them.
2. **As an employee**, I want to ask "How do I request PTO?", and get answers from the employee handbook.
3. **As an admin**, I want to see which documents are most queried, so that I can improve documentation.

### Technical Implementation

#### Database Schema
```sql
CREATE TABLE org_knowledge_base (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id) ON DELETE CASCADE,

    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- 'pdf', 'markdown', 'docx', 'slack_export'
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,

    uploaded_by VARCHAR(255) REFERENCES users(email),
    uploaded_at TIMESTAMP DEFAULT NOW(),

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'indexed', 'failed'
    processed_at TIMESTAMP,
    error_message TEXT,

    -- Metadata
    page_count INT,  -- For PDFs
    word_count INT,
    chunk_count INT,  -- Number of embeddings generated

    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE org_knowledge_chunks (
    id SERIAL PRIMARY KEY,
    document_id INT REFERENCES org_knowledge_base(id) ON DELETE CASCADE,
    org_id INT REFERENCES organizations(id) ON DELETE CASCADE,

    chunk_text TEXT NOT NULL,
    chunk_index INT,  -- Position in document
    page_number INT,  -- For PDFs

    embedding vector(384),  -- pgvector

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_org_knowledge_org ON org_knowledge_chunks(org_id);

-- Usage analytics
CREATE TABLE org_knowledge_queries (
    id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(id),
    user_email VARCHAR(255) REFERENCES users(email),

    query_text TEXT,
    matched_document_ids INT[],  -- Array of document IDs

    queried_at TIMESTAMP DEFAULT NOW()
);
```

#### Company Brain Service
```python
# company_brain_service.py
import PyPDF2
import markdown
from sentence_transformers import SentenceTransformer

class CompanyBrainService:
    """
    Manages organization knowledge base.
    Ingests documents, generates embeddings, enables RAG queries.
    """

    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def upload_document(self, org_id: int, file_path: str,
                       document_name: str, document_type: str,
                       uploaded_by: str) -> int:
        """
        Upload document to org knowledge base.

        Returns:
            document_id
        """
        import os
        file_size = os.path.getsize(file_path)

        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO org_knowledge_base
            (org_id, document_name, document_type, file_path,
             file_size_bytes, uploaded_by, processing_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """, (org_id, document_name, document_type, file_path,
              file_size, uploaded_by))

        document_id = cur.fetchone()[0]
        conn.commit()

        # Queue for processing (background job)
        self._queue_processing(document_id)

        return document_id

    def process_document(self, document_id: int):
        """
        Process document: extract text, generate embeddings.
        (Run as background job)
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        # Get document
        cur.execute("""
            SELECT org_id, document_type, file_path
            FROM org_knowledge_base
            WHERE id = %s
        """, (document_id,))

        org_id, doc_type, file_path = cur.fetchone()

        # Update status
        cur.execute("""
            UPDATE org_knowledge_base
            SET processing_status = 'processing'
            WHERE id = %s
        """, (document_id,))
        conn.commit()

        try:
            # Extract text
            if doc_type == 'pdf':
                chunks = self._extract_pdf_chunks(file_path)
            elif doc_type == 'markdown':
                chunks = self._extract_markdown_chunks(file_path)
            else:
                raise ValueError(f"Unsupported document type: {doc_type}")

            # Generate embeddings
            for i, chunk in enumerate(chunks):
                embedding = self.embedding_model.encode(chunk['text'])

                cur.execute("""
                    INSERT INTO org_knowledge_chunks
                    (document_id, org_id, chunk_text, chunk_index,
                     page_number, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (document_id, org_id, chunk['text'], i,
                      chunk.get('page'), embedding.tolist()))

            # Update status
            cur.execute("""
                UPDATE org_knowledge_base
                SET processing_status = 'indexed',
                    processed_at = NOW(),
                    chunk_count = %s
                WHERE id = %s
            """, (len(chunks), document_id))

            conn.commit()
            print(f"✅ Processed document {document_id}: {len(chunks)} chunks")

        except Exception as e:
            # Mark as failed
            cur.execute("""
                UPDATE org_knowledge_base
                SET processing_status = 'failed',
                    error_message = %s
                WHERE id = %s
            """, (str(e), document_id))
            conn.commit()

    def query_knowledge_base(self, org_id: int, query: str,
                            user_email: str, top_k: int = 3) -> list:
        """
        Query organization knowledge base.

        Returns:
            [
                {
                    "text": "...",
                    "document_name": "...",
                    "page": 42,
                    "relevance_score": 0.85
                }
            ]
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)

        # Search (using pgvector cosine similarity)
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.chunk_text,
                c.page_number,
                d.document_name,
                1 - (c.embedding <=> %s::vector) as similarity
            FROM org_knowledge_chunks c
            JOIN org_knowledge_base d ON c.document_id = d.id
            WHERE c.org_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding.tolist(), org_id, query_embedding.tolist(), top_k))

        results = []
        matched_doc_ids = []

        for row in cur.fetchall():
            results.append({
                'text': row[0],
                'page': row[1],
                'document_name': row[2],
                'relevance_score': round(row[3], 3)
            })
            matched_doc_ids.append(row[2])

        # Log query
        cur.execute("""
            INSERT INTO org_knowledge_queries
            (org_id, user_email, query_text, matched_document_ids)
            VALUES (%s, %s, %s, %s)
        """, (org_id, user_email, query, matched_doc_ids))

        conn.commit()

        return results

    def _extract_pdf_chunks(self, file_path: str) -> list:
        """Extract text chunks from PDF"""
        chunks = []

        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()

                # Split into smaller chunks (500 words each)
                words = text.split()
                for i in range(0, len(words), 500):
                    chunk_text = ' '.join(words[i:i+500])

                    chunks.append({
                        'text': chunk_text,
                        'page': page_num
                    })

        return chunks

    def _extract_markdown_chunks(self, file_path: str) -> list:
        """Extract chunks from Markdown"""
        with open(file_path, 'r') as f:
            content = f.read()

        # Split by headers
        sections = content.split('\n## ')

        chunks = []
        for section in sections:
            chunks.append({
                'text': section,
                'page': None
            })

        return chunks

company_brain = CompanyBrainService()
```

#### Flask Routes
```python
@app.route('/org/knowledge')
def org_knowledge():
    """Company Brain page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    org_id = get_user_org_id(session['email'])

    # Get documents
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, document_name, document_type, uploaded_at,
               processing_status, chunk_count
        FROM org_knowledge_base
        WHERE org_id = %s AND is_active = TRUE
        ORDER BY uploaded_at DESC
    """, (org_id,))

    documents = cur.fetchall()

    return render_template('org_knowledge.html', documents=documents)


@app.route('/org/knowledge/upload', methods=['POST'])
def upload_knowledge():
    """Upload document to Company Brain"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = get_user_org_id(session['email'])

    # Handle file upload
    file = request.files['document']
    filename = secure_filename(file.filename)
    upload_path = f"/app/org_knowledge/{org_id}/{filename}"

    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    file.save(upload_path)

    # Determine document type
    doc_type = filename.split('.')[-1]

    # Create database entry
    document_id = company_brain.upload_document(
        org_id=org_id,
        file_path=upload_path,
        document_name=filename,
        document_type=doc_type,
        uploaded_by=session['email']
    )

    return jsonify({
        'document_id': document_id,
        'status': 'processing'
    })


@app.route('/org/knowledge/query', methods=['POST'])
def query_knowledge():
    """Query Company Brain"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = get_user_org_id(session['email'])
    query = request.json['query']

    results = company_brain.query_knowledge_base(
        org_id=org_id,
        query=query,
        user_email=session['email']
    )

    return jsonify({'results': results})
```

### Testing Checklist
- [ ] Upload PDF document
- [ ] Document processed (chunks + embeddings)
- [ ] Query returns relevant results
- [ ] Cosine similarity ranking works
- [ ] Multiple document types supported
- [ ] Query logged for analytics

---

## Feature 4: Admin Traffic Tower (Metadata Audit)

### Overview
Privacy-preserving analytics. Admin sees metadata (who emails whom) WITHOUT reading content.

### User Stories
1. **As an admin**, I want to see email volume per employee, so that I can detect anomalies.
2. **As an admin**, I want to see top external contacts, so that I know who our partners are.
3. **As an admin**, I want alerts for unusual activity, so that I can prevent data leaks.

### Technical Implementation

```python
# traffic_tower_service.py
class TrafficTowerService:
    """
    Metadata-only analytics for organizations.
    NEVER accesses email content.
    """

    def get_email_volume_by_employee(self, org_id: int,
                                     days: int = 30) -> list:
        """Email volume per employee (last N days)"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                sender,
                COUNT(*) as sent_count,
                COUNT(DISTINCT recipient) as unique_recipients,
                SUM(CASE WHEN recipient LIKE '%@' || o.org_domain THEN 1 ELSE 0 END) as internal,
                SUM(CASE WHEN recipient NOT LIKE '%@' || o.org_domain THEN 1 ELSE 0 END) as external
            FROM sent_emails se
            JOIN org_members om ON se.sender = om.user_email
            JOIN organizations o ON om.org_id = o.id
            WHERE om.org_id = %s
              AND se.sent_at > NOW() - INTERVAL '%s days'
            GROUP BY sender
            ORDER BY sent_count DESC
        """, (org_id, days))

        return [
            {
                'employee': row[0],
                'sent_count': row[1],
                'unique_recipients': row[2],
                'internal': row[3],
                'external': row[4]
            }
            for row in cur.fetchall()
        ]

    def detect_anomalies(self, org_id: int) -> list:
        """Detect unusual activity"""
        # Example: Employee sending 10x their usual volume
        pass

traffic_tower = TrafficTowerService()
```

---

**This completes Priority 3: B2B/Organization documentation.**
**Time to implement: 8 weeks after Privacy Shield.**
