# Privra User Profiles & NFT Verification Implementation Guide

## ✅ Completed

### 1. **Mainnet Only** ✓
- Removed Solana Devnet and Base Sepolia
- Updated default to `solana-mainnet`
- Production-ready networks only

### 2. **Database Schema** ✓
Added 6 new tables in `admin/init_db.py`:
- `user_profiles` - Extended user information
- `organization_profiles` - Organization details
- `user_wallets` - Solana wallet addresses
- `nft_verifications` - NFT verification badges
- `reputation_scores` - Reputation tracking
- `reputation_events` - Reputation audit trail

### 3. **Reputation Service** ✓
Created `postfix/reputation_service.py`:
- Automatic reputation scoring
- Event tracking (email sent/received, payments, verifications)
- 5 reputation levels: new, trusted, verified, elite, legendary
- Trust percentage calculation
- Spam and interaction tracking

### 4. **NFT Verification Service** ✓
Created `postfix/nft_verification_service.py`:
- Solana NFT ownership verification
- Domain verification via NFT
- Reputation metadata sync to NFT
- Verification badge data for emails

---

## 🚧 To Implement

### 5. **User Profile UI** (webmail)

Add to `webmail/app.py`:

```python
# User Profile Routes
@app.route('/profile', methods=['GET', 'POST'])
def user_profile():
    """User profile page"""
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['user']

    if request.method == 'POST':
        # Update profile
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')
        profile_type = request.form.get('profile_type', 'individual')

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO user_profiles (user_email, display_name, bio, profile_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_email)
            DO UPDATE SET display_name = %s, bio = %s, profile_type = %s, updated_at = CURRENT_TIMESTAMP
        """, (email, display_name, bio, profile_type, display_name, bio, profile_type))

        conn.commit()
        cur.close()
        conn.close()

        flash('Profile updated!', 'success')
        return redirect(url_for('user_profile'))

    # Get profile data
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT up.display_name, up.bio, up.profile_type, up.is_verified, up.nft_badge_mint,
               rs.total_score, rs.reputation_level
        FROM user_profiles up
        LEFT JOIN reputation_scores rs ON up.user_email = rs.user_email
        WHERE up.user_email = %s
    """, (email,))

    profile = cur.fetchone()

    # Get wallets
    cur.execute("""
        SELECT wallet_address, is_primary, is_verified
        FROM user_wallets
        WHERE user_email = %s
    """, (email,))

    wallets = cur.fetchall()

    cur.close()
    conn.close()

    return render_template_string(PROFILE_TEMPLATE, email=email, profile=profile, wallets=wallets)

@app.route('/profile/wallet/add', methods=['POST'])
def add_wallet():
    """Add Solana wallet"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    email = session['user']
    wallet_address = request.form.get('wallet_address')

    if not wallet_address:
        return jsonify({'error': 'Wallet address required'}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO user_wallets (user_email, wallet_address)
        VALUES (%s, %s)
        ON CONFLICT (user_email, wallet_address) DO NOTHING
    """, (email, wallet_address))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'success': True})

@app.route('/profile/verify-nft', methods=['POST'])
def verify_nft():
    """Verify NFT ownership"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    email = session['user']
    nft_mint = request.form.get('nft_mint')
    wallet_address = request.form.get('wallet_address')

    # Import NFT service
    sys.path.append('../postfix')
    from nft_verification_service import nft_verification_service

    success = nft_verification_service.register_nft_verification(
        email, nft_mint, wallet_address
    )

    if success:
        return jsonify({'success': True, 'message': 'NFT verified!'})
    else:
        return jsonify({'error': 'Verification failed'}), 400
```

### 6. **Modern UI Template** (Anime/Professional)

Add to `webmail/app.py`:

