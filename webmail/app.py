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
from crypto_utils import decrypt_private_key_with_recovery_key

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Mail server settings
IMAP_HOST = os.getenv('IMAP_HOST', 'dovecot')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
SMTP_HOST = os.getenv('SMTP_HOST', 'postfix')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

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
    """Home page - redirect to inbox if logged in"""
    if 'email' in session:
        return redirect(url_for('inbox'))
    return redirect(url_for('login'))

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

                # Parse date
                try:
                    date = email.utils.parsedate_to_datetime(date_str)
                except:
                    date = datetime.now()

                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'date': date.strftime('%Y-%m-%d %H:%M')
                })
            except Exception as e:
                print(f"Error parsing email {email_id}: {e}")

        mail.logout()
        return render_template('inbox.html', emails=emails)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
