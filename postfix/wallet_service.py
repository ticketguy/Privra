#!/usr/bin/env python3
"""
Multi-Chain Wallet Service
Generates and manages wallets for multiple blockchain networks
Similar to OKX wallet - one seed, multiple chains
"""

import os
import psycopg2
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import scrypt
import hashlib

# Solana
from solders.keypair import Keypair as SolanaKeypair
from solders.pubkey import Pubkey as SolanaPubkey

# EVM (Ethereum, Base, Polygon, etc.)
from eth_account import Account as EVMAccount
from eth_keys import keys

class WalletService:
    """Multi-chain wallet generation and management"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

    def _get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def _encrypt_private_key(self, private_key: str, user_password: str) -> Tuple[str, str]:
        """
        Encrypt private key with user password using AES-256-GCM
        Returns: (encrypted_data, salt)
        """
        salt = get_random_bytes(32)
        key = scrypt(user_password.encode(), salt, 32, N=2**14, r=8, p=1)

        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(private_key.encode())

        # Combine nonce + tag + ciphertext
        encrypted_data = base64.b64encode(cipher.nonce + tag + ciphertext).decode()
        salt_b64 = base64.b64encode(salt).decode()

        return encrypted_data, salt_b64

    def _decrypt_private_key(self, encrypted_data: str, salt_b64: str, user_password: str) -> str:
        """Decrypt private key with user password"""
        try:
            salt = base64.b64decode(salt_b64)
            key = scrypt(user_password.encode(), salt, 32, N=2**14, r=8, p=1)

            encrypted_bytes = base64.b64decode(encrypted_data)
            nonce = encrypted_bytes[:16]
            tag = encrypted_bytes[16:32]
            ciphertext = encrypted_bytes[32:]

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)

            return plaintext.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def generate_wallets(self, user_email: str, user_password: str) -> Dict:
        """
        Generate multi-chain wallets for a user
        Returns wallet addresses for all supported chains
        """

        # Generate Solana wallet
        solana_keypair = SolanaKeypair()
        solana_private_key = base64.b64encode(bytes(solana_keypair)).decode()
        solana_address = str(solana_keypair.pubkey())

        # Generate EVM wallet (works for Ethereum, Base, Polygon, Arbitrum, etc.)
        evm_account = EVMAccount.create()
        evm_private_key = evm_account.key.hex()
        evm_address = evm_account.address

        # Encrypt private keys
        solana_encrypted, solana_salt = self._encrypt_private_key(solana_private_key, user_password)
        evm_encrypted, evm_salt = self._encrypt_private_key(evm_private_key, user_password)

        # Store in database
        try:
            conn = self._get_db()
            cur = conn.cursor()

            # Create or update wallet entry
            cur.execute("""
                INSERT INTO user_wallets_generated (
                    user_email,
                    solana_address,
                    solana_private_key_encrypted,
                    solana_salt,
                    evm_address,
                    evm_private_key_encrypted,
                    evm_salt,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_email)
                DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_email,
                solana_address,
                solana_encrypted,
                solana_salt,
                evm_address,
                evm_encrypted,
                evm_salt
            ))

            conn.commit()
            cur.close()
            conn.close()

            return {
                'success': True,
                'wallets': {
                    'solana': {
                        'address': solana_address,
                        'network': 'Solana Mainnet'
                    },
                    'ethereum': {
                        'address': evm_address,
                        'network': 'Ethereum Mainnet'
                    },
                    'base': {
                        'address': evm_address,
                        'network': 'Base Mainnet'
                    },
                    'polygon': {
                        'address': evm_address,
                        'network': 'Polygon Mainnet'
                    },
                    'arbitrum': {
                        'address': evm_address,
                        'network': 'Arbitrum One'
                    },
                    'optimism': {
                        'address': evm_address,
                        'network': 'Optimism Mainnet'
                    }
                }
            }

        except Exception as e:
            print(f"Error generating wallets: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_wallets(self, user_email: str) -> Dict:
        """Get wallet addresses for a user"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT solana_address, evm_address, created_at
                FROM user_wallets_generated
                WHERE user_email = %s
            """, (user_email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return {'success': False, 'error': 'No wallets found'}

            solana_addr, evm_addr, created_at = result

            return {
                'success': True,
                'wallets': {
                    'solana': {
                        'address': solana_addr,
                        'network': 'Solana Mainnet',
                        'explorer': f'https://solscan.io/account/{solana_addr}'
                    },
                    'ethereum': {
                        'address': evm_addr,
                        'network': 'Ethereum Mainnet',
                        'explorer': f'https://etherscan.io/address/{evm_addr}'
                    },
                    'base': {
                        'address': evm_addr,
                        'network': 'Base Mainnet',
                        'explorer': f'https://basescan.org/address/{evm_addr}'
                    },
                    'polygon': {
                        'address': evm_addr,
                        'network': 'Polygon Mainnet',
                        'explorer': f'https://polygonscan.com/address/{evm_addr}'
                    },
                    'arbitrum': {
                        'address': evm_addr,
                        'network': 'Arbitrum One',
                        'explorer': f'https://arbiscan.io/address/{evm_addr}'
                    },
                    'optimism': {
                        'address': evm_addr,
                        'network': 'Optimism Mainnet',
                        'explorer': f'https://optimistic.etherscan.io/address/{evm_addr}'
                    }
                },
                'created_at': created_at.isoformat() if created_at else None
            }

        except Exception as e:
            print(f"Error getting wallets: {e}")
            return {'success': False, 'error': str(e)}

    def reveal_private_key(self, user_email: str, user_password: str, chain: str) -> Dict:
        """
        Reveal private key for a specific chain
        Requires user password for decryption
        """
        try:
            conn = self._get_db()
            cur = conn.cursor()

            if chain.lower() == 'solana':
                cur.execute("""
                    SELECT solana_private_key_encrypted, solana_salt, solana_address
                    FROM user_wallets_generated
                    WHERE user_email = %s
                """, (user_email,))
            else:  # EVM chains (ethereum, base, polygon, etc.)
                cur.execute("""
                    SELECT evm_private_key_encrypted, evm_salt, evm_address
                    FROM user_wallets_generated
                    WHERE user_email = %s
                """, (user_email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if not result:
                return {'success': False, 'error': 'Wallet not found'}

            encrypted_key, salt, address = result

            # Decrypt private key
            private_key = self._decrypt_private_key(encrypted_key, salt, user_password)

            if not private_key:
                return {'success': False, 'error': 'Invalid password'}

            return {
                'success': True,
                'chain': chain,
                'address': address,
                'private_key': private_key,
                'warning': '⚠️ NEVER share your private key with anyone!'
            }

        except Exception as e:
            print(f"Error revealing private key: {e}")
            return {'success': False, 'error': str(e)}

    def export_wallet(self, user_email: str, user_password: str, format: str = 'json') -> Dict:
        """
        Export wallet data
        Formats: json, mnemonic (future)
        """
        try:
            wallets = self.get_wallets(user_email)

            if not wallets['success']:
                return wallets

            # Get private keys
            solana_pk = self.reveal_private_key(user_email, user_password, 'solana')
            evm_pk = self.reveal_private_key(user_email, user_password, 'ethereum')

            if not solana_pk['success'] or not evm_pk['success']:
                return {'success': False, 'error': 'Invalid password'}

            export_data = {
                'exported_at': datetime.now().isoformat(),
                'user_email': user_email,
                'wallets': {
                    'solana': {
                        'address': solana_pk['address'],
                        'private_key': solana_pk['private_key'],
                        'network': 'Solana Mainnet'
                    },
                    'evm': {
                        'address': evm_pk['address'],
                        'private_key': evm_pk['private_key'],
                        'networks': ['Ethereum', 'Base', 'Polygon', 'Arbitrum', 'Optimism']
                    }
                },
                'warning': '⚠️ Keep this file secure! Anyone with these private keys can access your funds.'
            }

            return {
                'success': True,
                'data': export_data
            }

        except Exception as e:
            print(f"Error exporting wallet: {e}")
            return {'success': False, 'error': str(e)}


# Global service instance
wallet_service = WalletService()
