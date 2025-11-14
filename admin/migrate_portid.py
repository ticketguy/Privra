#!/usr/bin/env python3
"""Database migration to add PortID support"""

import os
import psycopg2

def migrate_database():
    """Add PortID columns to existing database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'db'),
            database=os.getenv('DB_NAME', 'privramail'),
            user=os.getenv('DB_USER', 'privramail'),
            password=os.getenv('DB_PASSWORD')
        )

        cur = conn.cursor()

        print("Starting PortID migration...")

        # Migrate users table
        print("Migrating users table...")
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS portid VARCHAR(255) UNIQUE,
            ADD COLUMN IF NOT EXISTS recovery_key TEXT,
            ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) DEFAULT 'password',
            ALTER COLUMN password DROP NOT NULL
        """)

        # Migrate admin_users table
        print("Migrating admin_users table...")
        cur.execute("""
            ALTER TABLE admin_users
            ADD COLUMN IF NOT EXISTS portid VARCHAR(255) UNIQUE,
            ADD COLUMN IF NOT EXISTS recovery_key TEXT,
            ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) DEFAULT 'password',
            ALTER COLUMN password DROP NOT NULL
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("✅ PortID migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    migrate_database()
