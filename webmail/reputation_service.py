#!/usr/bin/env python3
"""
Reputation & Automated Penalty System
Privacy-preserving abuse prevention using metadata and user reports
"""

import os
import sys
import json
import psycopg2
import redis
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class ReputationService:
    """
    Trust Score System with Tiered Penalties

    Tiers:
    - Normal (80-100): Full access
    - Warning (50-79): Warning sent, full access
    - Throttle (20-49): 10 emails/hour limit
    - Walled (1-19): Internal-only mode
    - Frozen (0): Account locked
    """

    # Tier thresholds
    TIERS = {
        'normal': (80, 100),
        'warning': (50, 79),
        'throttle': (20, 49),
        'walled': (1, 19),
        'frozen': (0, 0)
    }

    # Score penalties (negative values)
    PENALTIES = {
        'user_report': -5,       # Weighted by reporter's score
        'bounce_rate_high': -10, # >10% bounce rate in 24h
        'spam_trap_hit': -100,   # Instant freeze
        'velocity_spike': -15,   # Sudden spike in sending
    }

    # Rate limits (emails per hour)
    RATE_LIMITS = {
        'normal': None,      # Unlimited
        'warning': 100,
        'throttle': 10,
        'walled': 5,
        'frozen': 0
    }

    HEALING_RATE = 5  # +5 points/day for good behavior

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'database': os.getenv('DB_NAME', 'privramail'),
            'user': os.getenv('DB_USER', 'privramail'),
            'password': os.getenv('DB_PASSWORD')
        }

        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=1,
                decode_responses=True,
                socket_connect_timeout=2
            )
            self.redis_client.ping()
        except:
            print("Warning: Redis not available, rate limiting disabled", file=sys.stderr)
            self.redis_client = None

    def get_db(self):
        return psycopg2.connect(**self.db_config)

    def get_user_reputation(self, user_email: str) -> Dict:
        """Get user's current reputation"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                SELECT current_score, tier, is_frozen, last_violation_at
                FROM user_reputation
                WHERE user_email = %s
            """, (user_email,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                return {
                    'email': user_email,
                    'score': result[0],
                    'tier': result[1],
                    'is_frozen': result[2],
                    'last_violation': result[3],
                    'rate_limit': self.RATE_LIMITS.get(result[1])
                }
            else:
                # Create default
                self._create_reputation(user_email)
                return {
                    'email': user_email,
                    'score': 100,
                    'tier': 'normal',
                    'is_frozen': False,
                    'last_violation': None,
                    'rate_limit': None
                }
        except Exception as e:
            print(f"Error getting reputation: {e}", file=sys.stderr)
            return {'email': user_email, 'score': 100, 'tier': 'normal', 'is_frozen': False, 'rate_limit': None}

    def _create_reputation(self, user_email: str):
        """Create default reputation"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_reputation (user_email, current_score, tier)
                VALUES (%s, 100, 'normal')
                ON CONFLICT (user_email) DO NOTHING
            """, (user_email,))
            conn.commit()
            cur.close()
            conn.close()
        except:
            pass

    def update_score(self, user_email: str, score_change: int, reason: str, metadata: Dict = None) -> Dict:
        """Update reputation score and tier"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("SELECT current_score, tier FROM user_reputation WHERE user_email = %s", (user_email,))
            result = cur.fetchone()

            if not result:
                self._create_reputation(user_email)
                result = (100, 'normal')

            old_score, old_tier = result
            new_score = max(0, min(100, old_score + score_change))
            new_tier = self._calculate_tier(new_score)
            is_frozen = (new_tier == 'frozen')

            cur.execute("""
                UPDATE user_reputation
                SET current_score = %s, tier = %s, is_frozen = %s,
                    last_violation_at = CASE WHEN %s < 0 THEN NOW() ELSE last_violation_at END
                WHERE user_email = %s
            """, (new_score, new_tier, is_frozen, score_change, user_email))

            cur.execute("""
                INSERT INTO reputation_events
                (user_email, event_type, score_change, old_score, new_score, old_tier, new_tier, reason, metadata)
                VALUES (%s, 'score_update', %s, %s, %s, %s, %s, %s, %s)
            """, (user_email, score_change, old_score, new_score, old_tier, new_tier, reason, json.dumps(metadata or {})))

            conn.commit()
            cur.close()
            conn.close()

            # Send notification if tier changed
            if old_tier != new_tier:
                self._notify_tier_change(user_email, new_tier, new_score)

            return {'old_score': old_score, 'new_score': new_score, 'old_tier': old_tier, 'new_tier': new_tier}
        except Exception as e:
            print(f"Error updating score: {e}", file=sys.stderr)
            return {}

    def _calculate_tier(self, score: int) -> str:
        """Calculate tier based on score"""
        for tier, (min_s, max_s) in self.TIERS.items():
            if min_s <= score <= max_s:
                return tier
        return 'frozen'

    def process_user_report(self, reporter_email: str, reported_email: str, reason: str, details: str = None) -> Dict:
        """Process abuse report with weighted impact based on reporter's reputation"""
        try:
            # Get reporter's reputation
            reporter_rep = self.get_user_reputation(reporter_email)
            reporter_score = reporter_rep['score']

            # Weighted penalty: reporter with score 100 = full penalty, score 50 = half penalty
            impact_multiplier = reporter_score / 100.0
            base_penalty = self.PENALTIES['user_report']
            actual_penalty = int(base_penalty * impact_multiplier)

            # Record report
            conn = self.get_db()
            cur = conn.cursor()

            # Check for duplicate report today
            cur.execute("""
                SELECT id FROM abuse_reports
                WHERE reporter_email = %s AND reported_email = %s AND created_at::DATE = CURRENT_DATE
            """, (reporter_email, reported_email))

            if cur.fetchone():
                cur.close()
                conn.close()
                return {'success': False, 'error': 'Already reported today'}

            cur.execute("""
                INSERT INTO abuse_reports
                (reporter_email, reported_email, reporter_score, impact_multiplier, score_penalty, reason, details, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'processed')
            """, (reporter_email, reported_email, reporter_score, impact_multiplier, actual_penalty, reason, details))

            conn.commit()
            cur.close()
            conn.close()

            # Apply penalty
            result = self.update_score(reported_email, actual_penalty, f'User report: {reason}',
                                       {'reporter': reporter_email, 'impact': impact_multiplier})

            return {'success': True, 'penalty': actual_penalty, 'impact_multiplier': impact_multiplier, 'result': result}
        except Exception as e:
            print(f"Error processing report: {e}", file=sys.stderr)
            return {'success': False, 'error': str(e)}

    def check_spam_trap(self, sender_email: str, recipient_email: str) -> bool:
        """Check if recipient is spam trap - instant freeze if hit"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("SELECT id FROM spam_traps WHERE trap_email = %s AND is_active = TRUE", (recipient_email,))
            if cur.fetchone():
                cur.execute("INSERT INTO spam_trap_hits (user_email, trap_address) VALUES (%s, %s)",
                           (sender_email, recipient_email))
                conn.commit()
                cur.close()
                conn.close()

                # Instant freeze
                self.update_score(sender_email, self.PENALTIES['spam_trap_hit'], 'Spam trap hit',
                                 {'trap': recipient_email})
                return True

            cur.close()
            conn.close()
            return False
        except:
            return False

    def check_velocity(self, user_email: str) -> Tuple[bool, int]:
        """Check sending rate limit - returns (allowed, current_count)"""
        if not self.redis_client:
            return True, 0

        try:
            rep = self.get_user_reputation(user_email)
            rate_limit = self.RATE_LIMITS.get(rep['tier'])

            if rate_limit is None:
                return True, 0

            key = f"velocity:{user_email}:hour"
            count = self.redis_client.get(key)

            if count is None:
                self.redis_client.setex(key, 3600, 1)
                return True, 1
            else:
                count = int(count)
                if count >= rate_limit:
                    return False, count
                else:
                    self.redis_client.incr(key)
                    return True, count + 1
        except:
            return True, 0

    def can_send_external(self, user_email: str) -> bool:
        """Check if user can send to external addresses (False for walled/frozen tiers)"""
        rep = self.get_user_reputation(user_email)
        return rep['tier'] not in ['walled', 'frozen']

    def can_send_email(self, user_email: str) -> Tuple[bool, str]:
        """Check if user can send email - returns (allowed, reason)"""
        rep = self.get_user_reputation(user_email)

        if rep['is_frozen'] or rep['tier'] == 'frozen':
            return False, 'Account frozen due to policy violations'

        can_send, count = self.check_velocity(user_email)
        if not can_send:
            return False, f'Rate limit exceeded ({count}/{rep["rate_limit"]}/hour)'

        return True, 'OK'

    def heal_scores(self) -> int:
        """Heal scores for users with good behavior (run daily via cron)"""
        try:
            conn = self.get_db()
            cur = conn.cursor()

            cur.execute("""
                UPDATE user_reputation
                SET current_score = LEAST(100, current_score + %s),
                    tier = CASE
                        WHEN LEAST(100, current_score + %s) >= 80 THEN 'normal'
                        WHEN LEAST(100, current_score + %s) >= 50 THEN 'warning'
                        WHEN LEAST(100, current_score + %s) >= 20 THEN 'throttle'
                        WHEN LEAST(100, current_score + %s) >= 1 THEN 'walled'
                        ELSE 'frozen'
                    END,
                    is_frozen = CASE WHEN LEAST(100, current_score + %s) > 0 THEN FALSE ELSE is_frozen END
                WHERE (last_violation_at IS NULL OR last_violation_at < NOW() - INTERVAL '24 hours')
                  AND current_score < 100
                  AND is_frozen = FALSE
                RETURNING user_email
            """, (self.HEALING_RATE,) * 6)

            healed = cur.fetchall()
            conn.commit()
            cur.close()
            conn.close()

            return len(healed)
        except Exception as e:
            print(f"Error healing scores: {e}", file=sys.stderr)
            return 0

    def _notify_tier_change(self, user_email: str, new_tier: str, score: int):
        """Notify user of tier change (implement email sending)"""
        print(f"NOTIFICATION: {user_email} moved to tier '{new_tier}' (score: {score})", file=sys.stderr)
        # TODO: Implement actual email notification


# Global instance
reputation_service = ReputationService()


if __name__ == '__main__':
    # CLI for testing
    import argparse
    parser = argparse.ArgumentParser(description='Reputation Service CLI')
    parser.add_argument('command', choices=['check', 'report', 'heal', 'stats'])
    parser.add_argument('--user', help='User email')
    parser.add_argument('--reporter', help='Reporter email')
    parser.add_argument('--reported', help='Reported user email')
    parser.add_argument('--reason', help='Report reason')

    args = parser.parse_args()

    if args.command == 'check':
        rep = reputation_service.get_user_reputation(args.user or 'test@example.com')
        print(json.dumps(rep, indent=2, default=str))

    elif args.command == 'report':
        result = reputation_service.process_user_report(
            args.reporter or 'reporter@example.com',
            args.reported or 'spammer@example.com',
            args.reason or 'spam'
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.command == 'heal':
        count = reputation_service.heal_scores()
        print(f"Healed {count} users")

    elif args.command == 'stats':
        conn = reputation_service.get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT tier, COUNT(*) as count, ROUND(AVG(current_score), 1) as avg_score
            FROM user_reputation
            GROUP BY tier
            ORDER BY avg_score DESC
        """)
        print("\nReputation Statistics:")
        print(f"{'Tier':<12} {'Users':<8} {'Avg Score'}")
        print("-" * 35)
        for tier, count, avg_score in cur.fetchall():
            print(f"{tier:<12} {count:<8} {avg_score}")
        cur.close()
        conn.close()
