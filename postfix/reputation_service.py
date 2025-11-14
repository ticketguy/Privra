#!/usr/bin/env python3
"""
Reputation Scoring Service
Tracks and updates user reputation based on email behavior
Syncs reputation to Solana NFT metadata
"""

import os
import sys
import psycopg2
from datetime import datetime
from typing import Dict, Optional, Tuple

class ReputationService:
    """Manages user reputation scoring"""

    # Reputation levels and thresholds
    REPUTATION_LEVELS = {
        'new': (0, 100),
        'trusted': (100, 500),
        'verified': (500, 1000),
        'elite': (1000, 5000),
        'legendary': (5000, float('inf'))
    }

    # Score adjustments for different events
    SCORE_ADJUSTMENTS = {
        # Positive events
        'email_sent': 1,
        'email_received': 1,
        'payment_made': 10,
        'domain_verified': 100,
        'nft_verified': 50,
        'positive_interaction': 5,
        'whitelist_added': 3,

        # Negative events
        'spam_report': -20,
        'payment_failed': -5,
        'blacklist_added': -10,
        'negative_interaction': -3,
    }

    def __init__(self):
        """Initialize reputation service"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_reputation_level(self, score: int) -> str:
        """Get reputation level based on score"""
        for level, (min_score, max_score) in self.REPUTATION_LEVELS.items():
            if min_score <= score < max_score:
                return level
        return 'new'

    def initialize_reputation(self, user_email: str):
        """Initialize reputation for new user"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO reputation_scores (user_email)
                VALUES (%s)
                ON CONFLICT (user_email) DO NOTHING
            """, (user_email,))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Error initializing reputation: {e}", file=sys.stderr)

    def record_event(
        self,
        user_email: str,
        event_type: str,
        event_category: str = 'general',
        description: str = None,
        metadata: Dict = None
    ) -> bool:
        """
        Record reputation event and update score

        Args:
            user_email: User's email address
            event_type: Type of event (e.g., 'email_sent', 'spam_report')
            event_category: Category of event
            description: Event description
            metadata: Additional metadata

        Returns:
            bool: Success status
        """
        try:
            # Get score adjustment for this event type
            score_change = self.SCORE_ADJUSTMENTS.get(event_type, 0)

            conn = self.get_db()
            cur = conn.cursor()

            # Ensure reputation record exists
            self.initialize_reputation(user_email)

            # Record the event
            cur.execute("""
                INSERT INTO reputation_events
                (user_email, event_type, event_category, score_change, description, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_email, event_type, event_category, score_change, description,
                  psycopg2.extras.Json(metadata) if metadata else None))

            # Update reputation scores
            self._update_scores(cur, user_email, event_type, score_change)

            conn.commit()
            cur.close()
            conn.close()

            print(f"Recorded reputation event: {user_email} - {event_type} ({score_change:+d})", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Error recording reputation event: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False

    def _update_scores(self, cur, user_email: str, event_type: str, score_change: int):
        """Update reputation scores based on event"""

        # Determine which score categories to update
        updates = []

        if event_type in ['email_sent', 'email_received']:
            updates.append(('email_score', score_change))
            if event_type == 'email_sent':
                updates.append(('emails_sent', 1))
            else:
                updates.append(('emails_received', 1))

        elif event_type in ['domain_verified', 'nft_verified']:
            updates.append(('verification_score', score_change))

        elif event_type in ['payment_made', 'payment_failed']:
            updates.append(('payment_score', abs(score_change)))

        elif event_type in ['spam_report']:
            updates.append(('spam_reports', 1))

        elif event_type in ['positive_interaction', 'whitelist_added']:
            updates.append(('positive_interactions', 1))
            updates.append(('trust_score', score_change))

        elif event_type in ['negative_interaction', 'blacklist_added']:
            updates.append(('negative_interactions', 1))
            updates.append(('trust_score', score_change))

        # Update total score
        updates.append(('total_score', score_change))

        # Build UPDATE query
        set_clauses = []
        for field, change in updates:
            if field == 'total_score' or field.endswith('_score'):
                # For scores, add the change
                set_clauses.append(f"{field} = GREATEST(0, {field} + {change})")
            else:
                # For counters, add the change
                set_clauses.append(f"{field} = {field} + {change}")

        if set_clauses:
            query = f"""
                UPDATE reputation_scores
                SET {', '.join(set_clauses)},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_email = %s
                RETURNING total_score
            """

            cur.execute(query, (user_email,))
            result = cur.fetchone()

            if result:
                new_score = result[0]
                new_level = self.get_reputation_level(new_score)

                # Update reputation level
                cur.execute("""
                    UPDATE reputation_scores
                    SET reputation_level = %s
                    WHERE user_email = %s
                """, (new_level, user_email))

    def get_reputation(self, user_email: str) -> Optional[Dict]:
        """Get user's reputation data"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT total_score, email_score, verification_score, payment_score,
                       trust_score, spam_reports, positive_interactions, negative_interactions,
                       emails_sent, emails_received, reputation_level, nft_sync_status,
                       last_nft_update
                FROM reputation_scores
                WHERE user_email = %s
            """, (user_email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                return {
                    'total_score': result[0],
                    'email_score': result[1],
                    'verification_score': result[2],
                    'payment_score': result[3],
                    'trust_score': result[4],
                    'spam_reports': result[5],
                    'positive_interactions': result[6],
                    'negative_interactions': result[7],
                    'emails_sent': result[8],
                    'emails_received': result[9],
                    'reputation_level': result[10],
                    'nft_sync_status': result[11],
                    'last_nft_update': result[12]
                }

            return None

        except Exception as e:
            print(f"Error getting reputation: {e}", file=sys.stderr)
            return None

    def calculate_trust_percentage(self, user_email: str) -> int:
        """Calculate trust percentage (0-100) based on reputation"""
        reputation = self.get_reputation(user_email)
        if not reputation:
            return 0

        total_score = reputation['total_score']
        spam_reports = reputation['spam_reports']

        # Base trust from total score (max 70%)
        base_trust = min(70, (total_score / 1000) * 70)

        # Verification bonus (up to 20%)
        verification_bonus = min(20, (reputation['verification_score'] / 100) * 20)

        # Spam penalty (subtract 10% per spam report, max -30%)
        spam_penalty = min(30, spam_reports * 10)

        # Interaction ratio bonus (up to 10%)
        total_interactions = reputation['positive_interactions'] + reputation['negative_interactions']
        if total_interactions > 0:
            positive_ratio = reputation['positive_interactions'] / total_interactions
            interaction_bonus = positive_ratio * 10
        else:
            interaction_bonus = 0

        trust = int(base_trust + verification_bonus + interaction_bonus - spam_penalty)
        return max(0, min(100, trust))


# Global instance
reputation_service = ReputationService()
