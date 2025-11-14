#!/usr/bin/env python3
"""
Database migration for pay-to-send and consent system
Creates tables for sender consent, whitelists, and blacklists
"""

import os
import sys
import psycopg2

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def migrate():
    """Create consent system tables"""
    try:
        print("🔄 Starting pay-to-send consent system migration...")

        conn = get_db()
        cur = conn.cursor()

        # Create consent_settings table (per-user settings)
        print("📝 Creating consent_settings table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consent_settings (
                user_email VARCHAR(255) PRIMARY KEY,
                require_consent BOOLEAN DEFAULT FALSE,
                require_payment BOOLEAN DEFAULT FALSE,
                payment_amount DECIMAL(10, 2) DEFAULT 0.00,
                payment_address VARCHAR(500),
                whitelist_mode BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE
            )
        """)

        # Create sender_whitelist table
        print("📝 Creating sender_whitelist table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sender_whitelist (
                id SERIAL PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                sender_email VARCHAR(255) NOT NULL,
                sender_domain VARCHAR(255),
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipient_email) REFERENCES users(email) ON DELETE CASCADE,
                UNIQUE(recipient_email, sender_email)
            )
        """)

        # Create sender_blacklist table
        print("📝 Creating sender_blacklist table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sender_blacklist (
                id SERIAL PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                sender_email VARCHAR(255),
                sender_domain VARCHAR(255),
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipient_email) REFERENCES users(email) ON DELETE CASCADE
            )
        """)

        # Create consent_requests table (track consent requests)
        print("📝 Creating consent_requests table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consent_requests (
                id SERIAL PRIMARY KEY,
                recipient_email VARCHAR(255) NOT NULL,
                sender_email VARCHAR(255) NOT NULL,
                token VARCHAR(100) UNIQUE NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                email_subject TEXT,
                email_preview TEXT,
                payment_txid VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                responded_at TIMESTAMP,
                FOREIGN KEY (recipient_email) REFERENCES users(email) ON DELETE CASCADE
            )
        """)

        # Create indexes
        print("📝 Creating indexes...")
        cur.execute("CREATE INDEX idx_sender_whitelist_recipient ON sender_whitelist(recipient_email)")
        cur.execute("CREATE INDEX idx_sender_blacklist_recipient ON sender_blacklist(recipient_email)")
        cur.execute("CREATE INDEX idx_consent_requests_recipient ON consent_requests(recipient_email)")
        cur.execute("CREATE INDEX idx_consent_requests_token ON consent_requests(token)")
        cur.execute("CREATE INDEX idx_consent_requests_status ON consent_requests(status)")

        # Add default settings for existing users
        print("📝 Adding default consent settings for existing users...")
        cur.execute("""
            INSERT INTO consent_settings (user_email, require_consent, require_payment)
            SELECT email, FALSE, FALSE
            FROM users
            WHERE email NOT IN (SELECT user_email FROM consent_settings)
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show summary
        cur.execute("SELECT COUNT(*) FROM consent_settings")
        settings_count = cur.fetchone()[0]
        print(f"📊 Consent settings created for {settings_count} users")

        cur.close()
        conn.close()

        print("\n📌 Next steps:")
        print("   1. Configure Postfix policy service for consent checking")
        print("   2. Add web UI for managing whitelist/blacklist")
        print("   3. Implement consent request gateway")
        print("   4. Test with external email sender")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    migrate()
