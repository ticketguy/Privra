#!/usr/bin/env python3
"""
Email Folder and Label Service
Manages email organization with system folders and custom labels
"""

import os
import psycopg2
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class FolderService:
    """Email folder and label management"""

    # System folder definitions
    SYSTEM_FOLDERS = {
        'inbox': {'name': 'Inbox', 'icon': '📥', 'color': '#667eea', 'sort_order': 1},
        'important': {'name': 'Important', 'icon': '⭐', 'color': '#f59e0b', 'sort_order': 2},
        'starred': {'name': 'Starred', 'icon': '⭐', 'color': '#fbbf24', 'sort_order': 3},
        'drafts': {'name': 'Drafts', 'icon': '📝', 'color': '#6b7280', 'sort_order': 4},
        'sent': {'name': 'Sent', 'icon': '📤', 'color': '#10b981', 'sort_order': 5},
        'scheduled': {'name': 'Scheduled', 'icon': '⏰', 'color': '#3b82f6', 'sort_order': 6},
        'socials': {'name': 'Socials', 'icon': '👥', 'color': '#8b5cf6', 'sort_order': 7},
        'updates': {'name': 'Updates', 'icon': '📰', 'color': '#06b6d4', 'sort_order': 8},
        'paid_shill': {'name': 'Paid Shill', 'icon': '💰', 'color': '#ec4899', 'sort_order': 9},
        'muted': {'name': 'Muted', 'icon': '🔇', 'color': '#9ca3af', 'sort_order': 10},
        'spam': {'name': 'Spam', 'icon': '🚫', 'color': '#ef4444', 'sort_order': 11},
        'trash': {'name': 'Trash', 'icon': '🗑️', 'color': '#f87171', 'sort_order': 12},
        'archive': {'name': 'Archive', 'icon': '📦', 'color': '#64748b', 'sort_order': 13},
    }

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

    def create_default_folders(self, user_email: str) -> bool:
        """Create default system folders for a new user"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            # Insert all system folders
            for folder_id, folder_info in self.SYSTEM_FOLDERS.items():
                cur.execute("""
                    INSERT INTO email_folders
                    (user_email, folder_name, folder_type, color, icon, is_system, sort_order)
                    VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                    ON CONFLICT (user_email, folder_name) DO NOTHING
                """, (
                    user_email,
                    folder_info['name'],
                    folder_id,
                    folder_info['color'],
                    folder_info['icon'],
                    folder_info['sort_order']
                ))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error creating default folders: {e}")
            return False

    def get_folders(self, user_email: str) -> List[Dict]:
        """Get all folders for a user (system + custom)"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, folder_name, folder_type, color, icon, is_system, sort_order
                FROM email_folders
                WHERE user_email = %s
                ORDER BY sort_order, folder_name
            """, (user_email,))

            folders = []
            for row in cur.fetchall():
                folders.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'color': row[3],
                    'icon': row[4],
                    'is_system': row[5],
                    'sort_order': row[6]
                })

            cur.close()
            conn.close()
            return folders

        except Exception as e:
            print(f"Error getting folders: {e}")
            return []

    def create_custom_folder(self, user_email: str, folder_name: str, color: str = '#667eea', icon: str = '📁') -> Tuple[bool, str]:
        """Create a custom user folder/label"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            # Check if folder already exists
            cur.execute("""
                SELECT id FROM email_folders
                WHERE user_email = %s AND folder_name = %s
            """, (user_email, folder_name))

            if cur.fetchone():
                cur.close()
                conn.close()
                return False, "Folder already exists"

            # Get max sort order
            cur.execute("""
                SELECT MAX(sort_order) FROM email_folders
                WHERE user_email = %s
            """, (user_email,))
            max_sort = cur.fetchone()[0] or 0

            # Insert custom folder
            cur.execute("""
                INSERT INTO email_folders
                (user_email, folder_name, folder_type, color, icon, is_system, sort_order)
                VALUES (%s, %s, 'custom', %s, %s, FALSE, %s)
            """, (user_email, folder_name, color, icon, max_sort + 1))

            conn.commit()
            cur.close()
            conn.close()
            return True, "Folder created successfully"

        except Exception as e:
            print(f"Error creating folder: {e}")
            return False, str(e)

    def delete_custom_folder(self, user_email: str, folder_id: int) -> Tuple[bool, str]:
        """Delete a custom folder (not system folders)"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            # Check if it's a system folder
            cur.execute("""
                SELECT is_system FROM email_folders
                WHERE id = %s AND user_email = %s
            """, (folder_id, user_email))

            result = cur.fetchone()
            if not result:
                cur.close()
                conn.close()
                return False, "Folder not found"

            if result[0]:  # is_system
                cur.close()
                conn.close()
                return False, "Cannot delete system folders"

            # Delete folder
            cur.execute("""
                DELETE FROM email_folders
                WHERE id = %s AND user_email = %s
            """, (folder_id, user_email))

            # Remove labels from emails
            cur.execute("""
                DELETE FROM email_labels
                WHERE user_email = %s
                AND label_name = (
                    SELECT folder_name FROM email_folders WHERE id = %s
                )
            """, (user_email, folder_id))

            conn.commit()
            cur.close()
            conn.close()
            return True, "Folder deleted successfully"

        except Exception as e:
            print(f"Error deleting folder: {e}")
            return False, str(e)

    def add_label_to_email(self, user_email: str, message_id: str, label_name: str, ai_generated: bool = False) -> bool:
        """Add a label to an email"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO email_labels (message_id, user_email, label_name, ai_generated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (message_id, user_email, label_name) DO NOTHING
            """, (message_id, user_email, label_name, ai_generated))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error adding label: {e}")
            return False

    def remove_label_from_email(self, user_email: str, message_id: str, label_name: str) -> bool:
        """Remove a label from an email"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM email_labels
                WHERE message_id = %s AND user_email = %s AND label_name = %s
            """, (message_id, user_email, label_name))

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"Error removing label: {e}")
            return False

    def get_email_labels(self, user_email: str, message_id: str) -> List[str]:
        """Get all labels for a specific email"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT label_name FROM email_labels
                WHERE user_email = %s AND message_id = %s
            """, (user_email, message_id))

            labels = [row[0] for row in cur.fetchall()]

            cur.close()
            conn.close()
            return labels

        except Exception as e:
            print(f"Error getting email labels: {e}")
            return []

    def get_folder_email_count(self, user_email: str, folder_name: str) -> int:
        """Get count of emails in a folder"""
        try:
            conn = self._get_db()
            cur = conn.cursor()

            if folder_name == 'Inbox':
                # For inbox, count emails without labels or with inbox label
                cur.execute("""
                    SELECT COUNT(DISTINCT message_id)
                    FROM email_labels
                    WHERE user_email = %s AND label_name = 'Inbox'
                """, (user_email,))
            else:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM email_labels
                    WHERE user_email = %s AND label_name = %s
                """, (user_email, folder_name))

            count = cur.fetchone()[0] or 0

            cur.close()
            conn.close()
            return count

        except Exception as e:
            print(f"Error getting folder count: {e}")
            return 0


# Global service instance
folder_service = FolderService()
