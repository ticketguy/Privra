#!/usr/bin/env python3
"""
X402 Payment Service for Email Consent
Supports Solana and Base (EVM) networks
"""

import os
import sys
import json
import secrets
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class X402PaymentService:
    """X402 payment request generator and verifier"""

    # Network configurations (Mainnet only)
    NETWORKS = {
        'solana-mainnet': {
            'name': 'Solana Mainnet',
            'usdc_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC SPL token
            'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
            'explorer': 'https://solscan.io/tx/'
        },
        'base-mainnet': {
            'name': 'Base Mainnet',
            'usdc_address': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # USDC on Base
            'rpc_url': os.getenv('BASE_RPC_URL', 'https://mainnet.base.org'),
            'explorer': 'https://basescan.org/tx/'
        }
    }

    def __init__(self):
        """Initialize X402 payment service"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

        # Payment configuration
        self.default_amount_usdc = os.getenv('X402_DEFAULT_AMOUNT_USDC', '0.01')  # $0.01
        self.default_network = os.getenv('X402_DEFAULT_NETWORK', 'solana-mainnet')
        self.payment_address_solana = os.getenv('X402_SOLANA_ADDRESS', '')
        self.payment_address_base = os.getenv('X402_BASE_ADDRESS', '')
        self.payment_timeout_seconds = int(os.getenv('X402_TIMEOUT_SECONDS', '3600'))  # 1 hour

        # X402 service URLs
        self.x402_base_url = os.getenv('X402_BASE_URL', 'https://admin.privra.xyz/x402')

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def generate_payment_request(
        self,
        sender_email: str,
        recipient_email: str,
        consent_request_id: int,
        network: Optional[str] = None,
        amount_usdc: Optional[str] = None
    ) -> Dict:
        """
        Generate X402 payment request for email consent

        Args:
            sender_email: Sender's email address
            recipient_email: Recipient's email address
            consent_request_id: ID of consent request
            network: Blockchain network (solana-mainnet, base-mainnet, etc.)
            amount_usdc: Amount in USDC (e.g., "0.01" for $0.01)

        Returns:
            Dict with payment request details
        """
        network = network or self.default_network
        amount_usdc = amount_usdc or self.default_amount_usdc

        # Get network config
        if network not in self.NETWORKS:
            raise ValueError(f"Unsupported network: {network}")

        network_config = self.NETWORKS[network]

        # Get payment address based on network
        if network.startswith('solana'):
            pay_to = self.payment_address_solana
        else:  # EVM networks (Base)
            pay_to = self.payment_address_base

        if not pay_to:
            raise ValueError(f"Payment address not configured for {network}")

        # Generate unique token for this payment request
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = datetime.now() + timedelta(seconds=self.payment_timeout_seconds)

        # Convert USDC amount to atomic units
        # USDC has 6 decimals on both Solana and Base
        amount_atomic = str(int(float(amount_usdc) * 1_000_000))

        # Create payment URL
        payment_url = f"{self.x402_base_url}/pay/{token}"

        # Store payment request in database
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO x402_payment_requests
                (consent_request_id, sender_email, recipient_email, payment_address,
                 amount_usdc, network, asset_address, payment_url, token, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (consent_request_id, sender_email, recipient_email, pay_to,
                  amount_usdc, network, network_config['usdc_address'],
                  payment_url, token, expires_at))

            payment_request_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Error storing X402 payment request: {e}", file=sys.stderr)
            raise

        # Build X402 payment requirement
        payment_requirement = {
            "x402Version": 1,
            "accepts": [
                {
                    "scheme": "exact",
                    "network": network,
                    "maxAmountRequired": amount_atomic,
                    "resource": payment_url,
                    "description": f"Email delivery to {recipient_email}",
                    "mimeType": "application/json",
                    "payTo": pay_to,
                    "maxTimeoutSeconds": self.payment_timeout_seconds,
                    "asset": network_config['usdc_address'],
                    "extra": {
                        "sender": sender_email,
                        "recipient": recipient_email,
                        "token": token,
                        "type": "email_consent"
                    }
                }
            ],
            "error": f"Payment required to send email to {recipient_email}. AI agents and unauthorized senders must pay ${amount_usdc} USDC to deliver this email."
        }

        return {
            "payment_request_id": payment_request_id,
            "token": token,
            "payment_url": payment_url,
            "amount_usdc": amount_usdc,
            "network": network,
            "pay_to": pay_to,
            "expires_at": expires_at.isoformat(),
            "payment_requirement": payment_requirement
        }

    def verify_payment(self, token: str, payment_header: str) -> Tuple[bool, Optional[str]]:
        """
        Verify X402 payment

        Args:
            token: Unique payment request token
            payment_header: Base64-encoded X-PAYMENT header

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            # Get payment request
            cur.execute("""
                SELECT id, consent_request_id, network, amount_usdc, expires_at, status
                FROM x402_payment_requests
                WHERE token = %s
            """, (token,))

            result = cur.fetchone()
            if not result:
                return False, "Payment request not found"

            payment_id, consent_request_id, network, amount_usdc, expires_at, status = result

            # Check if already paid
            if status == 'paid':
                return True, None

            # Check expiration
            if datetime.now() > expires_at:
                return False, "Payment request expired"

            # Decode payment header
            import base64
            try:
                payment_data = json.loads(base64.b64decode(payment_header))
            except Exception as e:
                return False, f"Invalid payment header: {e}"

            # Verify payment based on network
            if network.startswith('solana'):
                tx_verified, txid = self._verify_solana_payment(payment_data, network, amount_usdc)
            else:  # Base/EVM
                tx_verified, txid = self._verify_evm_payment(payment_data, network, amount_usdc)

            if not tx_verified:
                return False, "Payment verification failed"

            # Update payment request status
            cur.execute("""
                UPDATE x402_payment_requests
                SET status = 'paid', paid_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (payment_id,))

            # Update consent request
            cur.execute("""
                UPDATE consent_requests
                SET status = 'approved', payment_received = TRUE,
                    payment_txid = %s, approved_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (txid, consent_request_id))

            # Record payment transaction
            cur.execute("""
                INSERT INTO payment_transactions
                (consent_request_id, sender_email, recipient_email, amount_usdc,
                 payment_method, payment_network, txid, x402_payment_header, status, confirmed_at)
                VALUES (
                    %s,
                    (SELECT sender_email FROM consent_requests WHERE id = %s),
                    (SELECT recipient_email FROM consent_requests WHERE id = %s),
                    %s, 'x402', %s, %s, %s, 'confirmed', CURRENT_TIMESTAMP
                )
            """, (consent_request_id, consent_request_id, consent_request_id,
                  amount_usdc, network, txid, payment_header))

            conn.commit()
            cur.close()
            conn.close()

            return True, None

        except Exception as e:
            print(f"Error verifying payment: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False, str(e)

    def _verify_solana_payment(self, payment_data: Dict, network: str, expected_amount: str) -> Tuple[bool, Optional[str]]:
        """
        Verify Solana USDC payment

        Args:
            payment_data: Decoded payment header data
            network: Solana network (mainnet/devnet)
            expected_amount: Expected USDC amount

        Returns:
            Tuple of (verified, transaction_id)
        """
        try:
            # Extract transaction signature from payment data
            txid = payment_data.get('payload', {}).get('signature')
            if not txid:
                return False, None

            # TODO: Implement Solana RPC verification
            # For now, return the txid for manual verification
            # In production, verify using Solana RPC:
            # 1. Fetch transaction by signature
            # 2. Verify it's a USDC transfer
            # 3. Verify amount matches
            # 4. Verify recipient address matches

            print(f"Solana payment verification needed for tx: {txid}", file=sys.stderr)
            print(f"Network: {network}, Expected: {expected_amount} USDC", file=sys.stderr)

            return True, txid

        except Exception as e:
            print(f"Solana verification error: {e}", file=sys.stderr)
            return False, None

    def _verify_evm_payment(self, payment_data: Dict, network: str, expected_amount: str) -> Tuple[bool, Optional[str]]:
        """
        Verify EVM (Base) USDC payment

        Args:
            payment_data: Decoded payment header data
            network: EVM network (base-mainnet/sepolia)
            expected_amount: Expected USDC amount

        Returns:
            Tuple of (verified, transaction_hash)
        """
        try:
            # Extract transaction hash from payment data
            txid = payment_data.get('payload', {}).get('txHash')
            if not txid:
                return False, None

            # TODO: Implement EVM RPC verification
            # For now, return the txid for manual verification
            # In production, verify using Base RPC:
            # 1. Fetch transaction by hash
            # 2. Verify it's a USDC transfer
            # 3. Verify amount matches
            # 4. Verify recipient address matches

            print(f"Base payment verification needed for tx: {txid}", file=sys.stderr)
            print(f"Network: {network}, Expected: {expected_amount} USDC", file=sys.stderr)

            return True, txid

        except Exception as e:
            print(f"EVM verification error: {e}", file=sys.stderr)
            return False, None

    def check_payment_status(self, token: str) -> Optional[str]:
        """
        Check if payment has been completed

        Args:
            token: Payment request token

        Returns:
            Payment status or None if not found
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT status FROM x402_payment_requests
                WHERE token = %s
            """, (token,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            return result[0] if result else None

        except Exception as e:
            print(f"Error checking payment status: {e}", file=sys.stderr)
            return None


# Global instance
x402_service = X402PaymentService()
