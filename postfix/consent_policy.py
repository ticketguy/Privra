#!/usr/bin/env python3
"""
Postfix policy service for sender consent checking
Implements pay-to-send and consent system
"""

import sys
import os
import psycopg2
import hashlib
import secrets
from datetime import datetime, timedelta

class ConsentPolicy:
    """Policy server for checking sender consent"""

    def __init__(self):
        """Initialize policy server"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def check_policy(self, request):
        """
        Check if sender is allowed to send to recipient

        Args:
            request: dict of Postfix policy request attributes

        Returns:
            str: Policy action (DUNNO, REJECT, OK, etc.)
        """
        sender = request.get('sender', '').lower()
        recipient = request.get('recipient', '').lower()

        if not sender or not recipient:
            return 'DUNNO'

        # Extract domain from sender
        sender_domain = sender.split('@')[1] if '@' in sender else ''

        try:
            conn = self.get_db()
            cur = conn.cursor()

            # Check if recipient is a Privra user
            cur.execute("SELECT email FROM users WHERE email = %s AND active = TRUE", (recipient,))
            if not cur.fetchone():
                # Not a Privra user, pass through
                cur.close()
                conn.close()
                return 'DUNNO'

            # Check if sender is also a Privra user (whitelist internal)
            cur.execute("SELECT email FROM users WHERE email = %s AND active = TRUE", (sender,))
            if cur.fetchone():
                # Internal Privra email, always allow
                cur.close()
                conn.close()
                return 'DUNNO'

            # Get recipient's consent settings
            cur.execute("""
                SELECT require_consent, require_payment, whitelist_mode
                FROM consent_settings
                WHERE user_email = %s
            """, (recipient,))
            settings = cur.fetchone()

            if not settings:
                # No settings, allow by default
                cur.close()
                conn.close()
                return 'DUNNO'

            require_consent, require_payment, whitelist_mode = settings

            # If no consent required, allow
            if not require_consent and not require_payment and not whitelist_mode:
                cur.close()
                conn.close()
                return 'DUNNO'

            # Check blacklist first
            cur.execute("""
                SELECT id FROM sender_blacklist
                WHERE recipient_email = %s
                AND (sender_email = %s OR sender_domain = %s)
            """, (recipient, sender, sender_domain))
            if cur.fetchone():
                cur.close()
                conn.close()
                return f'REJECT Sender {sender} is blacklisted'

            # Check whitelist
            cur.execute("""
                SELECT id FROM sender_whitelist
                WHERE recipient_email = %s
                AND (sender_email = %s OR sender_domain = %s)
            """, (recipient, sender, sender_domain))
            if cur.fetchone():
                # Sender is whitelisted
                cur.close()
                conn.close()
                return 'DUNNO'

            # If whitelist mode is enabled and sender not in whitelist, reject
            if whitelist_mode:
                cur.close()
                conn.close()
                return f'REJECT Sender {sender} not in whitelist. Request consent at https://privra.com/consent'

            # Check if consent already exists
            cur.execute("""
                SELECT status FROM consent_requests
                WHERE recipient_email = %s AND sender_email = %s
                AND status = 'approved'
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1
            """, (recipient, sender))
            if cur.fetchone():
                # Consent already granted
                cur.close()
                conn.close()
                return 'DUNNO'

            # Check if consent required or payment required
            if require_consent or require_payment:
                # Check for pending consent request
                cur.execute("""
                    SELECT id, token FROM consent_requests
                    WHERE recipient_email = %s AND sender_email = %s
                    AND status = 'pending'
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC LIMIT 1
                """, (recipient, sender))
                existing = cur.fetchone()

                if not existing:
                    # Create new consent request
                    token = secrets.token_urlsafe(32)
                    subject = request.get('subject', 'No subject')
                    expires_at = datetime.now() + timedelta(days=7)

                    cur.execute("""
                        INSERT INTO consent_requests
                        (recipient_email, sender_email, token, email_subject, expires_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (recipient, sender, token, subject, expires_at))
                    consent_request_id = cur.fetchone()[0]
                    conn.commit()

                    # Generate X402 payment request if payment required
                    payment_url = None
                    if require_payment:
                        try:
                            # Get payment amount from settings
                            cur.execute("""
                                SELECT payment_amount_sats FROM consent_settings
                                WHERE user_email = %s
                            """, (recipient,))
                            payment_result = cur.fetchone()
                            payment_amount_sats = payment_result[0] if payment_result else 1000

                            # Convert sats to USDC (rough estimation: 1 sat ≈ $0.0003)
                            # For now, use a fixed USDC amount
                            amount_usdc = os.getenv('X402_DEFAULT_AMOUNT_USDC', '0.01')

                            # Import X402 service
                            from x402_service import x402_service

                            # Generate payment request
                            payment_request = x402_service.generate_payment_request(
                                sender_email=sender,
                                recipient_email=recipient,
                                consent_request_id=consent_request_id,
                                amount_usdc=amount_usdc
                            )

                            payment_url = payment_request['payment_url']
                            print(f"Generated X402 payment request: {payment_url}", file=sys.stderr)

                        except Exception as e:
                            print(f"Error generating X402 payment request: {e}", file=sys.stderr)
                            import traceback
                            traceback.print_exc(file=sys.stderr)

                    cur.close()
                    conn.close()

                    # Defer the email with payment URL if available
                    if payment_url:
                        return f'DEFER Payment required (HTTP 402). Pay at: {payment_url} to send email to {recipient}. AI agents: Use X402 protocol.'
                    else:
                        return f'DEFER Consent required. Sender {sender} must request permission from {recipient}'
                else:
                    # Existing consent request - check if it has X402 payment
                    consent_request_id = existing[0]

                    # Check if payment already made
                    cur.execute("""
                        SELECT payment_url, status FROM x402_payment_requests
                        WHERE consent_request_id = %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (consent_request_id,))
                    x402_result = cur.fetchone()

                    cur.close()
                    conn.close()

                    if x402_result and x402_result[0]:
                        payment_url = x402_result[0]
                        payment_status = x402_result[1]

                        if payment_status == 'paid':
                            # Payment completed, allow email through
                            return 'DUNNO'
                        else:
                            # Payment pending
                            return f'DEFER Payment required (HTTP 402). Pay at: {payment_url} to send email to {recipient}. AI agents: Use X402 protocol.'
                    else:
                        # No X402 payment, use standard consent message
                        return f'DEFER Consent required. Sender {sender} must request permission from {recipient}'

            cur.close()
            conn.close()
            return 'DUNNO'

        except Exception as e:
            print(f"Policy check error: {e}", file=sys.stderr)
            # On error, allow email through (fail open)
            return 'DUNNO'

    def handle_request(self, request_text):
        """
        Parse and handle Postfix policy request

        Args:
            request_text: Raw request from Postfix

        Returns:
            str: Policy response
        """
        request = {}
        for line in request_text.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                request[key] = value

        action = self.check_policy(request)
        return f"action={action}\n\n"

    def run(self):
        """Run policy server (stdin/stdout mode)"""
        print("Consent policy server started", file=sys.stderr)

        while True:
            try:
                # Read request from stdin
                request_lines = []
                while True:
                    line = sys.stdin.readline()
                    if not line:
                        # EOF, exit
                        return
                    if line.strip() == '':
                        # Empty line marks end of request
                        break
                    request_lines.append(line)

                if not request_lines:
                    continue

                request_text = ''.join(request_lines)
                response = self.handle_request(request_text)

                # Send response to stdout
                sys.stdout.write(response)
                sys.stdout.flush()

            except Exception as e:
                print(f"Error handling request: {e}", file=sys.stderr)
                # Send DUNNO on error (fail open)
                sys.stdout.write("action=DUNNO\n\n")
                sys.stdout.flush()


if __name__ == '__main__':
    policy = ConsentPolicy()
    policy.run()
