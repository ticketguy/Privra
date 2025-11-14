#!/usr/bin/env python3
"""Database initialization script"""

import os
import psycopg2
import time

def wait_for_db():
    """Wait for database to be ready"""
    max_retries = 30
    retry_interval = 2

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'db'),
                database=os.getenv('DB_NAME', 'privramail'),
                user=os.getenv('DB_USER', 'privramail'),
                password=os.getenv('DB_PASSWORD')
            )
            conn.close()
            print("Database is ready!")
            return True
        except psycopg2.OperationalError:
            print(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(retry_interval)

    print("ERROR: Could not connect to database")
    return False

def init_database():
    """Initialize database tables"""
    if not wait_for_db():
        return False

    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

    cur = conn.cursor()

    # Create domains table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domains (
            id SERIAL PRIMARY KEY,
            domain VARCHAR(255) UNIQUE NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255),
            domain VARCHAR(255) NOT NULL,
            portid VARCHAR(255) UNIQUE,
            recovery_key TEXT,
            auth_type VARCHAR(20) DEFAULT 'password',
            email_public_key TEXT,
            email_private_key_encrypted TEXT,
            active BOOLEAN DEFAULT TRUE,
            quota_bytes BIGINT DEFAULT 1073741824,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create aliases table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            id SERIAL PRIMARY KEY,
            source VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create admin users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255),
            portid VARCHAR(255) UNIQUE,
            recovery_key TEXT,
            auth_type VARCHAR(20) DEFAULT 'password',
            email VARCHAR(255),
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default domain
    domain = os.getenv('MAIL_DOMAIN', 'privra.xyz')
    cur.execute(
        "INSERT INTO domains (domain) VALUES (%s) ON CONFLICT (domain) DO NOTHING",
        (domain,)
    )

    # Create consent settings table (Phase 5)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consent_settings (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            require_consent BOOLEAN DEFAULT FALSE,
            require_payment BOOLEAN DEFAULT FALSE,
            whitelist_mode BOOLEAN DEFAULT FALSE,
            payment_amount_sats INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create sender whitelist table (Phase 5)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sender_whitelist (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255),
            sender_domain VARCHAR(255),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipient_email, sender_email),
            UNIQUE(recipient_email, sender_domain)
        )
    """)

    # Create sender blacklist table (Phase 5)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sender_blacklist (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255),
            sender_domain VARCHAR(255),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipient_email, sender_email),
            UNIQUE(recipient_email, sender_domain)
        )
    """)

    # Create consent requests table (Phase 5)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consent_requests (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255) NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            email_subject TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            payment_received BOOLEAN DEFAULT FALSE,
            payment_txid VARCHAR(255),
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            rejected_at TIMESTAMP
        )
    """)

    # Create email categories table (Phase 4 - AI Intelligence)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_categories (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            email_id VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL,
            confidence FLOAT,
            ai_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, email_id)
        )
    """)

    # Create payment transactions table (Phase 5)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id SERIAL PRIMARY KEY,
            consent_request_id INTEGER REFERENCES consent_requests(id) ON DELETE CASCADE,
            sender_email VARCHAR(255) NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            amount_sats INTEGER NOT NULL,
            payment_method VARCHAR(50),
            txid VARCHAR(255) UNIQUE,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP
        )
    """)

    # Create default admin user (admin/admin) - CHANGE THIS!
    import bcrypt
    default_password = bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode('utf-8')
    cur.execute(
        """INSERT INTO admin_users (username, password, email)
           VALUES (%s, %s, %s)
           ON CONFLICT (username) DO NOTHING""",
        ('admin', default_password, f'admin@{domain}')
    )

    conn.commit()
    cur.close()
    conn.close()

    print("Database initialized successfully!")
    return True

if __name__ == '__main__':
    init_database()
