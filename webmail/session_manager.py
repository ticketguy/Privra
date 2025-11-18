#!/usr/bin/env python3
"""Session Management for Privra - Track devices and activity like Gmail"""

import os
import secrets
import psycopg2
from datetime import datetime
from typing import Optional, Dict, List
from user_agents import parse

class SessionManager:
    """
    Manages user sessions across devices

    Features:
    - Track all active sessions per user
    - Record device info, IP, location, activity
    - Allow users to view all sessions
    - Allow users to revoke sessions (sign out other devices)
    """

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def create_session(self, user_email: str, user_agent: str, ip_address: str) -> str:
        """
        Create a new session when user logs in

        Args:
            user_email: User's email address
            user_agent: Browser user agent string
            ip_address: User's IP address

        Returns:
            session_token: Unique session token
        """
        # Parse user agent
        ua = parse(user_agent)

        device_type = 'Mobile' if ua.is_mobile else ('Tablet' if ua.is_tablet else 'Desktop')
        browser = f"{ua.browser.family} {ua.browser.version_string}"
        os_info = f"{ua.os.family} {ua.os.version_string}"
        device_name = f"{browser} on {os_info}"

        # Generate secure session token
        session_token = secrets.token_urlsafe(32)

        # TODO: Get location from IP (use a geolocation service)
        location = self._get_location_from_ip(ip_address)

        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user_sessions
                (user_email, session_token, device_name, device_type, browser, os, ip_address, location)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_email, session_token, device_name, device_type, browser, os_info, ip_address, location))

            conn.commit()
            cur.close()
            conn.close()

            return session_token

        except Exception as e:
            print(f"Session creation error: {e}")
            return None

    def update_session_activity(self, session_token: str):
        """Update last_activity timestamp for active session"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                UPDATE user_sessions
                SET last_activity = CURRENT_TIMESTAMP
                WHERE session_token = %s AND is_active = TRUE
            """, (session_token,))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Session update error: {e}")

    def verify_session(self, session_token: str) -> Optional[str]:
        """
        Verify session is valid and active

        Returns:
            user_email if valid, None if invalid
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT user_email, is_active
                FROM user_sessions
                WHERE session_token = %s
            """, (session_token,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result and result[1]:  # is_active = True
                # Update last activity
                self.update_session_activity(session_token)
                return result[0]

            return None

        except Exception as e:
            print(f"Session verification error: {e}")
            return None

    def get_user_sessions(self, user_email: str) -> List[Dict]:
        """
        Get all active sessions for a user

        Returns list of session dictionaries with device info
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, session_token, device_name, device_type, browser, os,
                       ip_address, location, last_activity, created_at
                FROM user_sessions
                WHERE user_email = %s AND is_active = TRUE
                ORDER BY last_activity DESC
            """, (user_email,))

            sessions = []
            for row in cur.fetchall():
                sessions.append({
                    'id': row[0],
                    'session_token': row[1],
                    'device_name': row[2],
                    'device_type': row[3],
                    'browser': row[4],
                    'os': row[5],
                    'ip_address': row[6],
                    'location': row[7],
                    'last_activity': row[8],
                    'created_at': row[9]
                })

            cur.close()
            conn.close()

            return sessions

        except Exception as e:
            print(f"Get sessions error: {e}")
            return []

    def revoke_session(self, session_token: str, user_email: str) -> bool:
        """
        Revoke a session (sign out from specific device)

        Args:
            session_token: Token to revoke
            user_email: Must match session owner (security check)

        Returns:
            True if revoked successfully
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                UPDATE user_sessions
                SET is_active = FALSE, revoked_at = CURRENT_TIMESTAMP
                WHERE session_token = %s AND user_email = %s
            """, (session_token, user_email))

            rows_affected = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()

            return rows_affected > 0

        except Exception as e:
            print(f"Session revocation error: {e}")
            return False

    def revoke_all_sessions(self, user_email: str, except_token: Optional[str] = None):
        """
        Revoke all sessions for a user (except current one)

        Useful for "Sign out all other sessions" feature
        """
        try:
            conn = self.get_db()
            cur = conn.cursor()

            if except_token:
                cur.execute("""
                    UPDATE user_sessions
                    SET is_active = FALSE, revoked_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s AND session_token != %s AND is_active = TRUE
                """, (user_email, except_token))
            else:
                cur.execute("""
                    UPDATE user_sessions
                    SET is_active = FALSE, revoked_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s AND is_active = TRUE
                """, (user_email,))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Revoke all sessions error: {e}")

    def _get_location_from_ip(self, ip_address: str) -> str:
        """
        Get location from IP address using geolocation service

        TODO: Integrate with ipapi.co or similar service
        """
        # For now, return placeholder
        # You can integrate with: https://ipapi.co/{ip}/json/
        if ip_address.startswith('127.') or ip_address == 'localhost':
            return 'Local'

        return f"Unknown ({ip_address})"


# Global instance
session_manager = SessionManager()
