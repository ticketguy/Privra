#!/usr/bin/env python3
"""Migration script to add email encryption key columns"""

import os
import psycopg2

def migrate_database():
    """Add email encryption key columns to existing database"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'db'),
            database=os.getenv('DB_NAME', 'privramail'),
            user=os.getenv('DB_USER', 'privramail'),
            password=os.getenv('DB_PASSWORD')
        )

        cur = conn.cursor()

        print("Adding email encryption key columns to users table...")

        # Add email encryption key columns to users table
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_public_key TEXT,
            ADD COLUMN IF NOT EXISTS email_private_key_encrypted TEXT
        """)

        conn.commit()
        cur.close()
        conn.close()

        print("✓ Migration completed successfully!")
        print("  - Added email_public_key column")
        print("  - Added email_private_key_encrypted column")
        print("\nExisting users will need to regenerate their keys on next login.")

        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == '__main__':
    migrate_database()
