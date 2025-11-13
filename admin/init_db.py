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
            password VARCHAR(255) NOT NULL,
            domain VARCHAR(255) NOT NULL,
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
            password VARCHAR(255) NOT NULL,
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
