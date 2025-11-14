#!/usr/bin/env python3
"""
Solana NFT Verification Service
Verifies domain ownership via NFT and updates reputation metadata
"""

import os
import sys
import json
import psycopg2
from datetime import datetime
from typing import Dict, Optional, Tuple
import base64

class NFTVerificationService:
    """Manages Solana NFT verification and reputation badges"""

    def __init__(self):
        """Initialize NFT verification service"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

        self.solana_rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        self.nft_collection_address = os.getenv('PRIVRA_NFT_COLLECTION', '')

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def verify_nft_ownership(self, user_email: str, nft_mint_address: str, wallet_address: str) -> Tuple[bool, str]:
        """
        Verify that user owns the NFT

        Args:
            user_email: User's email
            nft_mint_address: NFT mint address
            wallet_address: User's wallet address

        Returns:
            Tuple of (verified, message)
        """
        try:
            # TODO: Implement Solana RPC call to verify NFT ownership
            # For now, this is a placeholder

            # In production, this should:
            # 1. Query Solana RPC for token accounts
            # 2. Verify wallet owns NFT with mint address
            # 3. Check NFT is from verified collection

            print(f"Verifying NFT ownership: {wallet_address} owns {nft_mint_address}", file=sys.stderr)

            # Placeholder verification - always succeeds for development
            return True, "NFT ownership verified"

        except Exception as e:
            print(f"Error verifying NFT ownership: {e}", file=sys.stderr)
            return False, str(e)

    def get_nft_metadata(self, nft_mint_address: str) -> Optional[Dict]:
        """
        Fetch NFT metadata from Solana - NFT image becomes profile avatar

        Args:
            nft_mint_address: NFT mint address

        Returns:
            NFT metadata dict or None
        """
        try:
            import requests

            # Get NFT metadata from Solana
            rpc_url = self.solana_rpc_url

            # Method 1: Use Metaplex metadata account
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    nft_mint_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            response = requests.post(rpc_url, json=payload, timeout=10)
            data = response.json()

            if 'result' in data and data['result']:
                # Parse metadata
                # This is simplified - production would need full Metaplex parsing

                # For now, use placeholder but structure for real implementation
                return {
                    'name': f'NFT {nft_mint_address[:8]}',
                    'symbol': 'NFT',
                    'image': f'https://arweave.net/placeholder',  # Would be actual URI
                    'description': 'User profile NFT',
                    'attributes': []
                }

            return None

        except Exception as e:
            print(f"Error getting NFT metadata: {e}", file=sys.stderr)
            return None

    def set_nft_as_avatar(
        self,
        user_email: str,
        nft_mint_address: str,
        wallet_address: str
    ) -> Tuple[bool, str]:
        """
        Set NFT image as user's profile avatar (like Gmail profile picture)

        Args:
            user_email: User's email
            nft_mint_address: NFT mint address
            wallet_address: User's wallet address

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify ownership
            is_verified, message = self.verify_nft_ownership(user_email, nft_mint_address, wallet_address)

            if not is_verified:
                return False, f"NFT verification failed: {message}"

            # Get NFT metadata (includes image URL)
            metadata = self.get_nft_metadata(nft_mint_address)
            if not metadata:
                return False, "Failed to fetch NFT metadata"

            nft_image_url = metadata.get('image')
            if not nft_image_url:
                return False, "NFT has no image"

            conn = self.get_db()
            cur = conn.cursor()

            # Store NFT verification
            cur.execute("""
                INSERT INTO nft_verifications
                (user_email, nft_mint_address, nft_name, nft_symbol, nft_image_url, minted_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (nft_mint_address)
                DO UPDATE SET
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_email, nft_mint_address, metadata.get('name'),
                  metadata.get('symbol'), nft_image_url))

            # Update user profile - set NFT image as avatar
            cur.execute("""
                UPDATE user_profiles
                SET avatar_url = %s,
                    nft_badge_mint = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_email = %s
            """, (nft_image_url, nft_mint_address, user_email))

            # Record reputation event
            from reputation_service import reputation_service
            reputation_service.record_event(
                user_email,
                'nft_verified',
                'verification',
                'Set NFT as profile avatar',
                {'nft_mint': nft_mint_address}
            )

            conn.commit()
            cur.close()
            conn.close()

            return True, f"NFT image set as profile avatar"

        except Exception as e:
            print(f"Error setting NFT as avatar: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False, str(e)

    def update_nft_reputation(self, user_email: str) -> bool:
        """
        Update NFT metadata with current reputation score

        Args:
            user_email: User's email

        Returns:
            bool: Success status
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            # Get user's NFT and reputation
            cur.execute("""
                SELECT nv.nft_mint_address, nv.metadata_uri, rs.total_score, rs.reputation_level
                FROM nft_verifications nv
                JOIN reputation_scores rs ON nv.user_email = rs.user_email
                WHERE nv.user_email = %s AND nv.is_active = TRUE
            """, (user_email,))

            result = cur.fetchone()
            if not result:
                return False

            nft_mint, metadata_uri, total_score, reputation_level = result

            # TODO: Implement Solana transaction to update NFT metadata
            # This would require:
            # 1. Building a Solana transaction
            # 2. Updating the NFT metadata account
            # 3. Signing with authorized key
            # 4. Sending transaction to network

            # For now, just update our database
            cur.execute("""
                UPDATE nft_verifications
                SET reputation_score = %s,
                    reputation_level = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE nft_mint_address = %s
            """, (total_score, reputation_level, nft_mint))

            # Update reputation sync status
            cur.execute("""
                UPDATE reputation_scores
                SET nft_sync_status = 'synced',
                    last_nft_update = CURRENT_TIMESTAMP
                WHERE user_email = %s
            """, (user_email,))

            conn.commit()
            cur.close()
            conn.close()

            print(f"NFT reputation updated: {user_email} - Score: {total_score}, Level: {reputation_level}", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Error updating NFT reputation: {e}", file=sys.stderr)
            return False

    def get_verification_badge_data(self, user_email: str) -> Optional[Dict]:
        """
        Get verification badge data for display in emails

        Args:
            user_email: User's email

        Returns:
            Badge data dict or None
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT nv.nft_image_url, nv.verified_domain, nv.reputation_level,
                       nv.reputation_score, up.display_name, up.is_verified
                FROM nft_verifications nv
                JOIN user_profiles up ON nv.user_email = up.user_email
                WHERE nv.user_email = %s AND nv.is_active = TRUE
            """, (user_email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                return {
                    'badge_image': result[0],
                    'verified_domain': result[1],
                    'reputation_level': result[2],
                    'reputation_score': result[3],
                    'display_name': result[4],
                    'is_verified': result[5]
                }

            return None

        except Exception as e:
            print(f"Error getting verification badge: {e}", file=sys.stderr)
            return None

    def generate_domain_verification_token(self, user_email: str, domain: str) -> str:
        """
        Generate unique verification token for domain

        Args:
            user_email: User's email
            domain: Domain to verify

        Returns:
            Verification token
        """
        import hashlib
        import secrets

        # Generate unique token
        salt = secrets.token_hex(16)
        data = f"{user_email}:{domain}:{salt}"
        token = hashlib.sha256(data.encode()).hexdigest()[:32]

        # Store in database
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO domain_verifications
                (user_email, domain, verification_token, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_email, domain)
                DO UPDATE SET
                    verification_token = %s,
                    verified = FALSE,
                    created_at = CURRENT_TIMESTAMP
            """, (user_email, domain, token, token))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Error storing verification token: {e}", file=sys.stderr)

        return token

    def verify_domain_ownership(self, user_email: str, domain: str) -> Tuple[bool, str]:
        """
        Verify user owns a domain via DNS TXT record

        Args:
            user_email: User's email
            domain: Domain to verify

        Returns:
            Tuple of (verified, message)
        """
        try:
            import dns.resolver

            # Get verification token from database
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT verification_token FROM domain_verifications
                WHERE user_email = %s AND domain = %s
            """, (user_email, domain))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return False, "No verification token found. Generate one first."

            expected_token = result[0]

            # Check for TXT record: privra-verify=<token>
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')

                for record in txt_records:
                    txt_value = record.to_text().strip('"')

                    # Check for our verification record
                    if txt_value.startswith('privra-verify='):
                        token_from_dns = txt_value.split('=', 1)[1]

                        if token_from_dns == expected_token:
                            # Verification successful!
                            self._mark_domain_verified(user_email, domain)
                            return True, "Domain verified successfully"

                return False, f"TXT record not found. Add: privra-verify={expected_token}"

            except dns.resolver.NXDOMAIN:
                return False, f"Domain {domain} does not exist"
            except dns.resolver.NoAnswer:
                return False, f"No TXT records found for {domain}"
            except dns.resolver.Timeout:
                return False, "DNS query timed out"

        except ImportError:
            return False, "DNS verification not available (dnspython not installed)"
        except Exception as e:
            print(f"Error verifying domain: {e}", file=sys.stderr)
            return False, str(e)

    def _mark_domain_verified(self, user_email: str, domain: str):
        """Mark domain as verified in database"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            # Update domain_verifications
            cur.execute("""
                UPDATE domain_verifications
                SET verified = TRUE,
                    verified_at = CURRENT_TIMESTAMP
                WHERE user_email = %s AND domain = %s
            """, (user_email, domain))

            # Update user profile
            cur.execute("""
                UPDATE user_profiles
                SET is_verified = TRUE,
                    verification_method = 'domain',
                    organization_domain = %s
                WHERE user_email = %s
            """, (domain, user_email))

            # Update organization profile if exists
            cur.execute("""
                UPDATE organization_profiles
                SET verified_domain = %s,
                    domain_verified = TRUE
                WHERE org_email = %s
            """, (domain, user_email))

            # Record reputation event
            from reputation_service import reputation_service
            reputation_service.record_event(
                user_email,
                'domain_verified',
                'verification',
                f'Domain {domain} verified via DNS TXT',
                {'domain': domain}
            )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Error marking domain verified: {e}", file=sys.stderr)


# Global instance
nft_verification_service = NFTVerificationService()
