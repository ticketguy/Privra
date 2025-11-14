#!/usr/bin/env python3
"""
Database migration for email categorization
Adds category column to emails table
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
    """Add category column to database"""
    try:
        print("🔄 Starting email categorization migration...")

        conn = get_db()
        cur = conn.cursor()

        # Check if category column already exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'emails' AND column_name = 'category'
        """)

        if cur.fetchone():
            print("⚠️  Category column already exists, skipping...")
            cur.close()
            conn.close()
            return

        # Add category column to emails table
        print("📝 Adding category column to emails table...")
        cur.execute("""
            ALTER TABLE emails
            ADD COLUMN category VARCHAR(50) DEFAULT 'inbox'
        """)

        # Create index for faster category queries
        print("📝 Creating index on category column...")
        cur.execute("""
            CREATE INDEX idx_emails_category ON emails(category)
        """)

        # Create index on recipient + category for inbox queries
        print("📝 Creating composite index on recipient and category...")
        cur.execute("""
            CREATE INDEX idx_emails_recipient_category ON emails(recipient, category)
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show summary
        cur.execute("SELECT COUNT(*) FROM emails")
        count = cur.fetchone()[0]
        print(f"📊 Total emails in database: {count}")
        print(f"📊 All emails categorized as 'inbox' by default")

        cur.close()
        conn.close()

        print("\n📌 Next steps:")
        print("   1. Restart webmail service to apply changes")
        print("   2. Run categorization on existing emails (optional)")
        print("   3. New incoming emails will be auto-categorized")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    migrate()
