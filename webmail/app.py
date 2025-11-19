#!/usr/bin/env python3
"""Simple Webmail Client for Privra Mail Server"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from datetime import datetime, timedelta
import os
import psycopg2
from werkzeug.utils import secure_filename
from PIL import Image
import hashlib
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
import sys
sys.path.append('/app')
from nft_verification_service import nft_verification_service as nft_service
from reputation_service import reputation_service
from wallet_service import wallet_service
from folder_service import folder_service
from ai_labeling import ai_labeling_service
from session_manager import session_manager
from alias_service import alias_service
from email_sanitizer import email_sanitizer

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# File upload configuration
app.config['UPLOAD_FOLDER'] = '/app/static/uploads/avatars'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

def get_sender_verification(email_addr):
    """Get verification status for a sender"""
    try:
        # Extract just email if it has name (e.g., "Name <email@domain.com>")
        if '<' in email_addr and '>' in email_addr:
            email_addr = email_addr.split('<')[1].split('>')[0].strip()

        conn = get_db()
        cur = conn.cursor()

        # Check user profile for verification
        cur.execute("""
            SELECT
                up.is_verified,
                up.verification_method,
                up.nft_badge_mint,
                up.display_name,
                up.avatar_url,
                rs.reputation_level,
                rs.total_score
            FROM user_profiles up
            LEFT JOIN reputation_scores rs ON up.user_email = rs.user_email
            WHERE up.user_email = %s
        """, (email_addr,))

        result = cur.fetchone()

        # Check domain verification
        cur.execute("""
            SELECT domain, verified
            FROM domain_verifications
            WHERE user_email = %s AND verified = TRUE
            LIMIT 1
        """, (email_addr,))

        domain_verified = cur.fetchone()

        cur.close()
        conn.close()

        if not result:
            return {
                'verified': False,
                'method': None,
                'reputation_level': 'new',
                'score': 0,
                'display_name': None,
                'avatar_url': None,
                'badges': []
            }

        is_verified, method, nft_mint, display_name, avatar_url, rep_level, score = result

        # Determine badges
        badges = []
        if is_verified:
            if method == 'nft' and nft_mint:
                badges.append({'type': 'nft', 'text': 'NFT Verified', 'icon': '🖼️', 'color': '#8b5cf6'})
            if domain_verified:
                badges.append({'type': 'domain', 'text': f'Domain: {domain_verified[0]}', 'icon': '✅', 'color': '#10b981'})

        # Reputation badge
        if rep_level and rep_level != 'new':
            rep_colors = {
                'trusted': '#3b82f6',
                'verified': '#10b981',
                'elite': '#f59e0b',
                'legendary': '#dc2626'
            }
            badges.append({
                'type': 'reputation',
                'text': rep_level.capitalize(),
                'icon': '⭐',
                'color': rep_colors.get(rep_level, '#6b7280')
            })

        return {
            'verified': is_verified or bool(domain_verified),
            'method': method,
            'reputation_level': rep_level or 'new',
            'score': score or 0,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'badges': badges
        }

    except Exception as e:
        print(f"Error checking verification: {e}")
        return {
            'verified': False,
            'method': None,
            'reputation_level': 'new',
            'score': 0,
            'display_name': None,
            'avatar_url': None,
            'badges': []
        }

def get_email_body(msg):
    """
    Extract and sanitize email body from message.
    Removes tracking pixels and rewrites suspicious links.
    """
    body = ""
    is_html = False

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
                    is_html = True
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='replace')
            # Check if it's HTML
            if '<html' in body.lower() or '<body' in body.lower():
                is_html = True
        except:
            body = msg.get_payload()

    # Sanitize HTML emails
    if is_html and body:
        user_email = session.get('email', '')
        sanitization_result = email_sanitizer.sanitize_html(body, user_email)

        # Store sanitization stats in session for display
        session['last_sanitization'] = {
            'removed_pixels': sanitization_result['removed_pixels'],
            'rewritten_links': sanitization_result['rewritten_links'],
            'removed_scripts': sanitization_result['removed_scripts'],
            'warnings': sanitization_result['warnings']
        }

        body = sanitization_result['sanitized_html']
    else:
        # Clear sanitization stats for plain text emails
        session.pop('last_sanitization', None)

    return body

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_avatar_image(image_file, user_email):
    """Process and save avatar image"""
    # Generate unique filename
    file_hash = hashlib.md5(f"{user_email}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    ext = image_file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{file_hash}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Open and process image
    img = Image.open(image_file)

    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background

    # Resize to 400x400 (square avatar)
    img = img.resize((400, 400), Image.Resampling.LANCZOS)

    # Save optimized image
    img.save(filepath, quality=85, optimize=True)

    # Return relative URL path
    return f'/static/uploads/avatars/{filename}'

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

        # Authenticate via IMAP
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

            # Create session with device tracking (like Gmail)
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.remote_addr
            session_token = session_manager.create_session(email_addr, user_agent, ip_address)

            session.permanent = True
            session['email'] = email_addr
            session['password'] = password
            session['auth_type'] = 'password'
            session['session_token'] = session_token  # Store for session management
            flash('Login successful!', 'success')
            return redirect(url_for('inbox'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

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

            # Create default user profile
            cur.execute("""
                INSERT INTO user_profiles (user_email, display_name, profile_type)
                VALUES (%s, %s, 'individual')
            """, (email_addr, email_addr.split('@')[0]))

            conn.commit()
            cur.close()
            conn.close()

            # Generate multi-chain wallets for the user
            wallet_addresses = {}
            try:
                wallet_result = wallet_service.generate_wallets(email_addr, password)
                if wallet_result['success']:
                    print(f"✓ Wallets generated for {email_addr}")
                    print(f"  Solana: {wallet_result['wallets']['solana']['address']}")
                    print(f"  EVM: {wallet_result['wallets']['ethereum']['address']}")
                    wallet_addresses = {
                        'solana': wallet_result['wallets']['solana']['address'],
                        'evm': wallet_result['wallets']['ethereum']['address']
                    }
                else:
                    print(f"⚠ Warning: Wallet generation failed for {email_addr}: {wallet_result.get('error')}")
            except Exception as wallet_error:
                print(f"⚠ Warning: Wallet generation error for {email_addr}: {wallet_error}")
                # Don't fail registration if wallet generation fails

            # Create default email folders/categories
            try:
                if folder_service.create_default_folders(email_addr):
                    print(f"✓ Default folders created for {email_addr}")
                else:
                    print(f"⚠ Warning: Folder creation failed for {email_addr}")
            except Exception as folder_error:
                print(f"⚠ Warning: Folder creation error for {email_addr}: {folder_error}")
                # Don't fail registration if folder creation fails

            # ========== PORTID ZERO-KNOWLEDGE KEYRING ==========
            # This is the critical security feature:
            # We create an encrypted keyring containing ALL user keys.
            # The keyring is encrypted client-side with user's password.
            # Server stores encrypted blob - can NEVER decrypt it.
            # User needs recovery_key to access from new device.

            portid_recovery_key = None
            if portid_service.is_enabled():
                try:
                    # Create PortID encrypted storage
                    portid_result = portid_service.sign_up(email_addr, password)

                    if portid_result:
                        portid_recovery_key = portid_result['recovery_key']

                        # Create keyring with all sensitive keys
                        keyring = {
                            'email_private_key': private_key_pem,
                            'email_public_key': public_key_pem,
                            'wallets': wallet_addresses,
                            'preferences': {
                                'theme': 'light',
                                'language': 'en'
                            }
                        }

                        # Backup encrypted keyring to server
                        if portid_service.backup(keyring):
                            print(f"✓ Keyring backed up via PortID for {email_addr}")
                        else:
                            print(f"⚠ Warning: PortID backup failed for {email_addr}")

                except Exception as portid_error:
                    print(f"⚠ Warning: PortID setup error for {email_addr}: {portid_error}")

            # Store BOTH recovery keys in session to show to user
            # The original recovery_key encrypts the email private key in DB (fallback)
            # The portid_recovery_key allows restoring full keyring on new device (primary)
            session['show_recovery_key'] = recovery_key
            session['portid_recovery_key'] = portid_recovery_key
            session['recovery_email'] = email_addr

            flash('Account created successfully! Multi-chain wallet & encrypted keyring ready.', 'success')
            return redirect(url_for('show_recovery_key'))

        except Exception as e:
            import traceback
            print(f"Registration error: {e}")
            traceback.print_exc()
            # Log more detailed error for debugging
            error_msg = str(e)
            if 'consent_settings' in error_msg.lower():
                print("ERROR: consent_settings table might not exist. Run init_db.py to create required tables.")
            elif 'sender_whitelist' in error_msg.lower() or 'sender_blacklist' in error_msg.lower():
                print("ERROR: consent system tables missing. Run init_db.py to create required tables.")
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


@app.route('/api/portid/backup', methods=['POST'])
def portid_backup():
    """
    PortID backup endpoint - stores encrypted user data

    The PortID SDK encrypts data client-side and POSTs it here.
    We store the encrypted blob in the database without ever decrypting it.
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        app_id = data.get('app_id')
        encrypted_data = data.get('encrypted_data')

        if not user_email or not app_id or not encrypted_data:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db()
        cur = conn.cursor()

        # Insert or update encrypted backup
        cur.execute("""
            INSERT INTO portid_backups (user_email, app_id, encrypted_data, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_email)
            DO UPDATE SET
                encrypted_data = EXCLUDED.encrypted_data,
                updated_at = CURRENT_TIMESTAMP
        """, (user_email, app_id, encrypted_data))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "message": "Backup stored"}), 200

    except Exception as e:
        print(f"PortID backup error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/portid/restore', methods=['POST'])
def portid_restore():
    """
    PortID restore endpoint - retrieves encrypted user data

    The PortID SDK fetches the encrypted blob from here and decrypts it client-side.
    We never see the decrypted data.
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        app_id = data.get('app_id')

        if not user_email or not app_id:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db()
        cur = conn.cursor()

        # Fetch encrypted backup
        cur.execute("""
            SELECT encrypted_data, updated_at
            FROM portid_backups
            WHERE user_email = %s AND app_id = %s
        """, (user_email, app_id))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return jsonify({
                "success": True,
                "encrypted_data": result[0],
                "updated_at": result[1].isoformat() if result[1] else None
            }), 200
        else:
            return jsonify({"error": "No backup found"}), 404

    except Exception as e:
        print(f"PortID restore error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    """Logout"""
    # Revoke current session
    if 'session_token' in session:
        session_manager.revoke_session(session['session_token'], session.get('email'))

    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/sessions')
def sessions():
    """View active sessions (like Gmail's device activity)"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    current_token = session.get('session_token')

    # Get all active sessions for user
    all_sessions = session_manager.get_user_sessions(user_email)

    # Mark current session
    for sess in all_sessions:
        sess['is_current'] = (sess['session_token'] == current_token)

    return render_template('sessions.html', sessions=all_sessions)


@app.route('/sessions/revoke', methods=['POST'])
def revoke_session():
    """Revoke a specific session"""
    if 'email' not in session:
        return redirect(url_for('login'))

    session_token = request.form.get('session_token')
    user_email = session['email']

    if session_manager.revoke_session(session_token, user_email):
        flash('Session revoked successfully', 'success')
    else:
        flash('Failed to revoke session', 'error')

    return redirect(url_for('sessions'))


@app.route('/sessions/revoke-all', methods=['POST'])
def revoke_all_sessions():
    """Revoke all sessions except current one"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    current_token = session.get('session_token')

    session_manager.revoke_all_sessions(user_email, except_token=current_token)
    flash('All other sessions have been signed out', 'success')

    return redirect(url_for('sessions'))


# ==================== ALIAS MANAGEMENT ROUTES (Priority 1: Privacy Shield) ====================

@app.route('/aliases')
def aliases():
    """Alias management page - Dynamic Shield Aliasing"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    try:
        # Get all aliases (including burned ones in separate section)
        active_aliases = [a for a in alias_service.list_aliases(user_email, include_burned=False)]
        burned_aliases = [a for a in alias_service.list_aliases(user_email, include_burned=True) if a['burned_at']]

        return render_template('aliases.html',
                             active_aliases=active_aliases,
                             burned_aliases=burned_aliases)
    except Exception as e:
        flash(f'Error loading aliases: {str(e)}', 'error')
        return redirect(url_for('inbox'))


@app.route('/aliases/generate', methods=['POST'])
def generate_alias():
    """Generate a new alias - API endpoint"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']

    try:
        # Get parameters from request
        data = request.get_json()
        service_name = data.get('service_name', 'Unknown Service')
        custom_prefix = data.get('custom_prefix')
        description = data.get('description')

        # Generate alias
        result = alias_service.generate_alias(
            user_email=user_email,
            service_name=service_name,
            custom_prefix=custom_prefix,
            description=description
        )

        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/aliases/<int:alias_id>/burn', methods=['POST'])
def burn_alias(alias_id):
    """Burn an alias (irreversible) - Kill Switch"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']

    try:
        success = alias_service.burn_alias(alias_id, user_email)

        if success:
            flash('🔥 Alias burned successfully. Senders will now receive 550 errors.', 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Alias not found or already burned'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/aliases/<int:alias_id>', methods=['GET'])
def get_alias(alias_id):
    """Get alias details - API endpoint"""
    if 'email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_email = session['email']

    try:
        alias = alias_service.get_alias(alias_id, user_email)

        if alias:
            return jsonify(alias)
        else:
            return jsonify({'error': 'Alias not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== SAFE LINK PROXY (Priority 1: Active Sanitization) ====================

@app.route('/click/safe')
def safe_link_proxy():
    """
    Safe link proxy endpoint.
    Shows warning page before redirecting to potentially suspicious links.
    """
    encoded_url = request.args.get('url')

    if not encoded_url:
        flash('Missing URL parameter', 'error')
        return redirect(url_for('inbox'))

    # Decode the original URL
    original_url = email_sanitizer.decode_safe_url(encoded_url)

    # Render warning page (user can choose to continue or go back)
    return render_template('safe_link_warning.html',
                         original_url=original_url)


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

                # Get sender verification info
                verification = get_sender_verification(from_addr)

                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'date': date.strftime('%Y-%m-%d %H:%M'),
                    'category': category,
                    'category_name': category_name,
                    'verification': verification
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

        # Get sender verification info
        verification = get_sender_verification(from_addr)

        mail.logout()

        return render_template('view_email.html',
                             subject=subject,
                             from_addr=from_addr,
                             to_addr=to_addr,
                             date=date_formatted,
                             body=body,
                             is_encrypted=is_encrypted,
                             verification=verification)

    except Exception as e:
        print(f"View email error: {e}")
        flash('Error loading email', 'error')
        mail.logout()
        return redirect(url_for('inbox'))

@app.route('/report/abuse', methods=['POST'])
def report_abuse():
    """Report email as spam/abuse"""
    if 'email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from reputation_service import reputation_service

        reported_email = request.form.get('reported_email')
        reason = request.form.get('reason', 'spam')
        details = request.form.get('details', '')

        if not reported_email:
            return jsonify({'error': 'No email address provided'}), 400

        result = reputation_service.process_user_report(
            reporter_email=session['email'],
            reported_email=reported_email,
            reason=reason,
            details=details
        )

        if result.get('success'):
            flash(f'Report submitted. Thank you for keeping Privra safe.', 'success')
            return jsonify({'success': True, 'message': 'Report submitted'})
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Failed to submit report')}), 400

    except Exception as e:
        print(f"Report abuse error: {e}")
        return jsonify({'error': 'Failed to submit report'}), 500

@app.route('/reputation/check')
def check_reputation():
    """Check own reputation (for dashboard)"""
    if 'email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        from reputation_service import reputation_service
        rep = reputation_service.get_user_reputation(session['email'])
        return jsonify(rep)
    except Exception as e:
        print(f"Check reputation error: {e}")
        return jsonify({'error': 'Failed to check reputation'}), 500

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
        require_payment = request.form.get('require_payment') == 'on'
        payment_amount = request.form.get('payment_amount', '0').strip()
        payment_address = request.form.get('payment_address', '').strip()

        # Convert payment_amount to float
        try:
            payment_amount_float = float(payment_amount) if payment_amount else 0.0
        except ValueError:
            payment_amount_float = 0.0

        try:
            conn = get_db()
            cur = conn.cursor()

            # Upsert consent settings
            cur.execute("""
                INSERT INTO consent_settings (user_email, require_consent, whitelist_mode, require_payment, payment_amount, payment_address)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    require_consent = EXCLUDED.require_consent,
                    whitelist_mode = EXCLUDED.whitelist_mode,
                    require_payment = EXCLUDED.require_payment,
                    payment_amount = EXCLUDED.payment_amount,
                    payment_address = EXCLUDED.payment_address,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_email, require_consent, whitelist_mode, require_payment, payment_amount_float, payment_address))

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
            SELECT require_consent, whitelist_mode, require_payment, payment_amount, payment_address
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
                             require_payment=settings[2] if settings else False,
                             payment_amount=settings[3] if settings else 0.0,
                             payment_address=settings[4] if settings else '',
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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """User profile management"""
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    if request.method == 'POST':
        # Update profile
        display_name = request.form.get('display_name', '').strip()
        bio = request.form.get('bio', '').strip()
        profile_type = request.form.get('profile_type', 'individual')
        org_name = request.form.get('org_name', '').strip() if profile_type == 'organization' else None
        org_domain = request.form.get('org_domain', '').strip() if profile_type == 'organization' else None

        try:
            conn = get_db()
            cur = conn.cursor()

            # Upsert user profile
            cur.execute("""
                INSERT INTO user_profiles
                (user_email, display_name, bio, profile_type, organization_name, organization_domain)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    bio = EXCLUDED.bio,
                    profile_type = EXCLUDED.profile_type,
                    organization_name = EXCLUDED.organization_name,
                    organization_domain = EXCLUDED.organization_domain,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_email, display_name, bio, profile_type, org_name, org_domain))

            conn.commit()
            cur.close()
            conn.close()

            flash('Profile updated successfully!', 'success')
        except Exception as e:
            print(f"Error updating profile: {e}")
            flash('Error updating profile', 'error')

        return redirect(url_for('profile'))

    # Get profile data
    try:
        conn = get_db()
        cur = conn.cursor()

        # Get user profile
        cur.execute("""
            SELECT display_name, bio, avatar_url, profile_type, organization_name,
                   organization_domain, is_verified, verification_method, nft_badge_mint
            FROM user_profiles
            WHERE user_email = %s
        """, (user_email,))
        profile = cur.fetchone()

        # Get wallets
        cur.execute("""
            SELECT id, wallet_address, wallet_type, is_primary, is_verified, created_at
            FROM user_wallets
            WHERE user_email = %s
            ORDER BY is_primary DESC, created_at DESC
        """, (user_email,))
        wallets = cur.fetchall()

        # Get reputation
        reputation = reputation_service.get_reputation(user_email)
        trust_percentage = reputation_service.calculate_trust_percentage(user_email)

        # Get domain verifications
        cur.execute("""
            SELECT domain, verification_token, verified, verified_at
            FROM domain_verifications
            WHERE user_email = %s
            ORDER BY created_at DESC
        """, (user_email,))
        domains = cur.fetchall()

        cur.close()
        conn.close()

        profile_data = None
        if profile:
            profile_data = {
                'display_name': profile[0],
                'bio': profile[1],
                'avatar_url': profile[2],
                'profile_type': profile[3] or 'individual',
                'organization_name': profile[4],
                'organization_domain': profile[5],
                'is_verified': profile[6],
                'verification_method': profile[7],
                'nft_badge_mint': profile[8]
            }

        return render_template('profile.html',
                             profile=profile_data,
                             wallets=wallets,
                             reputation=reputation,
                             trust_percentage=trust_percentage,
                             domains=domains)

    except Exception as e:
        print(f"Error loading profile: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('dashboard'))

@app.route('/profile/wallet/add', methods=['POST'])
def add_wallet():
    """Add wallet to user profile"""
    if 'email' not in session:
        return redirect(url_for('login'))

    wallet_address = request.form.get('wallet_address', '').strip()
    wallet_type = request.form.get('wallet_type', 'solana')

    if not wallet_address:
        flash('Wallet address is required', 'error')
        return redirect(url_for('profile'))

    try:
        conn = get_db()
        cur = conn.cursor()

        # Check if this is the first wallet (make it primary)
        cur.execute("""
            SELECT COUNT(*) FROM user_wallets WHERE user_email = %s
        """, (session['email'],))
        wallet_count = cur.fetchone()[0]
        is_primary = (wallet_count == 0)

        # Insert wallet
        cur.execute("""
            INSERT INTO user_wallets (user_email, wallet_address, wallet_type, is_primary)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_email, wallet_address) DO NOTHING
        """, (session['email'], wallet_address, wallet_type, is_primary))

        conn.commit()
        cur.close()
        conn.close()

        flash(f'Wallet {wallet_address[:8]}... added successfully!', 'success')
    except Exception as e:
        print(f"Error adding wallet: {e}")
        flash('Error adding wallet', 'error')

    return redirect(url_for('profile'))

@app.route('/profile/wallet/remove/<int:wallet_id>', methods=['POST'])
def remove_wallet(wallet_id):
    """Remove wallet from user profile"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM user_wallets
            WHERE id = %s AND user_email = %s
        """, (wallet_id, session['email']))

        conn.commit()
        cur.close()
        conn.close()

        flash('Wallet removed successfully!', 'success')
    except Exception as e:
        print(f"Error removing wallet: {e}")
        flash('Error removing wallet', 'error')

    return redirect(url_for('profile'))

@app.route('/profile/upload-avatar', methods=['POST'])
def upload_avatar():
    """Upload and set profile avatar image"""
    if 'email' not in session:
        return redirect(url_for('login'))

    # Check if file was uploaded
    if 'avatar' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile'))

    file = request.files['avatar']

    # Check if filename is empty
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile'))

    # Validate file type
    if not allowed_file(file.filename):
        flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP', 'error')
        return redirect(url_for('profile'))

    try:
        # Process and save image
        avatar_url = process_avatar_image(file, session['email'])

        # Update database
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO user_profiles (user_email, avatar_url)
            VALUES (%s, %s)
            ON CONFLICT (user_email)
            DO UPDATE SET
                avatar_url = EXCLUDED.avatar_url,
                updated_at = CURRENT_TIMESTAMP
        """, (session['email'], avatar_url))

        conn.commit()
        cur.close()
        conn.close()

        flash('Profile picture updated successfully!', 'success')

    except Exception as e:
        print(f"Error uploading avatar: {e}")
        flash('Error uploading image. Please try again.', 'error')

    return redirect(url_for('profile'))

@app.route('/profile/verify-nft', methods=['POST'])
def verify_nft():
    """Set NFT as profile avatar"""
    if 'email' not in session:
        return redirect(url_for('login'))

    nft_mint = request.form.get('nft_mint', '').strip()
    wallet_address = request.form.get('wallet_address', '').strip()

    if not nft_mint or not wallet_address:
        flash('NFT mint address and wallet address are required', 'error')
        return redirect(url_for('profile'))

    try:
        # Set NFT as avatar
        success, message = nft_service.set_nft_as_avatar(
            session['email'],
            nft_mint,
            wallet_address
        )

        if success:
            # Record reputation event
            reputation_service.record_event(
                session['email'],
                'nft_verified',
                'verification',
                'NFT set as profile avatar',
                {'nft_mint': nft_mint, 'wallet': wallet_address}
            )
            flash(message, 'success')
        else:
            flash(message, 'error')

    except Exception as e:
        print(f"Error verifying NFT: {e}")
        flash('Error verifying NFT', 'error')

    return redirect(url_for('profile'))

@app.route('/profile/verify-domain/start', methods=['POST'])
def start_domain_verification():
    """Generate domain verification token"""
    if 'email' not in session:
        return redirect(url_for('login'))

    domain = request.form.get('domain', '').strip()

    if not domain:
        flash('Domain is required', 'error')
        return redirect(url_for('profile'))

    try:
        # Generate verification token
        token = nft_service.generate_domain_verification_token(session['email'], domain)

        flash(f'Add this TXT record to {domain}: privra-verify={token}', 'success')
    except Exception as e:
        print(f"Error generating domain token: {e}")
        flash('Error generating verification token', 'error')

    return redirect(url_for('profile'))

@app.route('/profile/verify-domain/check', methods=['POST'])
def check_domain_verification():
    """Verify domain ownership via DNS"""
    if 'email' not in session:
        return redirect(url_for('login'))

    domain = request.form.get('domain', '').strip()

    if not domain:
        flash('Domain is required', 'error')
        return redirect(url_for('profile'))

    try:
        # Verify domain
        success, message = nft_service.verify_domain_ownership(session['email'], domain)

        if success:
            # Record reputation event
            reputation_service.record_event(
                session['email'],
                'domain_verified',
                'verification',
                f'Domain {domain} verified',
                {'domain': domain}
            )
            flash(message, 'success')
        else:
            flash(message, 'error')

    except Exception as e:
        print(f"Error verifying domain: {e}")
        flash('Error verifying domain', 'error')

    return redirect(url_for('profile'))

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory('/app/static/uploads', filename)

@app.route('/wallet')
def wallet():
    """Multi-chain wallet management"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        # Get user's wallets
        wallet_result = wallet_service.get_wallets(session['email'])

        if not wallet_result['success']:
            flash('No wallets found. Please contact support.', 'error')
            return redirect(url_for('profile'))

        return render_template('wallet.html', wallets=wallet_result['wallets'])

    except Exception as e:
        print(f"Error loading wallet: {e}")
        flash('Error loading wallet', 'error')
        return redirect(url_for('profile'))

@app.route('/wallet/reveal', methods=['POST'])
def reveal_private_key_route():
    """Reveal private key for a specific chain"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    chain = request.form.get('chain', '').lower()
    password = request.form.get('password', '')

    if not chain or not password:
        return jsonify({'success': False, 'error': 'Chain and password required'}), 400

    try:
        result = wallet_service.reveal_private_key(session['email'], password, chain)
        return jsonify(result)
    except Exception as e:
        print(f"Error revealing private key: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wallet/export', methods=['POST'])
def export_wallet_route():
    """Export wallet data (JSON format)"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    password = request.form.get('password', '')

    if not password:
        return jsonify({'success': False, 'error': 'Password required'}), 400

    try:
        result = wallet_service.export_wallet(session['email'], password, format='json')

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        print(f"Error exporting wallet: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/folders')
def folders():
    """Get user's folders (for inbox sidebar)"""
    if 'email' not in session:
        return redirect(url_for('login'))

    try:
        folders_list = folder_service.get_folders(session['email'])
        return jsonify({'success': True, 'folders': folders_list})
    except Exception as e:
        print(f"Error getting folders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/folders/create', methods=['POST'])
def create_folder():
    """Create a custom folder/label"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    folder_name = request.form.get('folder_name', '').strip()
    color = request.form.get('color', '#667eea')
    icon = request.form.get('icon', '📁')

    if not folder_name:
        return jsonify({'success': False, 'error': 'Folder name required'}), 400

    try:
        success, message = folder_service.create_custom_folder(
            session['email'],
            folder_name,
            color,
            icon
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        print(f"Error creating folder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/folders/delete/<int:folder_id>', methods=['POST'])
def delete_folder(folder_id):
    """Delete a custom folder"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        success, message = folder_service.delete_custom_folder(session['email'], folder_id)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        print(f"Error deleting folder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/email/<message_id>/label', methods=['POST'])
def label_email(message_id):
    """Add a label to an email"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    label_name = request.form.get('label_name', '').strip()

    if not label_name:
        return jsonify({'success': False, 'error': 'Label name required'}), 400

    try:
        success = folder_service.add_label_to_email(
            session['email'],
            message_id,
            label_name,
            ai_generated=False
        )

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add label'}), 500

    except Exception as e:
        print(f"Error labeling email: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/email/<message_id>/unlabel', methods=['POST'])
def unlabel_email(message_id):
    """Remove a label from an email"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    label_name = request.form.get('label_name', '').strip()

    if not label_name:
        return jsonify({'success': False, 'error': 'Label name required'}), 400

    try:
        success = folder_service.remove_label_from_email(
            session['email'],
            message_id,
            label_name
        )

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to remove label'}), 500

    except Exception as e:
        print(f"Error unlabeling email: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# AI Email Labeling Routes
# ============================================

@app.route('/email/auto-label', methods=['POST'])
def auto_label_emails():
    """Automatically label emails in inbox using AI"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Connect to IMAP
        mail = connect_imap(session['email'], session['password'])
        if not mail:
            return jsonify({'success': False, 'error': 'Failed to connect to mail server'}), 500

        mail.select('INBOX')
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        labeled_count = 0
        spam_count = 0
        important_count = 0

        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                # Get subject and sender
                subject = email_message.get('Subject', '')
                if subject:
                    subject, encoding = decode_header(subject)[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or 'utf-8', errors='ignore')

                from_addr = email_message.get('From', '')
                if from_addr:
                    from_header = decode_header(from_addr)[0]
                    if isinstance(from_header[0], bytes):
                        from_addr = from_header[0].decode(from_header[1] or 'utf-8', errors='ignore')

                # Get email body for better analysis
                body = ''
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode('utf-8', errors='ignore')
                                    break
                            except:
                                pass
                else:
                    try:
                        payload = email_message.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    except:
                        pass

                # Limit body length for analysis
                body = body[:1000] if body else ''

                # Analyze with AI
                category = ai_labeling_service.categorize_email(from_addr, subject, body)

                # Add label if not inbox
                if category != 'inbox':
                    message_id = email_id.decode()
                    folder_service.add_label_to_email(
                        session['email'],
                        message_id,
                        category,
                        ai_generated=True
                    )
                    labeled_count += 1

                    if category == 'spam':
                        spam_count += 1
                    elif category == 'important':
                        important_count += 1

            except Exception as e:
                print(f"Error analyzing email {email_id}: {e}")
                continue

        mail.logout()

        return jsonify({
            'success': True,
            'message': f'Labeled {labeled_count} emails ({spam_count} spam, {important_count} important)',
            'labeled': labeled_count,
            'spam': spam_count,
            'important': important_count
        })

    except Exception as e:
        print(f"Error in auto-labeling: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/email/<message_id>/suggest-labels', methods=['GET'])
def suggest_labels(message_id):
    """Get AI suggested labels for a specific email"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Connect to IMAP
        mail = connect_imap(session['email'], session['password'])
        if not mail:
            return jsonify({'success': False, 'error': 'Failed to connect to mail server'}), 500

        mail.select('INBOX')

        # Fetch the specific email
        status, msg_data = mail.fetch(message_id.encode(), '(RFC822)')
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)

        # Get subject and sender
        subject = email_message.get('Subject', '')
        if subject:
            subject, encoding = decode_header(subject)[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8', errors='ignore')

        from_addr = email_message.get('From', '')
        if from_addr:
            from_header = decode_header(from_addr)[0]
            if isinstance(from_header[0], bytes):
                from_addr = from_header[0].decode(from_header[1] or 'utf-8', errors='ignore')

        # Get email body
        body = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break
                    except:
                        pass
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            except:
                pass

        body = body[:1000] if body else ''

        # Analyze with AI
        labels = ai_labeling_service.analyze_email(from_addr, subject, body)
        category = ai_labeling_service.categorize_email(from_addr, subject, body)

        mail.logout()

        return jsonify({
            'success': True,
            'labels': labels,
            'category': category,
            'from': from_addr,
            'subject': subject
        })

    except Exception as e:
        print(f"Error suggesting labels: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# RPC Configuration Routes
# ============================================

@app.route('/settings/rpc')
def rpc_settings():
    """User RPC configuration page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    # Check if user is admin
    cur.execute("SELECT is_admin FROM users WHERE email = %s", (session['email'],))
    is_admin = cur.fetchone()
    is_admin = is_admin[0] if is_admin else False

    # Get user's RPC config or create default
    cur.execute("""
        SELECT use_custom_rpc, solana_rpc_url, ethereum_rpc_url,
               base_rpc_url, polygon_rpc_url, arbitrum_rpc_url, optimism_rpc_url
        FROM user_rpc_config
        WHERE user_email = %s
    """, (session['email'],))

    user_config = cur.fetchone()

    if not user_config:
        # Create default config
        cur.execute("""
            INSERT INTO user_rpc_config (user_email, use_custom_rpc)
            VALUES (%s, FALSE)
            RETURNING use_custom_rpc, solana_rpc_url, ethereum_rpc_url,
                      base_rpc_url, polygon_rpc_url, arbitrum_rpc_url, optimism_rpc_url
        """, (session['email'],))
        user_config = cur.fetchone()
        conn.commit()

    # Get global defaults for reference
    cur.execute("""
        SELECT solana_rpc_url, ethereum_rpc_url, base_rpc_url,
               polygon_rpc_url, arbitrum_rpc_url, optimism_rpc_url
        FROM global_rpc_config
        WHERE is_active = TRUE
        LIMIT 1
    """)

    global_config = cur.fetchone()

    return render_template('rpc_settings.html',
                         is_admin=is_admin,
                         use_custom=user_config[0] if user_config else False,
                         user_config={
                             'solana': user_config[1] if user_config else '',
                             'ethereum': user_config[2] if user_config else '',
                             'base': user_config[3] if user_config else '',
                             'polygon': user_config[4] if user_config else '',
                             'arbitrum': user_config[5] if user_config else '',
                             'optimism': user_config[6] if user_config else ''
                         },
                         global_config={
                             'solana': global_config[0] if global_config else '',
                             'ethereum': global_config[1] if global_config else '',
                             'base': global_config[2] if global_config else '',
                             'polygon': global_config[3] if global_config else '',
                             'arbitrum': global_config[4] if global_config else '',
                             'optimism': global_config[5] if global_config else ''
                         })

@app.route('/settings/rpc/save', methods=['POST'])
def save_rpc_settings():
    """Save user RPC configuration"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    use_custom = request.form.get('use_custom_rpc') == 'true'
    solana_rpc = request.form.get('solana_rpc', '').strip()
    ethereum_rpc = request.form.get('ethereum_rpc', '').strip()
    base_rpc = request.form.get('base_rpc', '').strip()
    polygon_rpc = request.form.get('polygon_rpc', '').strip()
    arbitrum_rpc = request.form.get('arbitrum_rpc', '').strip()
    optimism_rpc = request.form.get('optimism_rpc', '').strip()

    try:
        conn = get_db()
        cur = conn.cursor()

        # Update or insert user config
        cur.execute("""
            INSERT INTO user_rpc_config (
                user_email, use_custom_rpc, solana_rpc_url, ethereum_rpc_url,
                base_rpc_url, polygon_rpc_url, arbitrum_rpc_url, optimism_rpc_url,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_email) DO UPDATE SET
                use_custom_rpc = EXCLUDED.use_custom_rpc,
                solana_rpc_url = EXCLUDED.solana_rpc_url,
                ethereum_rpc_url = EXCLUDED.ethereum_rpc_url,
                base_rpc_url = EXCLUDED.base_rpc_url,
                polygon_rpc_url = EXCLUDED.polygon_rpc_url,
                arbitrum_rpc_url = EXCLUDED.arbitrum_rpc_url,
                optimism_rpc_url = EXCLUDED.optimism_rpc_url,
                updated_at = NOW()
        """, (session['email'], use_custom, solana_rpc or None, ethereum_rpc or None,
              base_rpc or None, polygon_rpc or None, arbitrum_rpc or None, optimism_rpc or None))

        conn.commit()
        return jsonify({'success': True, 'message': 'RPC settings saved successfully'})

    except Exception as e:
        print(f"Error saving RPC settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/rpc')
def admin_rpc_settings():
    """Admin RPC configuration page"""
    if 'email' not in session:
        return redirect(url_for('login'))

    # Check if user is admin
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM users WHERE email = %s", (session['email'],))
    result = cur.fetchone()

    if not result or not result[0]:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('inbox'))

    # Get current global RPC config
    cur.execute("""
        SELECT id, config_name, solana_rpc_url, ethereum_rpc_url,
               base_rpc_url, polygon_rpc_url, arbitrum_rpc_url, optimism_rpc_url,
               is_active
        FROM global_rpc_config
        ORDER BY is_active DESC, config_name
    """)

    configs = cur.fetchall()

    return render_template('admin_rpc.html', configs=configs)

@app.route('/admin/rpc/save', methods=['POST'])
def save_admin_rpc_settings():
    """Save global RPC configuration (admin only)"""
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    # Check if user is admin
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM users WHERE email = %s", (session['email'],))
    result = cur.fetchone()

    if not result or not result[0]:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    config_id = request.form.get('config_id')
    solana_rpc = request.form.get('solana_rpc', '').strip()
    ethereum_rpc = request.form.get('ethereum_rpc', '').strip()
    base_rpc = request.form.get('base_rpc', '').strip()
    polygon_rpc = request.form.get('polygon_rpc', '').strip()
    arbitrum_rpc = request.form.get('arbitrum_rpc', '').strip()
    optimism_rpc = request.form.get('optimism_rpc', '').strip()

    try:
        if config_id:
            # Update existing config
            cur.execute("""
                UPDATE global_rpc_config SET
                    solana_rpc_url = %s,
                    ethereum_rpc_url = %s,
                    base_rpc_url = %s,
                    polygon_rpc_url = %s,
                    arbitrum_rpc_url = %s,
                    optimism_rpc_url = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (solana_rpc, ethereum_rpc, base_rpc, polygon_rpc,
                  arbitrum_rpc, optimism_rpc, config_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'Global RPC settings updated'})

    except Exception as e:
        print(f"Error saving admin RPC settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/sitemap.xml')
def sitemap():
    """Generate SEO sitemap for Google"""
    base_url = request.url_root.rstrip('/')
    lastmod = datetime.now().strftime('%Y-%m-%d')

    return render_template('sitemap.xml',
                         base_url=base_url,
                         lastmod=lastmod), 200, {'Content-Type': 'application/xml'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
