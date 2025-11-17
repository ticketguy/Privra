#!/usr/bin/env python3
"""
Postfix Policy Server for Reputation System
Integrates with Postfix to enforce reputation-based restrictions
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reputation_service import reputation_service


def read_policy_request():
    """Read policy request from Postfix"""
    request = {}
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        try:
            key, value = line.split('=', 1)
            request[key] = value
        except ValueError:
            continue
    return request


def handle_policy_request(request):
    """Process policy request and return action"""
    sender = request.get('sender', '')
    recipient = request.get('recipient', '')

    if not sender or sender == '<>':
        # Allow bounce messages
        return 'DUNNO'

    # Check if sender is frozen or rate limited
    can_send, reason = reputation_service.can_send_email(sender)
    if not can_send:
        return f'DEFER_IF_PERMIT {reason}'

    # Check spam trap
    if reputation_service.check_spam_trap(sender, recipient):
        return 'REJECT Spam detected'

    # Check if sending to external address while in walled garden mode
    if not reputation_service.can_send_external(sender):
        # Check if recipient is local
        local_domains = os.getenv('MAIL_DOMAIN', 'localhost').split(',')
        recipient_domain = recipient.split('@')[-1] if '@' in recipient else ''

        if recipient_domain not in local_domains:
            return 'REJECT External sending restricted - contact admin'

    return 'DUNNO'


def main():
    """Main policy server loop"""
    while True:
        request = read_policy_request()

        if not request:
            # Empty request = end of connection
            break

        action = handle_policy_request(request)

        # Send response to Postfix
        sys.stdout.write(f'action={action}\n\n')
        sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Policy server error: {e}", file=sys.stderr)
        sys.exit(1)
