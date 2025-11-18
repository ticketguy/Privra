#!/usr/bin/env python3
"""PortID Client-Side Encryption Service for Privra"""

import os
from portid_sdk import PortID, PortIDError
from typing import Optional, Dict, Any

class PortIDService:
    """
    PortID wrapper for client-side data encryption

    PortID is NOT an authentication service. It's a client-side encryption library
    that stores encrypted user data locally and syncs to YOUR server (not a PortID service).

    Flow:
    1. sign_up() - Creates encrypted local storage, returns recovery_key
    2. sign_in() - Decrypts local data with password
    3. backup() - Encrypts and sends data to YOUR sync server (stored in DB)
    4. restore() - Fetches encrypted data from YOUR server, decrypts it
    """

    def __init__(self):
        """Initialize PortID SDK with YOUR sync server URL"""
        self.app_id = os.getenv('PORTID_APP_ID', 'privra-mail-v1')
        # This should point to YOUR API endpoint that handles encrypted backups
        self.api_url = os.getenv('PORTID_API_URL', 'http://localhost:5000/api/portid')

        try:
            self.sdk = PortID(
                app_id=self.app_id,
                api_base_url=self.api_url
            )
        except Exception as e:
            print(f"Warning: PortID SDK initialization failed: {e}")
            print("PortID encryption will be disabled")
            self.sdk = None

    def is_enabled(self) -> bool:
        """Check if PortID SDK is initialized"""
        return self.sdk is not None

    def sign_up(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Create encrypted local storage for user

        This creates an encrypted IndexedDB/local storage with the user's data.
        The data is encrypted with the password on the client side.

        Returns:
            {
                'recovery_key': str  # Critical! User must save this
            }
        """
        if not self.is_enabled():
            return None

        try:
            credentials = self.sdk.sign_up(username, password)
            return {
                'recovery_key': credentials.get('recovery_key'),
                'username': username
            }
        except PortIDError as e:
            print(f"PortID signup error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during PortID signup: {e}")
            return None

    def sign_in(self, username: str, password: str) -> bool:
        """
        Decrypt local storage with password

        This doesn't call a server - it just decrypts the local encrypted data.
        Returns True if password is correct and data is decrypted.

        Returns:
            bool - True if sign-in successful, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            return self.sdk.sign_in(username, password)
        except PortIDError as e:
            print(f"PortID sign-in error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during PortID sign-in: {e}")
            return False

    def backup(self, data: Dict[str, Any]) -> bool:
        """
        Encrypt and send data to YOUR sync server

        The SDK encrypts the data client-side, then POSTs it to api_base_url.
        Your server should store this encrypted blob in the database.

        Args:
            data: Dictionary of data to encrypt and backup

        Returns:
            bool - True if backup successful
        """
        if not self.is_enabled():
            return False

        try:
            self.sdk.backup(data)
            return True
        except PortIDError as e:
            print(f"PortID backup error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during PortID backup: {e}")
            return False

    def restore(self, recovery_key: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Fetch encrypted data from YOUR server and decrypt it

        The SDK fetches the encrypted blob from api_base_url, then decrypts it
        locally using the recovery_key and password.

        Args:
            recovery_key: The recovery key from sign_up
            password: User's password

        Returns:
            Dict with decrypted user data, or None if failed
        """
        if not self.is_enabled():
            return None

        try:
            restored_data = self.sdk.restore(recovery_key, password)
            return restored_data
        except PortIDError as e:
            print(f"PortID restore error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during PortID restore: {e}")
            return None


# Global PortID service instance
portid_service = PortIDService()
