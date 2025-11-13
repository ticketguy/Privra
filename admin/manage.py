#!/usr/bin/env python3
"""Command-line user management"""

import sys
import os
import psycopg2
import bcrypt

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def adduser(email, password):
    """Add a new user"""
    domain = email.split('@')[1] if '@' in email else os.getenv('MAIL_DOMAIN')
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password, domain) VALUES (%s, %s, %s)",
            (email, hashed, domain)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ User {email} created successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def deluser(email):
    """Delete a user"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ User {email} deleted successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def passwd(email, password):
    """Change user password"""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
            (hashed, email)
        )
        if cur.rowcount == 0:
            print(f"❌ User {email} not found")
            sys.exit(1)
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Password updated for {email}!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def listusers():
    """List all users"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT email, active, created_at FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        cur.close()
        conn.close()

        print("\n📧 Email Users:")
        print("-" * 60)
        for email, active, created_at in users:
            status = "✓ Active" if active else "✗ Inactive"
            print(f"{email:40} {status:15} {created_at.strftime('%Y-%m-%d %H:%M')}")
        print("-" * 60)
        print(f"Total: {len(users)} users\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage.py adduser <email> <password>")
        print("  python manage.py deluser <email>")
        print("  python manage.py passwd <email> <new_password>")
        print("  python manage.py listusers")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'adduser' and len(sys.argv) == 4:
        adduser(sys.argv[2], sys.argv[3])
    elif command == 'deluser' and len(sys.argv) == 3:
        deluser(sys.argv[2])
    elif command == 'passwd' and len(sys.argv) == 4:
        passwd(sys.argv[2], sys.argv[3])
    elif command == 'listusers':
        listusers()
    else:
        print("Invalid command or arguments")
        sys.exit(1)
