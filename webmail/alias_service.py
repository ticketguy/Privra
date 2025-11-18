#!/usr/bin/env python3
"""
Email Alias Service - Dynamic Shield Aliasing (Priority 1)

Generates unlimited email aliases for privacy protection.
Examples: netflix.user@privra.xyz, amazon.user@privra.xyz
"""

import secrets
import string
import psycopg2
import os
from typing import Optional
from datetime import datetime


class AliasService:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'privra-dockyard'),
            'database': 'privra',
            'user': 'privra_user',
            'password': os.getenv('POSTGRES_PASSWORD', 'privra_secure_2024')
        }

    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def generate_alias(self, user_email: str, service_name: str,
                       custom_prefix: Optional[str] = None,
                       description: Optional[str] = None) -> dict:
        """
        Generate a new email alias.

        Args:
            user_email: User's primary email
            service_name: Name of service (e.g., "Netflix")
            custom_prefix: Optional custom prefix (default: auto-generated)
            description: Optional notes about the alias

        Returns:
            {
                "id": 123,
                "alias": "netflix.user@privra.xyz",
                "service_name": "Netflix",
                "created_at": "2025-11-18T..."
            }
        """
        # Extract username from user_email
        username = user_email.split('@')[0]

        # Generate alias prefix
        if custom_prefix:
            # Use custom prefix (sanitize it)
            prefix = self._sanitize_prefix(custom_prefix)
        else:
            # Auto-generate: servicename.random
            safe_service = self._sanitize_prefix(service_name)[:20]
            random_suffix = ''.join(secrets.choice(string.ascii_lowercase)
                                   for _ in range(4))
            prefix = f"{safe_service}.{random_suffix}"

        # Build full alias
        alias = f"{prefix}.{username}@privra.xyz"

        # Check uniqueness (handle collision)
        if self._alias_exists(alias):
            # Add extra random suffix
            collision_suffix = secrets.token_hex(3)
            alias = f"{prefix}.{collision_suffix}.{username}@privra.xyz"

        # Insert into database
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO email_aliases (user_email, alias, service_name, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id, alias, created_at
            """, (user_email, alias, service_name, description))

            result = cur.fetchone()
            conn.commit()

            return {
                "id": result[0],
                "alias": result[1],
                "service_name": service_name,
                "created_at": result[2].isoformat()
            }

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create alias: {str(e)}")
        finally:
            cur.close()
            conn.close()

    def list_aliases(self, user_email: str, include_burned: bool = False) -> list:
        """
        Get all aliases for a user.

        Args:
            user_email: User's email
            include_burned: Whether to include burned aliases

        Returns:
            List of alias dictionaries
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            query = """
                SELECT id, alias, service_name, description, created_at,
                       last_used, email_count, is_active, burned_at
                FROM email_aliases
                WHERE user_email = %s
            """

            if not include_burned:
                query += " AND burned_at IS NULL"

            query += " ORDER BY created_at DESC"

            cur.execute(query, (user_email,))
            rows = cur.fetchall()

            return [
                {
                    "id": row[0],
                    "alias": row[1],
                    "service_name": row[2],
                    "description": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "last_used": row[5].isoformat() if row[5] else None,
                    "email_count": row[6],
                    "is_active": row[7],
                    "burned_at": row[8].isoformat() if row[8] else None
                }
                for row in rows
            ]

        finally:
            cur.close()
            conn.close()

    def get_alias(self, alias_id: int, user_email: str) -> Optional[dict]:
        """Get a specific alias by ID"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, alias, service_name, description, created_at,
                       last_used, email_count, is_active, burned_at
                FROM email_aliases
                WHERE id = %s AND user_email = %s
            """, (alias_id, user_email))

            row = cur.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "alias": row[1],
                "service_name": row[2],
                "description": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "last_used": row[5].isoformat() if row[5] else None,
                "email_count": row[6],
                "is_active": row[7],
                "burned_at": row[8].isoformat() if row[8] else None
            }

        finally:
            cur.close()
            conn.close()

    def burn_alias(self, alias_id: int, user_email: str) -> bool:
        """
        Burn an alias (irreversible). Sender gets 550 error.

        Args:
            alias_id: Alias ID to burn
            user_email: User's email (for authorization)

        Returns:
            True if burned successfully, False if not found/unauthorized
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            # Verify ownership and burn
            cur.execute("""
                UPDATE email_aliases
                SET is_active = FALSE,
                    burned_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_email = %s AND burned_at IS NULL
                RETURNING alias
            """, (alias_id, user_email))

            result = cur.fetchone()

            if result:
                conn.commit()
                burned_alias = result[0]
                print(f"🔥 Burned alias: {burned_alias}")
                return True
            else:
                return False

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to burn alias: {str(e)}")
        finally:
            cur.close()
            conn.close()

    def update_alias_stats(self, alias: str):
        """
        Update alias statistics when email arrives.
        Called by Postfix delivery hook.

        Args:
            alias: The alias that received email
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE email_aliases
                SET last_used = CURRENT_TIMESTAMP,
                    email_count = email_count + 1
                WHERE alias = %s AND is_active = TRUE
            """, (alias,))

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Warning: Failed to update alias stats for {alias}: {str(e)}")
        finally:
            cur.close()
            conn.close()

    def resolve_alias(self, alias: str) -> Optional[str]:
        """
        Resolve alias to actual user email.
        Used by Postfix for email routing.

        Args:
            alias: Email alias (e.g., netflix.user@privra.xyz)

        Returns:
            User's actual email, or None if alias not found/burned
        """
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT user_email
                FROM email_aliases
                WHERE alias = %s AND is_active = TRUE
                LIMIT 1
            """, (alias,))

            result = cur.fetchone()

            if result:
                # Update stats asynchronously
                try:
                    self.update_alias_stats(alias)
                except:
                    pass  # Don't block email delivery on stats update

                return result[0]
            else:
                return None

        finally:
            cur.close()
            conn.close()

    def _alias_exists(self, alias: str) -> bool:
        """Check if alias already exists"""
        conn = self._get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT 1 FROM email_aliases WHERE alias = %s
            """, (alias,))

            return cur.fetchone() is not None

        finally:
            cur.close()
            conn.close()

    def _sanitize_prefix(self, text: str) -> str:
        """
        Sanitize prefix for email alias.
        Removes special characters, converts to lowercase.
        """
        # Convert to lowercase
        text = text.lower()

        # Replace spaces and special chars with hyphens
        text = text.replace(' ', '-')

        # Keep only alphanumeric and hyphens
        sanitized = ''.join(c for c in text if c.isalnum() or c == '-')

        # Remove consecutive hyphens
        while '--' in sanitized:
            sanitized = sanitized.replace('--', '-')

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')

        # Ensure not empty
        if not sanitized:
            sanitized = 'alias'

        return sanitized


# Global instance
alias_service = AliasService()
