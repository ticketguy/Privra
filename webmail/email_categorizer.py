#!/usr/bin/env python3
"""
Email categorization module
Basic rule-based categorization (placeholder for future LLM integration)
"""

import re
from typing import Dict, List

class EmailCategorizer:
    """Simple rule-based email categorizer"""

    # Category definitions
    CATEGORIES = {
        'priority': 'Priority',
        'social': 'Social',
        'updates': 'Updates',
        'promotions': 'Promotions',
        'spam': 'Spam',
        'inbox': 'Inbox'  # Default category
    }

    # Keywords for each category (placeholder - would be replaced by LLM)
    PRIORITY_KEYWORDS = [
        'urgent', 'important', 'asap', 'deadline', 'critical',
        'action required', 'time sensitive', 'immediate attention'
    ]

    SOCIAL_KEYWORDS = [
        'facebook', 'twitter', 'instagram', 'linkedin', 'tiktok',
        'snapchat', 'reddit', 'discord', 'telegram', 'whatsapp',
        'friend request', 'mentioned you', 'tagged you', 'liked your',
        'commented on', 'shared with you', 'connected with'
    ]

    UPDATES_KEYWORDS = [
        'newsletter', 'update', 'notification', 'alert', 'reminder',
        'subscription', 'digest', 'weekly', 'monthly', 'summary',
        'changelog', 'release notes', 'version', 'announcement'
    ]

    PROMOTIONS_KEYWORDS = [
        'sale', 'discount', 'offer', 'deal', 'coupon', 'promo',
        'limited time', 'special offer', 'save', 'free shipping',
        'buy now', 'shop now', 'order now', '% off', 'clearance'
    ]

    SPAM_KEYWORDS = [
        'viagra', 'cialis', 'lottery', 'winner', 'congratulations',
        'nigerian prince', 'inheritance', 'claim your prize',
        'click here now', 'make money fast', 'work from home',
        'weight loss', 'miracle cure', 'enlarge', 'refinance'
    ]

    # Sender domain patterns
    SOCIAL_DOMAINS = [
        'facebook.com', 'facebookmail.com', 'twitter.com', 'x.com',
        'instagram.com', 'linkedin.com', 'tiktok.com', 'snapchat.com',
        'reddit.com', 'discord.com', 'telegram.org'
    ]

    def __init__(self):
        """Initialize categorizer"""
        pass

    def categorize(self, subject: str, sender: str, body: str) -> str:
        """
        Categorize an email based on subject, sender, and body

        Args:
            subject: Email subject line
            sender: Sender email address
            body: Email body content

        Returns:
            str: Category key ('priority', 'social', 'updates', 'promotions', 'spam', or 'inbox')
        """
        # Normalize text for matching
        text = f"{subject} {body}".lower()
        sender_lower = sender.lower()

        # Check for spam first (highest priority check)
        if self._contains_keywords(text, self.SPAM_KEYWORDS):
            return 'spam'

        # Check for priority indicators
        if self._contains_keywords(text, self.PRIORITY_KEYWORDS):
            return 'priority'

        # Check for social media
        if self._is_social_domain(sender_lower) or self._contains_keywords(text, self.SOCIAL_KEYWORDS):
            return 'social'

        # Check for promotional content
        if self._contains_keywords(text, self.PROMOTIONS_KEYWORDS):
            return 'promotions'

        # Check for updates/newsletters
        if self._contains_keywords(text, self.UPDATES_KEYWORDS):
            return 'updates'

        # Default to inbox
        return 'inbox'

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text contains any of the keywords

        Args:
            text: Text to search (should be lowercase)
            keywords: List of keywords to look for

        Returns:
            bool: True if any keyword is found
        """
        for keyword in keywords:
            if keyword in text:
                return True
        return False

    def _is_social_domain(self, sender: str) -> bool:
        """
        Check if sender is from a social media domain

        Args:
            sender: Sender email address (lowercase)

        Returns:
            bool: True if sender is from social media
        """
        for domain in self.SOCIAL_DOMAINS:
            if domain in sender:
                return True
        return False

    def get_category_name(self, category_key: str) -> str:
        """
        Get display name for a category key

        Args:
            category_key: Category key

        Returns:
            str: Display name
        """
        return self.CATEGORIES.get(category_key, 'Inbox')

    def get_all_categories(self) -> Dict[str, str]:
        """
        Get all available categories

        Returns:
            dict: Category key -> display name mapping
        """
        return self.CATEGORIES.copy()


# Future LLM integration placeholder
class LLMEmailCategorizer(EmailCategorizer):
    """
    Placeholder for future LLM-based categorization

    TODO: Integrate with LLM API to provide intelligent categorization
    Features to add:
    - Semantic understanding of email content
    - Learning from user corrections
    - Context-aware categorization
    - Multi-label classification
    - Confidence scores
    """

    def __init__(self, llm_api_key=None):
        """Initialize LLM categorizer (not implemented yet)"""
        super().__init__()
        self.llm_api_key = llm_api_key
        # TODO: Initialize LLM client

    def categorize(self, subject: str, sender: str, body: str) -> str:
        """
        Categorize using LLM (falls back to rule-based for now)

        TODO: Implement LLM-based categorization
        """
        # Fall back to rule-based for now
        return super().categorize(subject, sender, body)

    def categorize_with_confidence(self, subject: str, sender: str, body: str) -> Dict:
        """
        Categorize with confidence score (future implementation)

        Returns:
            dict: {
                'category': str,
                'confidence': float,
                'explanation': str
            }
        """
        # TODO: Implement LLM categorization with confidence
        category = self.categorize(subject, sender, body)
        return {
            'category': category,
            'confidence': 0.5,  # Placeholder
            'explanation': 'Rule-based categorization (LLM not yet implemented)'
        }
