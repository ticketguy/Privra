#!/usr/bin/env python3
"""Simple Webmail Client for Privra Mail Server"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
import os
import psycopg2
from portid_service import portid_service
from crypto_utils import (
    decrypt_private_key_with_recovery_key,
    generate_email_keypair,
    serialize_public_key,
    serialize_private_key,
    encrypt_private_key_with_recovery_key
)
from Crypto.Random import get_random_bytes
import bcrypt
from email_categorizer import EmailCategorizer
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Handle reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Mail server settings
IMAP_HOST = os.getenv('IMAP_HOST', 'dovecot')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
SMTP_HOST = os.getenv('SMTP_HOST', 'postfix')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# Email categorizer
categorizer = EmailCategorizer()

# Database connection
def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def connect_imap(email_addr, password):
    """Connect to IMAP server"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(email_addr, password)
        return mail
    except Exception as e:
        print(f"IMAP connection error: {e}")
        return None

def connect_smtp(email_addr, password):
    """Connect to SMTP server"""
    try:
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        smtp.starttls()
        smtp.login(email_addr, password)
        return smtp
    except Exception as e:
        print(f"SMTP connection error: {e}")
        return None

def decode_mime_words(s):
    """Decode MIME encoded words"""
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    fragments = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            fragments.append(fragment.decode(encoding or 'utf-8', errors='replace'))
        else:
            fragments.append(fragment)
    return ''.join(fragments)

