#!/usr/bin/env python3
"""
Postfix content filter for outgoing email decryption
Decrypts emails to external recipients for compatibility
"""

import sys
import email
import psycopg2
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import crypto utilities
sys.path.append('/app')
from crypto_utils import decrypt_email_content

def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        database=os.getenv('DB_NAME', 'privramail'),
        user=os.getenv('DB_USER', 'privramail'),
        password=os.getenv('DB_PASSWORD')
    )

def is_privra_recipient(recipient_email):
    """Check if recipient is a Privra user"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT email FROM users
               WHERE email = %s AND active = TRUE""",
            (recipient_email,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"Error checking recipient: {e}", file=sys.stderr)
        return False

def get_sender_private_key(sender_email):
    """Get sender's decrypted private key from database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT email_private_key_encrypted, recovery_key FROM users
               WHERE email = %s AND active = TRUE""",
            (sender_email,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0] and result[1]:
            from crypto_utils import decrypt_private_key_with_recovery_key
            private_key_pem = decrypt_private_key_with_recovery_key(
                result[0], result[1]
            )
            return private_key_pem
        return None
    except Exception as e:
        print(f"Error fetching private key: {e}", file=sys.stderr)
        return None

def decrypt_outgoing_email(msg, sender_email, recipient_email):
    """Decrypt email body for external recipient"""
    try:
        # Check if email is encrypted
        if msg.get('X-Privra-Encrypted', '').lower() != 'true':
            # Not encrypted, pass through
            return msg, False

        # Check if recipient is external
        if is_privra_recipient(recipient_email):
            # Privra recipient, keep encrypted
            return msg, False

        # Get sender's private key for decryption
        private_key = get_sender_private_key(sender_email)
        if not private_key:
            # Can't decrypt, pass through
            print(f"Warning: Cannot decrypt email from {sender_email} - no private key", file=sys.stderr)
            return msg, False

        # Extract encrypted email body
        if msg.is_multipart():
            # Find text/plain part
            encrypted_body = None
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    encrypted_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    break

            if not encrypted_body:
                # No text/plain, pass through
                return msg, False
        else:
            encrypted_body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

        # Decrypt the body
        decrypted_body = decrypt_email_content(encrypted_body, private_key)

        # Create new message with decrypted body
        new_msg = MIMEMultipart() if msg.is_multipart() else MIMEText(decrypted_body)

        # Copy headers (except encryption headers)
        for header, value in msg.items():
            if header.lower() not in ['content-type', 'content-transfer-encoding',
                                       'mime-version', 'x-privra-encrypted',
                                       'x-privra-gateway-encrypted']:
                new_msg[header] = value

        # Add gateway decryption header
        new_msg['X-Privra-Gateway-Decrypted'] = 'true'

        # Set decrypted body
        if msg.is_multipart():
            new_msg.attach(MIMEText(decrypted_body, 'plain'))
        else:
            new_msg.set_payload(decrypted_body)

        return new_msg, True

    except Exception as e:
        print(f"Decryption error: {e}", file=sys.stderr)
        return msg, False

def main():
    """Main content filter"""
    try:
        # Read email from stdin
        raw_email = sys.stdin.buffer.read()
        msg = email.message_from_bytes(raw_email)

        # Get sender and recipient
        sender = msg.get('From', '').strip()
        if '<' in sender:
            sender = sender.split('<')[1].split('>')[0].strip()

        recipient = msg.get('To', '').strip()
        if '<' in recipient:
            recipient = recipient.split('<')[1].split('>')[0].strip()

        # Try to decrypt if needed
        new_msg, decrypted = decrypt_outgoing_email(msg, sender, recipient)

        # Output to stdout for delivery
        sys.stdout.buffer.write(new_msg.as_bytes())

        if decrypted:
            print(f"Decrypted outgoing email from {sender} to external {recipient}", file=sys.stderr)
        else:
            print(f"Passed through email from {sender} to {recipient} (no decryption)", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"Content filter error: {e}", file=sys.stderr)
        # On error, output original email
        sys.stdout.buffer.write(raw_email)
        return 1

if __name__ == '__main__':
    sys.exit(main())
