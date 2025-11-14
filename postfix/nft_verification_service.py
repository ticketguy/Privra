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
        Fetch NFT metadata from Solana

        Args:
            nft_mint_address: NFT mint address

        Returns:
            NFT metadata dict or None
        """
        try:
            # TODO: Implement Solana RPC call to get NFT metadata
            # For now, return placeholder data

            return {
                'name': f'Privra Verified Badge',
                'symbol': 'PRVRF',
                'image': 'https://privra.com/assets/nft-badge.png',
                'description': 'Verified email sender with reputation tracking',
                'attributes': [
                    {'trait_type': 'Verification Type', 'value': 'Domain'},
                    {'trait_type': 'Reputation Level', 'value': 'Trusted'},
                    {'trait_type': 'Reputation Score', 'value': '0'}
                ]
            }

        except Exception as e:
            print(f"Error getting NFT metadata: {e}", file=sys.stderr)
            return None

    def register_nft_verification(
        self,
        user_email: str,
        nft_mint_address: str,
        wallet_address: str,
        verification_type: str = 'domain',
        verified_domain: str = None
    ) -> bool:
        """
        Register NFT verification for user

        Args:
            user_email: User's email
            nft_mint_address: NFT mint address
            wallet_address: User's wallet address
            verification_type: Type of verification
            verified_domain: Domain being verified

        Returns:
            bool: Success status
        """
        try:
            # Verify ownership
            is_verified, message = self.verify_nft_ownership(user_email, nft_mint_address, wallet_address)

            if not is_verified:
                print(f"NFT verification failed: {message}", file=sys.stderr)
                return False

            # Get NFT metadata
            metadata = self.get_nft_metadata(nft_mint_address)
            if not metadata:
                print(f"Failed to fetch NFT metadata", file=sys.stderr)
                return False

            conn = self.get_db()
            cur = conn.cursor()

            # Insert or update NFT verification
            cur.execute("""
                INSERT INTO nft_verifications
                (user_email, nft_mint_address, nft_name, nft_symbol, nft_image_url,
                 verification_type, verified_domain, minted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (nft_mint_address)
                DO UPDATE SET
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (user_email, nft_mint_address, metadata.get('name'), metadata.get('symbol'),
                  metadata.get('image'), verification_type, verified_domain))

            verification_id = cur.fetchone()[0]

            # Update user profile with verification
            cur.execute("""
                UPDATE user_profiles
                SET is_verified = TRUE,
                    verification_method = %s,
                    nft_badge_mint = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_email = %s
            """, (verification_type, nft_mint_address, user_email))

            # Record reputation event
            from reputation_service import reputation_service
            reputation_service.record_event(
                user_email,
                'nft_verified',
                'verification',
                f'NFT verification via {verification_type}',
                {'nft_mint': nft_mint_address, 'domain': verified_domain}
            )

            conn.commit()
            cur.close()
            conn.close()

            print(f"NFT verification registered: {user_email} - {nft_mint_address}", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Error registering NFT verification: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False

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
            # TODO: Implement DNS verification
            # Should check for TXT record like: privra-verify=<token>

            # Extract domain from email
            email_domain = user_email.split('@')[1] if '@' in user_email else ''

            if email_domain.lower() == domain.lower():
                # User's email domain matches
                return True, "Domain matches email"

            # Placeholder - always succeeds for development
            return True, "Domain verification placeholder"

        except Exception as e:
            print(f"Error verifying domain: {e}", file=sys.stderr)
            return False, str(e)


# Global instance
nft_verification_service = NFTVerificationService()
