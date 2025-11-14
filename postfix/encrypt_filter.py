#!/usr/bin/env python3
"""
Postfix content filter for incoming email encryption
Encrypts emails to Privra users with their public keys
"""

import sys
import email
import psycopg2
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import crypto utilities
sys.path.append('/app')
from crypto_utils import encrypt_email_content

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def get_recipient_public_key(recipient_email):
    """Get recipient's public key from database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT email_public_key FROM users
               WHERE email = %s AND active = TRUE AND email_public_key IS NOT NULL""",
            (recipient_email,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        print(f"Error fetching public key: {e}", file=sys.stderr)
        return None

def encrypt_incoming_email(msg, recipient_email):
    """Encrypt email body for Privra recipient"""
    try:
        # Get recipient's public key
        public_key = get_recipient_public_key(recipient_email)
        if not public_key:
            # Recipient doesn't have encryption - pass through unchanged
            return msg, False

        # Check if already encrypted
        if msg.get('X-Privra-Encrypted', '').lower() == 'true':
            # Already encrypted, pass through
            return msg, False

        # Extract email body
        if msg.is_multipart():
            # Find text/plain part
            body = None
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    break

            if not body:
                # No text/plain, pass through
                return msg, False
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

        # Encrypt the body
        encrypted_body = encrypt_email_content(body, public_key)

        # Create new message with encrypted body
        new_msg = MIMEMultipart() if msg.is_multipart() else MIMEText(encrypted_body)

        # Copy headers
        for header, value in msg.items():
            if header.lower() not in ['content-type', 'content-transfer-encoding', 'mime-version']:
                new_msg[header] = value

        # Add encryption header
        new_msg['X-Privra-Encrypted'] = 'true'
        new_msg['X-Privra-Gateway-Encrypted'] = 'true'

        # Set encrypted body
        if msg.is_multipart():
            new_msg.attach(MIMEText(encrypted_body, 'plain'))
        else:
            new_msg.set_payload(encrypted_body)

        return new_msg, True

    except Exception as e:
        print(f"Encryption error: {e}", file=sys.stderr)
        return msg, False

def main():
    """Main content filter"""
    try:
        # Read email from stdin
        raw_email = sys.stdin.buffer.read()
        msg = email.message_from_bytes(raw_email)

        # Get recipient from To header
        recipient = msg.get('To', '').strip()
        if '<' in recipient:
            # Extract email from "Name <email@domain.com>" format
            recipient = recipient.split('<')[1].split('>')[0].strip()

        # Try to encrypt
        new_msg, encrypted = encrypt_incoming_email(msg, recipient)

        # Output to stdout for delivery
        sys.stdout.buffer.write(new_msg.as_bytes())

        if encrypted:
            print(f"Encrypted incoming email for {recipient}", file=sys.stderr)
        else:
            print(f"Passed through email for {recipient} (no encryption)", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"Content filter error: {e}", file=sys.stderr)
        # On error, output original email
        sys.stdout.buffer.write(raw_email)
        return 1

if __name__ == '__main__':
    sys.exit(main())
