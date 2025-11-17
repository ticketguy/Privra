#!/usr/bin/env python3
"""Privra Mail Admin Interface"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import psycopg2
import bcrypt
import os
import redis
from portid_service import portid_service
from crypto_utils import (
    generate_email_keypair,
    serialize_public_key,
    serialize_private_key,
    encrypt_private_key_with_recovery_key
)
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Handle reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Database connection
def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Login required decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'admin_user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT email, active, created_at FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template_string(INDEX_TEMPLATE, users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        use_portid = request.form.get('use_portid', '').lower() == 'true'

        # Try PortID authentication first if enabled
        if portid_service.is_enabled() and use_portid:
            result = portid_service.login(username, password)
            if result and result.get('success'):
                # Store PortID info in session
                session['admin_user'] = username
                session['auth_type'] = 'portid'
                session['portid'] = result.get('portid')
                flash('Login successful via PortID!', 'success')
                return redirect(url_for('index'))
            else:
                flash('PortID authentication failed', 'error')
                return render_template_string(LOGIN_TEMPLATE, portid_enabled=True)

        # Fall back to legacy password authentication
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT password, auth_type FROM admin_users WHERE username = %s AND active = TRUE", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0] and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            session['admin_user'] = username
            session['auth_type'] = result[1] or 'password'
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template_string(LOGIN_TEMPLATE, portid_enabled=portid_service.is_enabled())

@app.route('/logout')
def logout():
    session.pop('admin_user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/api/pubkey/<email>')
def get_public_key(email):
    """
    Public key lookup API endpoint
    Returns the public key for a given email address if user exists
    """
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

@app.route('/adduser', methods=['GET', 'POST'])
@login_required
def adduser():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        domain = email.split('@')[1] if '@' in email else os.getenv('MAIL_DOMAIN')

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Generate recovery key (32 bytes hex - same as PortID)
        from Crypto.Random import get_random_bytes
        recovery_key = get_random_bytes(32).hex()

        # Generate email encryption keys
        private_key, public_key = generate_email_keypair()
        public_key_pem = serialize_public_key(public_key)
        private_key_pem = serialize_private_key(private_key)

        # Encrypt private key with recovery key
        encrypted_private_key = encrypt_private_key_with_recovery_key(
            private_key_pem,
            recovery_key
        )

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO users
                   (email, password, domain, recovery_key, email_public_key, email_private_key_encrypted)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (email, hashed, domain, recovery_key, public_key_pem, encrypted_private_key)
            )
            conn.commit()
            cur.close()
            conn.close()

            # Store recovery key in session to display it once
            session['new_user_recovery_key'] = recovery_key
            session['new_user_email'] = email

            flash(f'User {email} created successfully!', 'success')
            return redirect(url_for('show_recovery_key'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template_string(ADDUSER_TEMPLATE)

@app.route('/recovery-key')
@login_required
def show_recovery_key():
    """Show recovery key once after user creation"""
    recovery_key = session.pop('new_user_recovery_key', None)
    email = session.pop('new_user_email', None)

    if not recovery_key:
        flash('No recovery key to display', 'error')
        return redirect(url_for('index'))

    return render_template_string(RECOVERY_KEY_TEMPLATE,
                                 recovery_key=recovery_key,
                                 email=email)

@app.route('/deluser/<email>', methods=['POST'])
@login_required
def deluser(email):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        cur.close()
        conn.close()
        flash(f'User {email} deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/passwd/<email>', methods=['GET', 'POST'])
@login_required
def passwd(email):
    if request.method == 'POST':
        new_password = request.form.get('password')
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
                (hashed, email)
            )
            conn.commit()
            cur.close()
            conn.close()
            flash(f'Password updated for {email}!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template_string(PASSWD_TEMPLATE, email=email)

@app.route('/consent/<email>', methods=['GET', 'POST'])
@login_required
def consent_settings(email):
    """Manage consent settings for a user"""
    if request.method == 'POST':
        require_consent = request.form.get('require_consent') == 'on'
        require_payment = request.form.get('require_payment') == 'on'
        whitelist_mode = request.form.get('whitelist_mode') == 'on'
        payment_amount = int(request.form.get('payment_amount_sats', 1000))

        try:
            conn = get_db()
            cur = conn.cursor()

            # Upsert consent settings
            cur.execute("""
                INSERT INTO consent_settings
                (user_email, require_consent, require_payment, whitelist_mode, payment_amount_sats, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    require_consent = %s,
                    require_payment = %s,
                    whitelist_mode = %s,
                    payment_amount_sats = %s,
                    updated_at = CURRENT_TIMESTAMP
            """, (email, require_consent, require_payment, whitelist_mode, payment_amount,
                  require_consent, require_payment, whitelist_mode, payment_amount))

            conn.commit()
            cur.close()
            conn.close()

            flash(f'Consent settings updated for {email}!', 'success')
            return redirect(url_for('consent_settings', email=email))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    # Get current settings
    try:
        conn = get_db()
        cur = conn.cursor()

        # Get user
        cur.execute("SELECT email, active FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            flash(f'User {email} not found!', 'error')
            return redirect(url_for('index'))

        # Get consent settings
        cur.execute("""
            SELECT require_consent, require_payment, whitelist_mode, payment_amount_sats
            FROM consent_settings WHERE user_email = %s
        """, (email,))
        settings = cur.fetchone()

        # Get whitelist
        cur.execute("""
            SELECT sender_email, sender_domain, added_at
            FROM sender_whitelist WHERE recipient_email = %s
            ORDER BY added_at DESC
        """, (email,))
        whitelist = cur.fetchall()

        # Get blacklist
        cur.execute("""
            SELECT sender_email, sender_domain, added_at
            FROM sender_blacklist WHERE recipient_email = %s
            ORDER BY added_at DESC
        """, (email,))
        blacklist = cur.fetchall()

        cur.close()
        conn.close()

        return render_template_string(CONSENT_TEMPLATE,
                                     email=email,
                                     settings=settings,
                                     whitelist=whitelist,
                                     blacklist=blacklist)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/consent/<email>/whitelist/add', methods=['POST'])
@login_required
def add_whitelist(email):
    """Add sender to whitelist"""
    sender_email = request.form.get('sender_email', '').strip()
    sender_domain = request.form.get('sender_domain', '').strip()

    if not sender_email and not sender_domain:
        flash('Please provide either an email or domain', 'error')
        return redirect(url_for('consent_settings', email=email))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sender_whitelist (recipient_email, sender_email, sender_domain)
            VALUES (%s, %s, %s)
        """, (email, sender_email if sender_email else None, sender_domain if sender_domain else None))
        conn.commit()
        cur.close()
        conn.close()
        flash('Added to whitelist!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('consent_settings', email=email))

@app.route('/consent/<email>/blacklist/add', methods=['POST'])
@login_required
def add_blacklist(email):
    """Add sender to blacklist"""
    sender_email = request.form.get('sender_email', '').strip()
    sender_domain = request.form.get('sender_domain', '').strip()

    if not sender_email and not sender_domain:
        flash('Please provide either an email or domain', 'error')
        return redirect(url_for('consent_settings', email=email))

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sender_blacklist (recipient_email, sender_email, sender_domain)
            VALUES (%s, %s, %s)
        """, (email, sender_email if sender_email else None, sender_domain if sender_domain else None))
        conn.commit()
        cur.close()
        conn.close()
        flash('Added to blacklist!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('consent_settings', email=email))

# X402 Payment Routes (Public - no login required for AI agents)
@app.route('/x402/pay/<token>', methods=['GET'])
def x402_payment_page(token):
    """Display X402 payment request page for AI agents and senders"""
    try:
        # Import X402 service
        import sys
        sys.path.append('/app')
        sys.path.append('../postfix')
        from x402_service import x402_service

        conn = get_db()
        cur = conn.cursor()

        # Get payment request details
        cur.execute("""
            SELECT pr.id, pr.sender_email, pr.recipient_email, pr.amount_usdc,
                   pr.network, pr.payment_address, pr.asset_address, pr.expires_at, pr.status,
                   cr.email_subject
            FROM x402_payment_requests pr
            JOIN consent_requests cr ON pr.consent_request_id = cr.id
            WHERE pr.token = %s
        """, (token,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({"error": "Payment request not found"}), 404

        payment_id, sender, recipient, amount_usdc, network, pay_to, asset, expires_at, status, subject = result

        # Check if already paid
        if status == 'paid':
            return render_template_string(X402_PAID_TEMPLATE, sender=sender, recipient=recipient)

        # Check if expired
        from datetime import datetime
        if datetime.now() > expires_at:
            return jsonify({"error": "Payment request expired"}), 410

        # Build payment requirement
        network_config = x402_service.NETWORKS.get(network, {})
        amount_atomic = str(int(float(amount_usdc) * 1_000_000))

        payment_requirement = {
            "x402Version": 1,
            "accepts": [
                {
                    "scheme": "exact",
                    "network": network,
                    "maxAmountRequired": amount_atomic,
                    "resource": f"/x402/pay/{token}",
                    "description": f"Email delivery to {recipient}",
                    "mimeType": "application/json",
                    "payTo": pay_to,
                    "maxTimeoutSeconds": 3600,
                    "asset": asset,
                    "extra": {
                        "sender": sender,
                        "recipient": recipient,
                        "token": token,
                        "type": "email_consent"
                    }
                }
            ],
            "error": f"Payment required to send email to {recipient}"
        }

        # Return JSON for AI agents or HTML for browsers
        if request.headers.get('Accept', '').startswith('application/json'):
            return jsonify(payment_requirement), 402
        else:
            return render_template_string(
                X402_PAYMENT_TEMPLATE,
                sender=sender,
                recipient=recipient,
                amount_usdc=amount_usdc,
                network=network,
                network_name=network_config.get('name', network),
                pay_to=pay_to,
                token=token,
                subject=subject,
                payment_requirement=json.dumps(payment_requirement, indent=2)
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/x402/verify/<token>', methods=['POST'])
def x402_verify_payment(token):
    """Verify X402 payment"""
    try:
        # Get payment header from request
        payment_header = request.headers.get('X-PAYMENT')
        if not payment_header:
            # Try JSON body
            data = request.get_json()
            payment_header = data.get('paymentHeader') if data else None

        if not payment_header:
            return jsonify({"error": "Missing X-PAYMENT header"}), 400

        # Import X402 service
        import sys
        sys.path.append('/app')
        sys.path.append('../postfix')
        from x402_service import x402_service

        # Verify payment
        is_valid, error = x402_service.verify_payment(token, payment_header)

        if is_valid:
            return jsonify({
                "success": True,
                "message": "Payment verified. Email will be delivered."
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": error or "Payment verification failed"
            }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/x402/status/<token>', methods=['GET'])
def x402_payment_status(token):
    """Check X402 payment status"""
    try:
        # Import X402 service
        import sys
        sys.path.append('/app')
        sys.path.append('../postfix')
        from x402_service import x402_service

        status = x402_service.check_payment_status(token)

        if status is None:
            return jsonify({"error": "Payment request not found"}), 404

        return jsonify({"status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# HTML Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Privra Mail - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 400px; margin: 100px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { margin-bottom: 30px; color: #333; text-align: center; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #0056b3; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .flash.error { background: #fee; color: #c33; border: 1px solid #fcc; }
        .flash.success { background: #efe; color: #3c3; border: 1px solid #cfc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Privra Mail</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            {% if portid_enabled %}
            <div style="margin: 15px 0;">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" name="use_portid" value="true" style="width: auto; margin-right: 8px;">
                    <span style="font-size: 14px; color: #555;">Use PortID Authentication</span>
                </label>
                <p style="font-size: 12px; color: #888; margin: 5px 0 0 28px;">Zero-knowledge authentication via PortID</p>
            </div>
            {% endif %}
            <button type="submit">Login</button>
        </form>
        <p style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">Default: admin/admin (change this!)</p>
    </div>
</body>
</html>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Privra Mail Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { display: inline-block; color: #333; }
        .header .logout { float: right; color: #007bff; text-decoration: none; line-height: 40px; }
        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .actions { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .actions a { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; }
        .actions a:hover { background: #0056b3; }
        table { width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th { background: #f8f9fa; padding: 15px; text-align: left; font-weight: 600; color: #555; }
        td { padding: 15px; border-top: 1px solid #f0f0f0; }
        .btn { padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 13px; display: inline-block; margin-right: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; border: none; cursor: pointer; }
        .flash { padding: 12px 20px; margin-bottom: 20px; border-radius: 4px; }
        .flash.error { background: #fee; color: #c33; border: 1px solid #fcc; }
        .flash.success { background: #efe; color: #3c3; border: 1px solid #cfc; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Privra Mail Admin</h1>
        <a href="{{ url_for('logout') }}" class="logout">Logout</a>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="actions">
            <a href="{{ url_for('adduser') }}">➕ Add User</a>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for user in users %}
                <tr>
                    <td>{{ user[0] }}</td>
                    <td>{{ 'Active' if user[1] else 'Inactive' }}</td>
                    <td>{{ user[2].strftime('%Y-%m-%d %H:%M') }}</td>
                    <td>
                        <a href="{{ url_for('passwd', email=user[0]) }}" class="btn btn-primary">Change Password</a>
                        <a href="{{ url_for('consent_settings', email=user[0]) }}" class="btn btn-primary">Consent Settings</a>
                        <form method="POST" action="{{ url_for('deluser', email=user[0]) }}" style="display: inline;">
                            <button type="submit" class="btn btn-danger" onclick="return confirm('Delete {{ user[0] }}?')">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

ADDUSER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Add User - Privra Mail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { margin-bottom: 20px; color: #333; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #0056b3; }
        .back { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Privra Mail Admin</h1>
    </div>
    <div class="container">
        <a href="{{ url_for('index') }}" class="back">← Back to Users</a>
        <h2>Add New User</h2>
        <form method="POST">
            <input type="email" name="email" placeholder="user@domain.com" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Create User</button>
        </form>
    </div>
</body>
</html>
'''

PASSWD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Change Password - Privra Mail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { margin-bottom: 20px; color: #333; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #0056b3; }
        .back { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Privra Mail Admin</h1>
    </div>
    <div class="container">
        <a href="{{ url_for('index') }}" class="back">← Back to Users</a>
        <h2>Change Password for {{ email }}</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="New Password" required>
            <button type="submit">Update Password</button>
        </form>
    </div>
</body>
</html>
'''

RECOVERY_KEY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Recovery Key - Privra Mail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { margin-bottom: 20px; color: #333; }
        .warning { background: #fff3cd; border: 2px solid #ffc107; border-radius: 4px; padding: 15px; margin: 20px 0; }
        .warning h3 { color: #856404; margin-bottom: 10px; }
        .recovery-key { background: #f8f9fa; border: 2px solid #007bff; border-radius: 4px; padding: 20px; margin: 20px 0; font-family: monospace; font-size: 14px; word-break: break-all; }
        .copy-btn { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 10px 0; }
        .copy-btn:hover { background: #218838; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 20px; }
        button:hover { background: #0056b3; }
        ul { margin: 15px 0 15px 30px; }
        li { margin: 8px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Privra Mail Admin</h1>
    </div>
    <div class="container">
        <h2>✅ User Created: {{ email }}</h2>

        <div class="warning">
            <h3>⚠️ IMPORTANT: Save This Recovery Key!</h3>
            <p>This recovery key will only be shown ONCE and cannot be recovered later.</p>
            <p><strong>The user MUST save this key to:</strong></p>
            <ul>
                <li>Decrypt their encrypted emails</li>
                <li>Recover their account on a new device</li>
                <li>Access their private encryption key</li>
            </ul>
        </div>

        <h3>Recovery Key for {{ email }}:</h3>
        <div class="recovery-key" id="recoveryKey">{{ recovery_key }}</div>

        <button class="copy-btn" onclick="copyRecoveryKey()">📋 Copy Recovery Key</button>

        <p style="margin-top: 20px; color: #666;">
            Instruct the user to:
        </p>
        <ul>
            <li>Save this key in a secure password manager</li>
            <li>Write it down and store it safely offline</li>
            <li>Never share it with anyone</li>
            <li>Keep it separate from their password</li>
        </ul>

        <form action="{{ url_for('index') }}">
            <button type="submit">Done - Return to Users</button>
        </form>
    </div>

    <script>
    function copyRecoveryKey() {
        const recoveryKey = document.getElementById('recoveryKey').textContent;
        navigator.clipboard.writeText(recoveryKey).then(() => {
            alert('Recovery key copied to clipboard!');
        });
    }
    </script>
</body>
</html>
'''

CONSENT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Consent Settings - {{ email }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }
        h2 { margin-bottom: 20px; color: #333; }
        h3 { margin: 25px 0 15px 0; color: #555; font-size: 18px; }
        .back { display: inline-block; margin-bottom: 20px; color: #007bff; text-decoration: none; }
        input[type="checkbox"] { margin-right: 8px; width: auto; }
        input[type="number"], input[type="text"] { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }
        label { display: block; margin: 12px 0; font-size: 14px; }
        button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .flash { padding: 12px; margin: 15px 0; border-radius: 4px; }
        .flash.error { background: #fee; color: #c33; border: 1px solid #fcc; }
        .flash.success { background: #efe; color: #3c3; border: 1px solid #cfc; }
        .section { background: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }
        .info-box { background: #e7f3ff; border-left: 4px solid #007bff; padding: 12px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Privra Mail Admin</h1>
    </div>
    <div class="container">
        <a href="{{ url_for('index') }}" class="back">← Back to Users</a>
        <h2>Consent & Pay-to-Send Settings for {{ email }}</h2>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="info-box">
            <strong>Phase 5: Pay-to-Send Economic Layer</strong><br>
            Control who can send emails to this user. Configure consent requirements, payment settings, and whitelist/blacklist.
        </div>

        <form method="POST" class="section">
            <h3>Consent Settings</h3>

            <label>
                <input type="checkbox" name="require_consent" {% if settings and settings[0] %}checked{% endif %}>
                Require consent from unknown senders
            </label>

            <label>
                <input type="checkbox" name="require_payment" {% if settings and settings[1] %}checked{% endif %}>
                Require payment for consent
            </label>

            <label>
                <input type="checkbox" name="whitelist_mode" {% if settings and settings[2] %}checked{% endif %}>
                Whitelist mode (only allow whitelisted senders)
            </label>

            <label>
                Payment amount (satoshis):
                <input type="number" name="payment_amount_sats" value="{{ settings[3] if settings else 1000 }}" min="1">
            </label>

            <button type="submit">Save Settings</button>
        </form>

        <h3>Whitelist (Allowed Senders)</h3>
        <div class="section">
            <form method="POST" action="{{ url_for('add_whitelist', email=email) }}" style="margin-bottom: 20px;">
                <label>
                    Sender Email:
                    <input type="text" name="sender_email" placeholder="sender@example.com">
                </label>
                <label>
                    OR Sender Domain:
                    <input type="text" name="sender_domain" placeholder="example.com">
                </label>
                <button type="submit" class="btn-success">Add to Whitelist</button>
            </form>

            {% if whitelist %}
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Domain</th>
                        <th>Added</th>
                    </tr>
                </thead>
                <tbody>
                    {% for entry in whitelist %}
                    <tr>
                        <td>{{ entry[0] or '-' }}</td>
                        <td>{{ entry[1] or '-' }}</td>
                        <td>{{ entry[2].strftime('%Y-%m-%d %H:%M') }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="color: #666; font-style: italic;">No entries in whitelist</p>
            {% endif %}
        </div>

        <h3>Blacklist (Blocked Senders)</h3>
        <div class="section">
            <form method="POST" action="{{ url_for('add_blacklist', email=email) }}" style="margin-bottom: 20px;">
                <label>
                    Sender Email:
                    <input type="text" name="sender_email" placeholder="spammer@example.com">
                </label>
                <label>
                    OR Sender Domain:
                    <input type="text" name="sender_domain" placeholder="spam.com">
                </label>
                <button type="submit" class="btn-success">Add to Blacklist</button>
            </form>

            {% if blacklist %}
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Domain</th>
                        <th>Added</th>
                    </tr>
                </thead>
                <tbody>
                    {% for entry in blacklist %}
                    <tr>
                        <td>{{ entry[0] or '-' }}</td>
                        <td>{{ entry[1] or '-' }}</td>
                        <td>{{ entry[2].strftime('%Y-%m-%d %H:%M') }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="color: #666; font-style: italic;">No entries in blacklist</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

X402_PAYMENT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Payment Required - X402</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { max-width: 700px; margin: 20px; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        h2 { color: #667eea; margin: 30px 0 15px 0; font-size: 20px; }
        .status-code { background: #667eea; color: white; padding: 8px 16px; border-radius: 6px; display: inline-block; font-weight: bold; margin-bottom: 20px; }
        .info-box { background: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .info-box strong { color: #667eea; }
        .payment-details { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .payment-details div { margin: 10px 0; display: flex; justify-content: space-between; }
        .payment-details .label { color: #666; font-weight: 600; }
        .payment-details .value { color: #333; font-family: monospace; word-break: break-all; }
        .code-block { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 12px; margin: 15px 0; }
        .btn { display: inline-block; padding: 14px 28px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; border: none; cursor: pointer; }
        .btn:hover { background: #5568d3; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
        .network-badge { background: #28a745; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-left: 10px; }
        .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 6px; margin: 20px 0; color: #856404; }
        .ai-agent-note { background: #e7f3ff; border-left: 4px solid #0066cc; padding: 15px; margin: 20px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Payment Required</h1>
        <div class="status-code">HTTP 402</div>

        <div class="info-box">
            <strong>From:</strong> {{ sender }}<br>
            <strong>To:</strong> {{ recipient }}<br>
            <strong>Subject:</strong> {{ subject }}
        </div>

        <p style="margin: 20px 0; color: #666; line-height: 1.6;">
            This recipient requires payment for email delivery from unauthorized senders.
            This helps prevent spam and ensures only serious senders reach the inbox.
        </p>

        <h2>💰 Payment Details</h2>
        <div class="payment-details">
            <div>
                <span class="label">Amount:</span>
                <span class="value">${{ amount_usdc }} USDC</span>
            </div>
            <div>
                <span class="label">Network:</span>
                <span class="value">{{ network_name }} <span class="network-badge">{{ network }}</span></span>
            </div>
            <div>
                <span class="label">Payment Address:</span>
                <span class="value">{{ pay_to }}</span>
            </div>
        </div>

        <div class="ai-agent-note">
            <strong>🤖 AI Agents:</strong> Use the X402 protocol to pay programmatically.
            Send USDC on {{ network_name }} to the address above, then submit the payment proof via the X-PAYMENT header.
        </div>

        <h2>📝 X402 Payment Requirement</h2>
        <div class="code-block">{{ payment_requirement }}</div>

        <h2>🔗 How to Pay</h2>
        <div style="margin: 20px 0;">
            <ol style="margin-left: 20px; line-height: 1.8;">
                <li>Send <strong>${{ amount_usdc }} USDC</strong> to the payment address above on <strong>{{ network_name }}</strong></li>
                <li>Get your transaction hash/signature</li>
                <li>Submit payment proof via POST to <code>/x402/verify/{{ token }}</code></li>
                <li>Your email will be automatically delivered once payment is verified</li>
            </ol>
        </div>

        <div class="warning">
            <strong>⏰ Note:</strong> This payment request expires in 1 hour.
            Once paid, the sender will be approved and can send emails without future payments.
        </div>

        <div style="margin-top: 30px; text-align: center;">
            <p style="color: #666; font-size: 14px;">
                Powered by <strong>X402 Protocol</strong> • Privra Mail Server<br>
                <a href="https://x402.org" style="color: #667eea;">Learn more about X402</a>
            </p>
        </div>
    </div>
</body>
</html>
'''

X402_PAID_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Payment Confirmed - X402</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { max-width: 600px; margin: 20px; background: white; padding: 50px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; }
        h1 { color: #11998e; margin-bottom: 20px; font-size: 32px; }
        .checkmark { font-size: 80px; color: #38ef7d; margin-bottom: 20px; }
        p { color: #666; line-height: 1.6; margin: 15px 0; }
        .email-info { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 30px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✓</div>
        <h1>Payment Confirmed!</h1>
        <p>Your payment has been verified and your email will be delivered shortly.</p>

        <div class="email-info">
            <strong>From:</strong> {{ sender }}<br>
            <strong>To:</strong> {{ recipient }}
        </div>

        <p style="font-size: 14px; color: #999;">
            You are now approved to send emails to this recipient. Future emails will be delivered without payment.
        </p>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    # Initialize database on startup
    from init_db import init_database
    init_database()

    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
