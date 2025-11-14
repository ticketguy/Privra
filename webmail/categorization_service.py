#!/usr/bin/env python3
"""
Background service for automatic email categorization
Categorizes incoming emails and stores results in database
"""

import imaplib
import email
import psycopg2
import os
import time
import sys
from email_categorizer import EmailCategorizer
from email.header import decode_header

class CategorizationService:
    """Background service for email categorization"""

    def __init__(self):
        """Initialize categorization service"""
        self.categorizer = EmailCategorizer()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }
        self.imap_host = os.getenv('IMAP_HOST', 'dovecot')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.check_interval = int(os.getenv('CATEGORIZATION_INTERVAL', '60'))  # seconds

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_all_users(self):
        """Get all active users from database"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute("SELECT email, password FROM users WHERE active = TRUE AND password IS NOT NULL")
            users = cur.fetchall()
            cur.close()
            conn.close()
            return users
        except Exception as e:
            print(f"Error fetching users: {e}", file=sys.stderr)
            return []

    def connect_imap(self, email_addr, password):
        """Connect to IMAP server for a user"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(email_addr, password)
            return mail
        except Exception as e:
            print(f"IMAP connection error for {email_addr}: {e}", file=sys.stderr)
            return None

    def decode_mime_words(self, s):
        """Decode MIME encoded words"""
        if not s:
            return ""
        try:
            decoded_fragments = decode_header(s)
            fragments = []
            for fragment, encoding in decoded_fragments:
                if isinstance(fragment, bytes):
                    fragments.append(fragment.decode(encoding or 'utf-8', errors='replace'))
                else:
                    fragments.append(fragment)
            return ''.join(fragments)
        except:
            return str(s)

    def get_email_body(self, msg):
        """Extract email body from message"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors='replace')
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode(errors='replace')
            except:
                pass
        return body

    def is_already_categorized(self, user_email, email_id):
        """Check if email is already categorized"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM email_categories
                WHERE user_email = %s AND email_id = %s
            """, (user_email, email_id))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result is not None
        except Exception as e:
            print(f"Error checking categorization: {e}", file=sys.stderr)
            return False

    def save_categorization(self, user_email, email_id, category, confidence=0.8):
        """Save email categorization to database"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO email_categories (user_email, email_id, category, confidence)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_email, email_id)
                DO UPDATE SET category = %s, confidence = %s
            """, (user_email, email_id, category, confidence, category, confidence))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving categorization: {e}", file=sys.stderr)
            return False

    def categorize_user_emails(self, user_email, password):
        """Categorize uncategorized emails for a user"""
        mail = self.connect_imap(user_email, password)
        if not mail:
            return 0

        categorized_count = 0

        try:
            # Select inbox
            mail.select('INBOX')

            # Search for all emails
            status, messages = mail.search(None, 'ALL')
            if status != 'OK':
                mail.logout()
                return 0

            email_ids = messages[0].split()

            # Process last 100 emails (to avoid processing entire mailbox on first run)
            recent_emails = email_ids[-100:] if len(email_ids) > 100 else email_ids

            for email_id in recent_emails:
                try:
                    email_id_str = email_id.decode()

                    # Check if already categorized
                    if self.is_already_categorized(user_email, email_id_str):
                        continue

                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Extract fields
                    subject = self.decode_mime_words(msg.get('Subject', ''))
                    sender = msg.get('From', '')
                    body = self.get_email_body(msg)

                    # Categorize
                    category = self.categorizer.categorize(subject, sender, body)

                    # Save to database
                    if self.save_categorization(user_email, email_id_str, category):
                        categorized_count += 1
                        print(f"Categorized email {email_id_str} for {user_email} as '{category}'", file=sys.stderr)

                except Exception as e:
                    print(f"Error processing email {email_id}: {e}", file=sys.stderr)
                    continue

            mail.logout()

        except Exception as e:
            print(f"Error categorizing emails for {user_email}: {e}", file=sys.stderr)

        return categorized_count

    def run_categorization_cycle(self):
        """Run one categorization cycle for all users"""
        print("Starting categorization cycle...", file=sys.stderr)

        users = self.get_all_users()
        total_categorized = 0

        for user_email, password in users:
            try:
                count = self.categorize_user_emails(user_email, password)
                total_categorized += count
            except Exception as e:
                print(f"Error processing user {user_email}: {e}", file=sys.stderr)
                continue

        print(f"Categorization cycle complete. Categorized {total_categorized} emails.", file=sys.stderr)
        return total_categorized

    def run(self):
        """Run categorization service continuously"""
        print("Email categorization service started", file=sys.stderr)
        print(f"Check interval: {self.check_interval} seconds", file=sys.stderr)

        while True:
            try:
                self.run_categorization_cycle()
            except Exception as e:
                print(f"Error in categorization cycle: {e}", file=sys.stderr)

            # Wait before next cycle
            time.sleep(self.check_interval)


if __name__ == '__main__':
    service = CategorizationService()
    service.run()
