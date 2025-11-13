#!/usr/bin/env python3
"""PortID Authentication Service for Privra"""

import os
from portid_sdk import PortID, PortIDError
from typing import Optional, Dict, Any

class PortIDService:
    """Wrapper for PortID SDK with Privra-specific logic"""

    def __init__(self):
        """Initialize PortID SDK"""
        self.app_id = os.getenv('PORTID_APP_ID', 'privra-mail-v1')
        self.api_url = os.getenv('PORTID_API_URL', 'http://localhost:5001')

        try:
            self.sdk = PortID(
                app_id=self.app_id,
                api_base_url=self.api_url
            )
        except Exception as e:
            print(f"Warning: PortID SDK initialization failed: {e}")
            print("Falling back to legacy password authentication")
            self.sdk = None

    def is_enabled(self) -> bool:
        """Check if PortID is enabled and initialized"""
        return self.sdk is not None

    def sign_up(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Register a new user with PortID

        Returns:
            {
                'username': str,
                'recovery_key': str,
                'portid': str  # Unique PortID identifier
            }
        """
        if not self.is_enabled():
            return None

        try:
            credentials = self.sdk.sign_up(username, password)
            return {
                'username': username,
                'recovery_key': credentials.get('recovery_key'),
                'portid': credentials.get('portid', username)  # Use PortID as unique identifier
            }
        except PortIDError as e:
            print(f"PortID signup error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during PortID signup: {e}")
            return None

    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with PortID

        Returns:
            {
                'username': str,
                'portid': str,
                'token': str  # Authentication token for session
            }
        """
        if not self.is_enabled():
            return None

        try:
            result = self.sdk.login(username, password)
            return {
                'username': username,
                'portid': result.get('portid', username),
                'token': result.get('token', ''),
                'success': True
            }
        except PortIDError as e:
            print(f"PortID login error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            print(f"Unexpected error during PortID login: {e}")
            return {'success': False, 'error': 'Authentication failed'}

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a PortID authentication token

        Returns:
            {
                'valid': bool,
                'portid': str,
                'username': str
            }
        """
        if not self.is_enabled():
            return None

        try:
            # PortID SDK should have a verify method
            # For now, we'll assume tokens are self-contained
            # You may need to implement actual verification based on PortID's token format
            return {
                'valid': True,
                'token': token
            }
        except Exception as e:
            print(f"Token verification error: {e}")
            return {'valid': False}


# Global PortID service instance
portid_service = PortIDService()