def get_email_body(msg):
    """Extract email body from message"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors='replace')
                    break
                except:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    body = part.get_payload(decode=True).decode(errors='replace')
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='replace')
        except:
            body = msg.get_payload()
    return body

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in"""
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Dashboard with stats and features"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        mail = connect_imap(session['email'], session['password'])
        if not mail:
            return redirect(url_for('login'))

        # Get inbox count
        mail.select('INBOX')
        status, messages = mail.search(None, 'ALL')
        total_emails = len(messages[0].split()) if messages[0] else 0

        # Get unread count
        status, unread = mail.search(None, 'UNSEEN')
        unread_count = len(unread[0].split()) if unread[0] else 0

        mail.logout()

        # Get encryption status
        has_encryption = session.get('has_encryption', False)

        # Get consent settings
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT require_consent, whitelist_mode
            FROM consent_settings
            WHERE user_email = %s
        """, (session['email'],))
        consent_settings = cur.fetchone()
        require_consent = consent_settings[0] if consent_settings else False
        whitelist_mode = consent_settings[1] if consent_settings else False

        # Get whitelist/blacklist counts
        cur.execute("SELECT COUNT(*) FROM sender_whitelist WHERE recipient_email = %s", (session['email'],))
        whitelist_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sender_blacklist WHERE recipient_email = %s", (session['email'],))
        blacklist_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return render_template('dashboard.html',
                             total_emails=total_emails,
                             unread_count=unread_count,
                             has_encryption=has_encryption,
                             require_consent=require_consent,
                             whitelist_mode=whitelist_mode,
                             whitelist_count=whitelist_count,
                             blacklist_count=blacklist_count)

    except Exception as e:
        print(f"Dashboard error: {e}")
        return redirect(url_for('inbox'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email_addr = request.form.get('email')
        password = request.form.get('password')
        use_portid = request.form.get('use_portid', '').lower() == 'true'

        # Try PortID authentication first if enabled
        if portid_service.is_enabled() and use_portid:
            result = portid_service.login(email_addr, password)
            if result and result.get('success'):
                # Look up user's IMAP password from database
                try:
                    conn = get_db()
                    cur = conn.cursor()
                    cur.execute("SELECT email, password FROM users WHERE email = %s AND active = TRUE", (email_addr,))
                    user_data = cur.fetchone()
                    cur.close()
                    conn.close()

                    if user_data and user_data[1]:
                        # Test IMAP connection with database password
                        mail = connect_imap(user_data[0], user_data[1])
                        if mail:
                            mail.logout()
                            session.permanent = True
                            session['email'] = user_data[0]
                            session['password'] = user_data[1]
                            session['auth_type'] = 'portid'
                            session['portid'] = result.get('portid')
                            flash('Login successful via PortID!', 'success')
                            return redirect(url_for('inbox'))
                except Exception as e:
                    print(f"PortID login error: {e}")
                    flash('PortID authentication failed', 'error')
                    return render_template('login.html', portid_enabled=True)

        # Fall back to legacy IMAP authentication
        mail = connect_imap(email_addr, password)
        if mail:
            mail.logout()

            # Load user's encryption keys from database
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute(
                    """SELECT recovery_key, email_private_key_encrypted
                       FROM users WHERE email = %s AND active = TRUE""",
                    (email_addr,)
                )
                key_data = cur.fetchone()
                cur.close()
                conn.close()

                # If user has encryption keys, decrypt private key and store in session
                if key_data and key_data[0] and key_data[1]:
                    recovery_key = key_data[0]
                    encrypted_private_key = key_data[1]

                    # Decrypt private key with recovery key
                    private_key_pem = decrypt_private_key_with_recovery_key(
                        encrypted_private_key,
                        recovery_key
                    )

                    if private_key_pem:
                        # Store decrypted private key in session (encrypted via HTTPS)
                        session['private_key'] = private_key_pem
                        session['has_encryption'] = True
                    else:
                        session['has_encryption'] = False
                else:
                    session['has_encryption'] = False
            except Exception as e:
                print(f"Error loading encryption keys: {e}")
                session['has_encryption'] = False

            session.permanent = True
            session['email'] = email_addr
            session['password'] = password
            session['auth_type'] = 'password'
            flash('Login successful!', 'success')
            return redirect(url_for('inbox'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html', portid_enabled=portid_service.is_enabled())

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        email_addr = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not email_addr or not password:
            flash('Email and password are required', 'error')
            return render_template('register.html')

        if '@' not in email_addr:
            flash('Invalid email address', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('register.html')

        # Extract domain
        domain = email_addr.split('@')[1]

        try:
            conn = get_db()
            cur = conn.cursor()

            # Check if user already exists
            cur.execute("SELECT email FROM users WHERE email = %s", (email_addr,))
            if cur.fetchone():
                flash('Email address already registered', 'error')
                cur.close()
                conn.close()
                return render_template('register.html')

            # Check if domain exists
            cur.execute("SELECT domain FROM domains WHERE domain = %s", (domain,))
            if not cur.fetchone():
                flash(f'Domain {domain} is not configured for this mail server', 'error')
                cur.close()
                conn.close()
                return render_template('register.html')

            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Generate recovery key (32 bytes hex - same as PortID)
            recovery_key = get_random_bytes(32).hex()

            # Generate email encryption keys
            private_key, public_key = generate_email_keypair()
            public_key_pem = serialize_public_key(public_key)
            private_key_pem = serialize_private_key(private_key)

            # Encrypt private key with recovery key
            encrypted_private_key = encrypt_private_key_with_recovery_key(
                private_key_pem, recovery_key
            )

            # Insert user into database
            cur.execute("""
                INSERT INTO users
                (email, password, domain, recovery_key, email_public_key, email_private_key_encrypted, active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            """, (email_addr, hashed_password, domain, recovery_key, public_key_pem, encrypted_private_key))

            # Create default consent settings
            cur.execute("""
                INSERT INTO consent_settings (user_email, require_consent, whitelist_mode)
                VALUES (%s, FALSE, FALSE)
            """, (email_addr,))

            conn.commit()
            cur.close()
            conn.close()

            # Store recovery key in session to show to user
            session['show_recovery_key'] = recovery_key
            session['recovery_email'] = email_addr

            flash('Account created successfully!', 'success')
            return redirect(url_for('show_recovery_key'))

        except Exception as e:
            print(f"Registration error: {e}")
            flash('Error creating account. Please try again.', 'error')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/recovery-key')
def show_recovery_key():
    """Show recovery key to newly registered user"""
    if 'show_recovery_key' not in session:
        return redirect(url_for('login'))

    recovery_key = session.get('show_recovery_key')
    email = session.get('recovery_email')

    return render_template('show_recovery_key.html', recovery_key=recovery_key, email=email)

@app.route('/recovery-key/confirm', methods=['POST'])
def confirm_recovery_key():
    """User confirms they've saved their recovery key"""
    session.pop('show_recovery_key', None)
    session.pop('recovery_email', None)
    flash('You can now log in with your email and password', 'success')
    return redirect(url_for('login'))

@app.route('/api/private-key')
def get_private_key():
    """API endpoint to get user's private key for client-side encryption"""
    if 'email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    if not session.get('has_encryption', False):
        return jsonify({'error': 'Encryption not enabled for this user'}), 404

    private_key = session.get('private_key')
    if not private_key:
        return jsonify({'error': 'Private key not available'}), 404

    return jsonify({
        'private_key': private_key,
        'has_encryption': True
    })

@app.route('/api/pubkey/<email>')
def get_public_key(email):
    """Public key lookup API endpoint"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT email, email_public_key FROM users WHERE email = %s AND active = TRUE",
            (email,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[1]:
            # User exists and has a public key
            return jsonify({
                "email": result[0],
                "public_key": result[1],
                "is_privra": True,
                "encrypted": True
            }), 200
        elif result:
            # User exists but no encryption keys yet
            return jsonify({
                "email": result[0],
                "is_privra": True,
                "encrypted": False,
                "message": "User exists but hasn't set up encryption yet"
            }), 200
        else:
            # User doesn't exist - external email
            return jsonify({
                "email": email,
                "is_privra": False,
                "encrypted": False
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/inbox')
def inbox():
    """View inbox"""
    if 'email' not in session:
        return redirect(url_for('login'))

    mail = connect_imap(session['email'], session['password'])
    if not mail:
        flash('Failed to connect to mail server', 'error')
        return redirect(url_for('login'))

    try:
        mail.select('INBOX')
        # Search for all emails
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()
        email_ids.reverse()  # Show newest first

        emails = []
        # Get last 50 emails
        for email_id in email_ids[:50]:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])

                # Parse email
                subject = decode_mime_words(msg['Subject']) or '(No Subject)'
                from_addr = decode_mime_words(msg['From']) or 'Unknown'
                date_str = msg['Date']

                # Get body for categorization (limited preview to save resources)
                body_preview = get_email_body(msg)[:500]  # First 500 chars

                # Categorize email
                category = categorizer.categorize(subject, from_addr, body_preview)
                category_name = categorizer.get_category_name(category)

                # Parse date
                try:
                    date = email.utils.parsedate_to_datetime(date_str)
                except:
                    date = datetime.now()

                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'date': date.strftime('%Y-%m-%d %H:%M'),
                    'category': category,
                    'category_name': category_name
                })
            except Exception as e:
                print(f"Error parsing email {email_id}: {e}")

        # Filter by category if requested
        filter_category = request.args.get('category', 'all')
        if filter_category != 'all':
            emails = [e for e in emails if e['category'] == filter_category]

        mail.logout()
        return render_template('inbox.html',
                             emails=emails,
                             categories=categorizer.get_all_categories(),
                             current_category=filter_category)

    except Exception as e:
        print(f"Inbox error: {e}")
        flash('Error loading inbox', 'error')
        mail.logout()
        return redirect(url_for('login'))

@app.route('/email/<email_id>')
def view_email(email_id):
    """View individual email"""
    if 'email' not in session:
        return redirect(url_for('login'))

    mail = connect_imap(session['email'], session['password'])
    if not mail:
        flash('Failed to connect to mail server', 'error')
        return redirect(url_for('login'))

    try:
        mail.select('INBOX')
        status, msg_data = mail.fetch(email_id.encode(), '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])

        subject = decode_mime_words(msg['Subject']) or '(No Subject)'
        from_addr = decode_mime_words(msg['From']) or 'Unknown'
        to_addr = decode_mime_words(msg['To']) or 'Unknown'
        date_str = msg['Date']
        body = get_email_body(msg)

        # Check if email is encrypted
        is_encrypted = msg.get('X-Privra-Encrypted', '').lower() == 'true'

        try:
            date = email.utils.parsedate_to_datetime(date_str)
            date_formatted = date.strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_formatted = date_str

        mail.logout()

        return render_template('view_email.html',
                             subject=subject,
                             from_addr=from_addr,
                             to_addr=to_addr,
                             date=date_formatted,
                             body=body,
                             is_encrypted=is_encrypted)

    except Exception as e:
        print(f"View email error: {e}")
        flash('Error loading email', 'error')
        mail.logout()
        return redirect(url_for('inbox'))

@app.route('/compose', methods=['GET', 'POST'])
def compose():
    """Compose and send email"""
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        to_addr = request.form.get('to')
        subject = request.form.get('subject')
        body = request.form.get('body')
        is_encrypted = request.form.get('encrypted', 'false') == 'true'
        encrypted_body = request.form.get('encrypted_body', '')

        if not to_addr or not subject:
            flash('Please fill in To and Subject fields', 'error')
            return render_template('compose.html')

        # Use encrypted body if available, otherwise use plaintext
        email_body = encrypted_body if is_encrypted else body

        # Connect to SMTP
        smtp = connect_smtp(session['email'], session['password'])
        if not smtp:
            flash('Failed to connect to mail server', 'error')
            return render_template('compose.html')

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = session['email']
            msg['To'] = to_addr
            msg['Subject'] = subject

            # Add encryption header if encrypted
            if is_encrypted:
                msg['X-Privra-Encrypted'] = 'true'

            msg.attach(MIMEText(email_body, 'plain'))

            # Send email
            smtp.send_message(msg)
            smtp.quit()

            if is_encrypted:
                flash('Encrypted email sent successfully! 🔒', 'success')
            else:
                flash('Email sent successfully!', 'success')
            return redirect(url_for('inbox'))

        except Exception as e:
            print(f"Send email error: {e}")
            flash(f'Error sending email: {str(e)}', 'error')
            smtp.quit()
            return render_template('compose.html')

    return render_template('compose.html')

@app.route('/settings/consent', methods=['GET', 'POST'])
def consent_settings():
    """Manage consent and whitelist settings"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    if request.method == 'POST':
        # Update consent settings
        require_consent = request.form.get('require_consent') == 'on'
        whitelist_mode = request.form.get('whitelist_mode') == 'on'

        try:
            conn = get_db()
            cur = conn.cursor()

            # Upsert consent settings
            cur.execute("""
                INSERT INTO consent_settings (user_email, require_consent, whitelist_mode)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    require_consent = EXCLUDED.require_consent,
                    whitelist_mode = EXCLUDED.whitelist_mode,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_email, require_consent, whitelist_mode))

            conn.commit()
            cur.close()
            conn.close()

            flash('Consent settings updated successfully!', 'success')
        except Exception as e:
            print(f"Error updating consent settings: {e}")
            flash('Error updating settings', 'error')

        return redirect(url_for('consent_settings'))

    # Get current settings
    try:
        conn = get_db()
        cur = conn.cursor()

        # Get consent settings
        cur.execute("""
            SELECT require_consent, whitelist_mode
            FROM consent_settings
            WHERE user_email = %s
        """, (user_email,))
        settings = cur.fetchone()

        # Get whitelist
        cur.execute("""
            SELECT id, sender_email, sender_domain, note, created_at
            FROM sender_whitelist
            WHERE recipient_email = %s
            ORDER BY created_at DESC
        """, (user_email,))
        whitelist = cur.fetchall()

        # Get blacklist
        cur.execute("""
            SELECT id, sender_email, sender_domain, reason, created_at
            FROM sender_blacklist
            WHERE recipient_email = %s
            ORDER BY created_at DESC
        """, (user_email,))
        blacklist = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('consent_settings.html',
                             require_consent=settings[0] if settings else False,
                             whitelist_mode=settings[1] if settings else False,
                             whitelist=whitelist,
                             blacklist=blacklist)

    except Exception as e:
        print(f"Error loading consent settings: {e}")
        flash('Error loading settings', 'error')
        return redirect(url_for('inbox'))

@app.route('/settings/whitelist/add', methods=['POST'])
def add_whitelist():
    """Add sender to whitelist"""
    if 'email' not in session:
        return redirect(url_for('login'))

    sender = request.form.get('sender', '').strip()
    note = request.form.get('note', '').strip()

    if not sender:
        flash('Sender email is required', 'error')
        return redirect(url_for('consent_settings'))

    try:
        conn = get_db()
        cur = conn.cursor()

        # Determine if it's a domain or email
        if sender.startswith('@'):
            # Domain whitelist
            cur.execute("""
                INSERT INTO sender_whitelist (recipient_email, sender_domain, note)
                VALUES (%s, %s, %s)
                ON CONFLICT (recipient_email, sender_email) DO NOTHING
            """, (session['email'], sender[1:], note))
        else:
            # Email whitelist
            cur.execute("""
                INSERT INTO sender_whitelist (recipient_email, sender_email, note)
                VALUES (%s, %s, %s)
                ON CONFLICT (recipient_email, sender_email) DO NOTHING
            """, (session['email'], sender, note))

        conn.commit()
        cur.close()
        conn.close()

        flash(f'Added {sender} to whitelist', 'success')
    except Exception as e:
        print(f"Error adding to whitelist: {e}")
        flash('Error adding to whitelist', 'error')

    return redirect(url_for('consent_settings'))

@app.route('/settings/whitelist/remove/<int:id>', methods=['POST'])
def remove_whitelist(id):
    """Remove sender from whitelist"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM sender_whitelist
            WHERE id = %s AND recipient_email = %s
        """, (id, session['email']))
        conn.commit()
        cur.close()
        conn.close()

        flash('Removed from whitelist', 'success')
    except Exception as e:
        print(f"Error removing from whitelist: {e}")
        flash('Error removing from whitelist', 'error')

    return redirect(url_for('consent_settings'))

@app.route('/settings/blacklist/add', methods=['POST'])
def add_blacklist():
    """Add sender to blacklist"""
    if 'email' not in session:
        return redirect(url_for('login'))

    sender = request.form.get('sender', '').strip()
    reason = request.form.get('reason', '').strip()

    if not sender:
        flash('Sender email is required', 'error')
        return redirect(url_for('consent_settings'))

    try:
        conn = get_db()
        cur = conn.cursor()

        # Determine if it's a domain or email
        if sender.startswith('@'):
            # Domain blacklist
            cur.execute("""
                INSERT INTO sender_blacklist (recipient_email, sender_domain, reason)
                VALUES (%s, %s, %s)
            """, (session['email'], sender[1:], reason))
        else:
            # Email blacklist
            cur.execute("""
                INSERT INTO sender_blacklist (recipient_email, sender_email, reason)
                VALUES (%s, %s, %s)
            """, (session['email'], sender, reason))

        conn.commit()
        cur.close()
        conn.close()

        flash(f'Added {sender} to blacklist', 'success')
    except Exception as e:
        print(f"Error adding to blacklist: {e}")
        flash('Error adding to blacklist', 'error')

    return redirect(url_for('consent_settings'))

@app.route('/settings/blacklist/remove/<int:id>', methods=['POST'])
def remove_blacklist(id):
    """Remove sender from blacklist"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM sender_blacklist
            WHERE id = %s AND recipient_email = %s
        """, (id, session['email']))
        conn.commit()
        cur.close()
        conn.close()

        flash('Removed from blacklist', 'success')
    except Exception as e:
        print(f"Error removing from blacklist: {e}")
        flash('Error removing from blacklist', 'error')

    return redirect(url_for('consent_settings'))

@app.route('/settings/account')
def account_settings():
    """Account settings page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cur = conn.cursor()

        # Get user info
        cur.execute("""
            SELECT email, domain, recovery_key, auth_type, active, created_at
            FROM users
            WHERE email = %s
        """, (session['email'],))
        user_info = cur.fetchone()

        cur.close()
        conn.close()

        if not user_info:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))

        return render_template('account_settings.html',
                             email=user_info[0],
                             domain=user_info[1],
                             has_recovery_key=bool(user_info[2]),
                             auth_type=user_info[3] or 'password',
                             active=user_info[4],
                             created_at=user_info[5],
                             has_encryption=session.get('has_encryption', False))

    except Exception as e:
        print(f"Error loading account settings: {e}")
        flash('Error loading account settings', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
