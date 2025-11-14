#!/usr/bin/env python3
"""Admin user management script"""

import os
import sys
import psycopg2
import bcrypt
from Crypto.Random import get_random_bytes

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def list_admins():
    """List all admin users"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, email, active, created_at FROM admin_users ORDER BY created_at")
    admins = cur.fetchall()
    cur.close()
    conn.close()

    print("\n📋 Admin Users:")
    print("-" * 80)
    for admin in admins:
        status = "✅ Active" if admin[2] else "❌ Inactive"
        print(f"{admin[0]:20} {admin[1]:30} {status:15} {admin[3]}")
    print("-" * 80)

def create_admin():
    """Create a new admin user"""
    print("\n➕ Create New Admin")
    username = input("Username: ")
    password = input("Password: ")
    email = input("Email (optional): ")

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO admin_users (username, password, email)
               VALUES (%s, %s, %s)""",
            (username, hashed, email or None)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Admin user '{username}' created successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")

def delete_admin():
    """Delete an admin user"""
    print("\n🗑️  Delete Admin")
    username = input("Username to delete: ")
    confirm = input(f"Are you sure you want to delete '{username}'? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Cancelled.")
        return

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_users WHERE username = %s", (username,))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        if deleted > 0:
            print(f"✅ Admin user '{username}' deleted successfully!")
        else:
            print(f"❌ Admin user '{username}' not found.")
    except Exception as e:
        print(f"❌ Error: {e}")

def change_password():
    """Change admin password"""
    print("\n🔑 Change Admin Password")
    username = input("Username: ")
    password = input("New password: ")

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE admin_users SET password = %s WHERE username = %s",
            (hashed, username)
        )
        updated = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        if updated > 0:
            print(f"✅ Password for '{username}' updated successfully!")
        else:
            print(f"❌ Admin user '{username}' not found.")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            list_admins()
        elif command == "create":
            create_admin()
        elif command == "delete":
            delete_admin()
        elif command == "passwd":
            change_password()
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        # Interactive menu
        print("\n🔧 Privra Admin Management")
        print("1. List admins")
        print("2. Create admin")
        print("3. Delete admin")
        print("4. Change password")
        print("0. Exit")

        choice = input("\nChoice: ")

        if choice == "1":
            list_admins()
        elif choice == "2":
            create_admin()
        elif choice == "3":
            delete_admin()
        elif choice == "4":
            change_password()
        elif choice == "0":
            print("Goodbye!")
        else:
            print("Invalid choice")

def print_usage():
    print("""
Usage: python manage_admins.py [command]

Commands:
  list      - List all admin users
  create    - Create a new admin user
  delete    - Delete an admin user
  passwd    - Change admin password

Interactive mode: python manage_admins.py (no arguments)
""")

if __name__ == '__main__':
    main()
