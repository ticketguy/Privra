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

    # Create consent settings table (Phase 5) - Merged version
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consent_settings (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            require_consent BOOLEAN DEFAULT FALSE,
            require_payment BOOLEAN DEFAULT FALSE,
            whitelist_mode BOOLEAN DEFAULT FALSE,
            payment_amount_sats INTEGER DEFAULT 1000,
            payment_address VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create sender whitelist table (Phase 5) - Merged version
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sender_whitelist (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255),
            sender_domain VARCHAR(255),
            note TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipient_email, sender_email),
            UNIQUE(recipient_email, sender_domain)
        )
    """)

    # Create sender blacklist table (Phase 5) - Merged version
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sender_blacklist (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255),
            sender_domain VARCHAR(255),
            reason TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recipient_email, sender_email),
            UNIQUE(recipient_email, sender_domain)
        )
    """)

    # Create consent requests table (Phase 5) - Merged version
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consent_requests (
            id SERIAL PRIMARY KEY,
            recipient_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            sender_email VARCHAR(255) NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            email_subject TEXT,
            email_preview TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            payment_received BOOLEAN DEFAULT FALSE,
            payment_txid VARCHAR(255),
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            rejected_at TIMESTAMP,
            responded_at TIMESTAMP
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
            amount_sats INTEGER,
            amount_usdc VARCHAR(50),
            payment_method VARCHAR(50),
            payment_network VARCHAR(50),
            txid VARCHAR(255) UNIQUE,
            blockchain_address VARCHAR(255),
            x402_payment_header TEXT,
            x402_settlement_data TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP
        )
    """)

    # Create X402 payment requests table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS x402_payment_requests (
            id SERIAL PRIMARY KEY,
            consent_request_id INTEGER REFERENCES consent_requests(id) ON DELETE CASCADE,
            sender_email VARCHAR(255) NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            payment_address VARCHAR(255) NOT NULL,
            amount_usdc VARCHAR(50) NOT NULL,
            network VARCHAR(50) NOT NULL,
            asset_address VARCHAR(255),
            payment_url TEXT,
            token VARCHAR(255) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP
        )
    """)

    # Create user profiles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            display_name VARCHAR(255),
            bio TEXT,
            avatar_url TEXT,
            profile_type VARCHAR(20) DEFAULT 'individual',
            organization_name VARCHAR(255),
            organization_domain VARCHAR(255),
            website_url TEXT,
            twitter_handle VARCHAR(255),
            github_handle VARCHAR(255),
            linkedin_url TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            verification_method VARCHAR(50),
            nft_badge_mint VARCHAR(255),
            reputation_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create organization profiles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS organization_profiles (
            id SERIAL PRIMARY KEY,
            org_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            org_name VARCHAR(255) NOT NULL,
            org_type VARCHAR(50),
            industry VARCHAR(100),
            employee_count VARCHAR(50),
            founded_year INTEGER,
            description TEXT,
            logo_url TEXT,
            banner_url TEXT,
            verified_domain VARCHAR(255),
            domain_verified BOOLEAN DEFAULT FALSE,
            nft_badge_mint VARCHAR(255),
            reputation_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create user wallets table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_wallets (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            wallet_address VARCHAR(255) NOT NULL,
            wallet_type VARCHAR(20) DEFAULT 'solana',
            is_primary BOOLEAN DEFAULT FALSE,
            is_verified BOOLEAN DEFAULT FALSE,
            verified_at TIMESTAMP,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, wallet_address)
        )
    """)

    # Create NFT verifications table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nft_verifications (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            nft_mint_address VARCHAR(255) UNIQUE NOT NULL,
            nft_name VARCHAR(255),
            nft_symbol VARCHAR(10),
            nft_image_url TEXT,
            verification_type VARCHAR(50),
            verified_domain VARCHAR(255),
            reputation_level VARCHAR(20) DEFAULT 'unverified',
            reputation_score INTEGER DEFAULT 0,
            metadata_uri TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            minted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create reputation scores table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reputation_scores (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            total_score INTEGER DEFAULT 0,
            email_score INTEGER DEFAULT 0,
            verification_score INTEGER DEFAULT 0,
            payment_score INTEGER DEFAULT 0,
            trust_score INTEGER DEFAULT 0,
            spam_reports INTEGER DEFAULT 0,
            positive_interactions INTEGER DEFAULT 0,
            negative_interactions INTEGER DEFAULT 0,
            emails_sent INTEGER DEFAULT 0,
            emails_received INTEGER DEFAULT 0,
            reputation_level VARCHAR(20) DEFAULT 'new',
            nft_sync_status VARCHAR(20) DEFAULT 'pending',
            last_nft_update TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create reputation events table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reputation_events (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            event_category VARCHAR(50),
            score_change INTEGER,
            description TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create generated wallets table (multi-chain)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_wallets_generated (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            solana_address VARCHAR(255) NOT NULL,
            solana_private_key_encrypted TEXT NOT NULL,
            solana_salt TEXT NOT NULL,
            evm_address VARCHAR(255) NOT NULL,
            evm_private_key_encrypted TEXT NOT NULL,
            evm_salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create RPC configuration table (user-specific)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_rpc_config (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            solana_rpc_url TEXT,
            ethereum_rpc_url TEXT,
            base_rpc_url TEXT,
            polygon_rpc_url TEXT,
            arbitrum_rpc_url TEXT,
            optimism_rpc_url TEXT,
            use_custom_rpc BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create global RPC configuration table (admin)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS global_rpc_config (
            id SERIAL PRIMARY KEY,
            config_name VARCHAR(50) UNIQUE NOT NULL,
            solana_rpc_url TEXT DEFAULT 'https://mainnet.helius-rpc.com/?api-key=8675550c-52de-4fa5-8540-760140875275',
            ethereum_rpc_url TEXT DEFAULT 'https://eth.llamarpc.com',
            base_rpc_url TEXT DEFAULT 'https://mainnet.base.org',
            polygon_rpc_url TEXT DEFAULT 'https://polygon-rpc.com',
            arbitrum_rpc_url TEXT DEFAULT 'https://arb1.arbitrum.io/rpc',
            optimism_rpc_url TEXT DEFAULT 'https://mainnet.optimism.io',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default RPC configuration
    cur.execute("""
        INSERT INTO global_rpc_config (config_name)
        VALUES ('default')
        ON CONFLICT (config_name) DO NOTHING
    """)

    # Create email folders/labels table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_folders (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            folder_name VARCHAR(100) NOT NULL,
            folder_type VARCHAR(50) DEFAULT 'custom',
            color VARCHAR(20),
            icon VARCHAR(50),
            is_system BOOLEAN DEFAULT FALSE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, folder_name)
        )
    """)

    # Create email labels table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_labels (
            id SERIAL PRIMARY KEY,
            message_id VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            label_name VARCHAR(100) NOT NULL,
            ai_generated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, user_email, label_name)
        )
    """)

    # ========== ABUSE PREVENTION SYSTEM TABLES ==========

    # User reputation tracking (abuse prevention)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_reputation (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL,
            current_score INTEGER DEFAULT 100 CHECK (current_score >= 0 AND current_score <= 100),
            tier VARCHAR(20) DEFAULT 'normal' CHECK (tier IN ('normal', 'warning', 'throttle', 'walled', 'frozen')),
            is_frozen BOOLEAN DEFAULT FALSE,
            last_violation_at TIMESTAMP,
            last_score_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_reports_received INTEGER DEFAULT 0,
            total_reports_filed INTEGER DEFAULT 0,
            false_report_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User abuse reports (spam/abuse reports)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS abuse_reports (
            id SERIAL PRIMARY KEY,
            reporter_email VARCHAR(255) NOT NULL,
            reported_email VARCHAR(255) NOT NULL,
            reporter_score INTEGER,
            impact_multiplier DECIMAL(3,2),
            score_penalty INTEGER,
            reason VARCHAR(100),
            details TEXT,
            email_subject VARCHAR(500),
            email_date TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'dismissed', 'false_report')),
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_date DATE DEFAULT CURRENT_DATE,
            UNIQUE(reporter_email, reported_email, report_date)
        )
    """)

    # Bounce tracking
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounce_tracking (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            bounce_type VARCHAR(50),
            bounce_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Spam trap hits (honeypot addresses)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spam_trap_hits (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            trap_address VARCHAR(255) NOT NULL,
            email_subject VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sending velocity violations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS velocity_violations (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            emails_sent INTEGER NOT NULL,
            time_window INTEGER NOT NULL,
            threshold_exceeded BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Penalty notifications log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS penalty_notifications (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            notification_type VARCHAR(50) NOT NULL,
            tier VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL,
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Spam trap addresses (honeypots)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spam_traps (
            id SERIAL PRIMARY KEY,
            trap_email VARCHAR(255) UNIQUE NOT NULL,
            trap_type VARCHAR(50) DEFAULT 'honeypot',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create PortID encrypted backups table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portid_backups (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) UNIQUE NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            app_id VARCHAR(100) NOT NULL,
            encrypted_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