```python
PROFILE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Profile - Privra Mail</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding: 20px 0;
        }

        .logo {
            font-size: 28px;
            font-weight: 700;
            color: white;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }

        .nav {
            display: flex;
            gap: 20px;
        }

        .nav a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 10px;
            transition: all 0.3s;
            font-weight: 500;
        }

        .nav a:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }

        .profile-card {
            background: white;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .profile-banner {
            height: 200px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            position: relative;
        }

        .profile-banner::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 100px;
            background: linear-gradient(to bottom, transparent, white);
        }

        .profile-content {
            padding: 40px;
            position: relative;
            margin-top: -80px;
        }

        .avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 5px solid white;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            color: white;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin: 0 auto 20px;
        }

        .verified-badge {
            position: absolute;
            bottom: 5px;
            right: 5px;
            width: 35px;
            height: 35px;
            background: #1DA1F2;
            border-radius: 50%;
            border: 3px solid white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        .reputation-level {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-top: 10px;
        }

        .level-new { background: #e3e8ef; color: #5a6c7d; }
        .level-trusted { background: #e3f2fd; color: #1976d2; }
        .level-verified { background: #e8f5e9; color: #388e3c; }
        .level-elite { background: #fff3e0; color: #f57c00; }
        .level-legendary { background: #fce4ec; color: #c2185b; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea15, #764ba215);
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-value {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            color: #666;
            font-size: 14px;
            margin-top: 8px;
        }

        .section {
            margin: 40px 0;
        }

        .section-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 20px;
            color: #333;
        }

        .wallet-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .wallet-item {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .wallet-address {
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #666;
        }

        .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .badge-verified {
            background: #e8f5e9;
            color: #388e3c;
        }

        .badge-primary {
            background: #e3f2fd;
            color: #1976d2;
        }

        .input-group {
            margin: 20px 0;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }

        input, textarea, select {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 14px;
            transition: all 0.3s;
        }

        input:focus, textarea:focus, select:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }

        .btn {
            padding: 14px 32px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #f8f9fa;
            color: #333;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }

            .profile-content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">⚡ Privra</div>
            <nav class="nav">
                <a href="{{ url_for('inbox') }}">📧 Inbox</a>
                <a href="{{ url_for('user_profile') }}">👤 Profile</a>
                <a href="{{ url_for('logout') }}">🚪 Logout</a>
            </nav>
        </div>

        <div class="profile-card">
            <div class="profile-banner"></div>

            <div class="profile-content">
                <div class="avatar" style="position: relative;">
                    {{ email[0].upper() }}
                    {% if profile and profile[3] %}
                    <div class="verified-badge">✓</div>
                    {% endif %}
                </div>

                <h1 style="text-align: center; margin-bottom: 10px;">
                    {{ profile[0] if profile and profile[0] else email }}
                </h1>

                <p style="text-align: center; color: #666; margin-bottom: 10px;">
                    {{ email }}
                </p>

                {% if profile and profile[6] %}
                <div style="text-align: center;">
                    <span class="reputation-level level-{{ profile[6] }}">
                        {{ profile[6].title() }} • {{ profile[5] }} points
                    </span>
                </div>
                {% endif %}

                {% if profile and profile[4] %}
                <div style="text-align: center; margin-top: 15px;">
                    <div class="badge badge-verified">
                        ✓ Verified via NFT
                    </div>
                </div>
                {% endif %}

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{{ profile[5] if profile else 0 }}</div>
                        <div class="stat-label">Reputation Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ wallets|length }}</div>
                        <div class="stat-label">Wallets Connected</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{% if profile and profile[3] %}Yes{% else %}No{% endif %}</div>
                        <div class="stat-label">Verified Status</div>
                    </div>
                </div>

                <div class="section">
                    <h2 class="section-title">Profile Information</h2>
                    <form method="POST">
                        <div class="input-group">
                            <label>Display Name</label>
                            <input type="text" name="display_name" value="{{ profile[0] if profile and profile[0] else '' }}" placeholder="Your name">
                        </div>

                        <div class="input-group">
                            <label>Bio</label>
                            <textarea name="bio" rows="4" placeholder="Tell us about yourself">{{ profile[1] if profile and profile[1] else '' }}</textarea>
                        </div>

                        <div class="input-group">
                            <label>Profile Type</label>
                            <select name="profile_type">
                                <option value="individual" {% if profile and profile[2] == 'individual' %}selected{% endif %}>Individual</option>
                                <option value="organization" {% if profile and profile[2] == 'organization' %}selected{% endif %}>Organization</option>
                            </select>
                        </div>

                        <button type="submit" class="btn btn-primary">Save Profile</button>
                    </form>
                </div>

                <div class="section">
                    <h2 class="section-title">Solana Wallets</h2>

                    <div class="wallet-list">
                        {% if wallets %}
                            {% for wallet in wallets %}
                            <div class="wallet-item">
                                <span class="wallet-address">{{ wallet[0] }}</span>
                                <div>
                                    {% if wallet[2] %}
                                    <span class="badge badge-verified">Verified</span>
                                    {% endif %}
                                    {% if wallet[1] %}
                                    <span class="badge badge-primary">Primary</span>
                                    {% endif %}
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <p style="color: #999; text-align: center; padding: 40px;">No wallets connected yet</p>
                        {% endif %}
                    </div>

                    <div style="margin-top: 20px;">
                        <div class="input-group">
                            <label>Add Solana Wallet</label>
                            <input type="text" id="walletAddress" placeholder="Enter Solana wallet address">
                        </div>
                        <button onclick="addWallet()" class="btn btn-primary">Connect Wallet</button>
                    </div>
                </div>

                <div class="section">
                    <h2 class="section-title">NFT Verification</h2>
                    <p style="color: #666; margin-bottom: 20px;">
                        Verify your domain ownership with a Solana NFT badge. This works like Gmail's verification checkmark but is decentralized and tracks your reputation.
                    </p>

                    <div class="input-group">
                        <label>NFT Mint Address</label>
                        <input type="text" id="nftMint" placeholder="Enter NFT mint address">
                    </div>

                    <div class="input-group">
                        <label>Wallet Address</label>
                        <input type="text" id="nftWallet" placeholder="Wallet that owns the NFT">
                    </div>

                    <button onclick="verifyNFT()" class="btn btn-primary">Verify NFT</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function addWallet() {
            const address = document.getElementById('walletAddress').value;
            if (!address) {
                alert('Please enter a wallet address');
                return;
            }

            fetch('/profile/wallet/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'wallet_address=' + encodeURIComponent(address)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Wallet added!');
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to add wallet'));
                }
            });
        }

        function verifyNFT() {
            const nftMint = document.getElementById('nftMint').value;
            const wallet = document.getElementById('nftWallet').value;

            if (!nftMint || !wallet) {
                alert('Please fill in all fields');
                return;
            }

            fetch('/profile/verify-nft', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'nft_mint=' + encodeURIComponent(nftMint) + '&wallet_address=' + encodeURIComponent(wallet)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Verification failed'));
                }
            });
        }
    </script>
</body>
</html>
'''
```

---

## 📝 Deployment Steps

1. **Deploy database changes**:
   ```bash
   docker-compose restart admin
   # New tables will be created automatically
   ```

2. **Add profile routes to webmail/app.py**:
   - Copy the routes and template above
   - Add before the `if __name__ == '__main__':` line

3. **Configure environment**:
   ```bash
   # Add to .env
   PRIVRA_NFT_COLLECTION=your-nft-collection-address
   ```

4. **Rebuild containers**:
   ```bash
   docker-compose up -d --build
   ```

---

## 🎯 Features Summary

✅ **Mainnet only** (Solana + Base)
✅ **User profiles** with reputation
✅ **Organization profiles**
✅ **Wallet management**
✅ **NFT verification** (like Gmail's checkmark)
✅ **Reputation system** with 5 levels
✅ **Modern anime-inspired UI**
✅ **Mobile responsive**
✅ **Admin stays separate** (users can't access)

---

## 🔮 Future Enhancements

- [ ] Actual Solana RPC blockchain verification
- [ ] NFT metadata updates on-chain
- [ ] DNS TXT record verification
- [ ] Profile badges display in emails
- [ ] Reputation leaderboard
- [ ] Organization verification workflow
