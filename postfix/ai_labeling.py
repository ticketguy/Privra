#!/usr/bin/env python3
"""
AI-Powered Email Labeling Service
Automatically categorizes emails into appropriate folders using pattern matching
and keyword analysis.
"""

import re
from typing import List, Tuple

class AILabelingService:
    """Service for automatically labeling emails based on content analysis"""

    # Social media and social networking keywords
    SOCIAL_KEYWORDS = [
        'facebook', 'twitter', 'instagram', 'linkedin', 'tiktok', 'snapchat',
        'social', 'friend request', 'tagged you', 'mentioned you', 'liked your',
        'commented on', 'followed you', 'connection request', 'discord', 'telegram',
        'whatsapp', 'signal', 'reddit', 'pinterest', 'youtube notification'
    ]

    # Update/newsletter keywords
    UPDATE_KEYWORDS = [
        'newsletter', 'digest', 'weekly update', 'monthly update', 'news',
        'bulletin', 'announcement', 'release notes', 'changelog', 'update',
        'summary', 'roundup', 'recap', 'briefing', 'blog post', 'article',
        'subscribe', 'unsubscribe', 'subscription'
    ]

    # Promotional/Paid shill keywords
    PAID_SHILL_KEYWORDS = [
        'sponsored', 'advertisement', 'ad:', 'promo', 'discount', 'sale',
        'offer', 'deal', 'coupon', 'limited time', 'exclusive', 'special offer',
        'buy now', 'shop now', 'order now', 'save', 'off', 'free shipping',
        'partnership', 'collaboration', 'affiliate', 'referral', 'earn money',
        'make money', 'passive income', 'investment opportunity', 'crypto offer',
        'nft drop', 'presale', 'whitelist', 'airdrop promotion'
    ]

    # Notification keywords (important)
    IMPORTANT_KEYWORDS = [
        'urgent', 'important', 'action required', 'verify', 'confirm',
        'security alert', 'password reset', 'account', 'billing', 'invoice',
        'payment', 'receipt', 'order confirmation', 'shipped', 'delivered',
        'expiring', 'expires', 'deadline', 'reminder', 'alert', 'warning',
        'verification', 'two-factor', '2fa', 'otp', 'code'
    ]

    # Spam indicators
    SPAM_KEYWORDS = [
        'congratulations! you won', 'claim your prize', 'you have been selected',
        'nigerian prince', 'inheritance', 'lottery', 'click here now',
        'act now', 'limited slots', 'risk-free', 'no credit card',
        'dear sir/madam', 'dear friend', 'this is not spam', 'mlm',
        'multi-level marketing', 'get rich quick', 'work from home',
        'viagra', 'cialis', 'weight loss', 'lose weight fast'
    ]

    # Web3/Crypto specific keywords
    CRYPTO_KEYWORDS = [
        'wallet', 'nft', 'crypto', 'blockchain', 'defi', 'dao', 'token',
        'mint', 'ethereum', 'solana', 'bitcoin', 'metamask', 'opensea',
        'uniswap', 'pancakeswap', 'gas fee', 'transaction', 'smart contract',
        'web3', 'dapp', 'staking', 'yield', 'liquidity'
    ]

    # Social domains
    SOCIAL_DOMAINS = [
        'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'linkedin.com',
        'tiktok.com', 'snapchat.com', 'discord.com', 'telegram.org',
        'reddit.com', 'pinterest.com', 'youtube.com', 'twitch.tv',
        'medium.com', 'substack.com'
    ]

    # Update/Newsletter domains
    UPDATE_DOMAINS = [
        'substack.com', 'medium.com', 'ghost.io', 'mailchimp.com',
        'constantcontact.com', 'sendgrid.net', 'customerio.com',
        'intercom.io', 'marketing.', 'newsletter.', 'news.'
    ]

    def __init__(self):
        """Initialize the AI labeling service"""
        pass

    def extract_domain(self, email_address: str) -> str:
        """Extract domain from email address"""
        try:
            if '<' in email_address and '>' in email_address:
                email_address = email_address.split('<')[1].split('>')[0]
            parts = email_address.split('@')
            if len(parts) == 2:
                return parts[1].lower()
        except:
            pass
        return ''

    def contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    def analyze_email(self, from_addr: str, subject: str, body: str = '') -> List[str]:
        """
        Analyze email and return suggested labels/categories

        Args:
            from_addr: Sender email address
            subject: Email subject line
            body: Email body content (optional)

        Returns:
            List of suggested category labels
        """
        labels = []
        score = {}

        # Combine subject and body for analysis
        content = f"{subject} {body}".lower()
        domain = self.extract_domain(from_addr)

        # Score each category
        score['spam'] = 0
        score['important'] = 0
        score['socials'] = 0
        score['updates'] = 0
        score['paid_shill'] = 0

        # Check for spam first (highest priority)
        if self.contains_keywords(content, self.SPAM_KEYWORDS):
            score['spam'] += 3

        # Check domain-based categorization
        if any(social_domain in domain for social_domain in self.SOCIAL_DOMAINS):
            score['socials'] += 2

        if any(update_domain in domain for update_domain in self.UPDATE_DOMAINS):
            score['updates'] += 2

        # Check content keywords
        if self.contains_keywords(content, self.IMPORTANT_KEYWORDS):
            score['important'] += 2

        if self.contains_keywords(content, self.SOCIAL_KEYWORDS):
            score['socials'] += 1

        if self.contains_keywords(content, self.UPDATE_KEYWORDS):
            score['updates'] += 1

        if self.contains_keywords(content, self.PAID_SHILL_KEYWORDS):
            score['paid_shill'] += 2

        # Special handling for no-reply addresses
        if 'noreply@' in from_addr or 'no-reply@' in from_addr:
            score['updates'] += 1

        # Check for Web3/Crypto content (could go to updates or paid_shill)
        if self.contains_keywords(content, self.CRYPTO_KEYWORDS):
            if score['paid_shill'] > 0:
                score['paid_shill'] += 1
            else:
                score['updates'] += 1

        # Determine primary label based on highest score
        if score['spam'] >= 3:
            labels.append('spam')
        elif score['important'] >= 2:
            labels.append('important')
        elif score['socials'] >= 2:
            labels.append('socials')
        elif score['updates'] >= 2:
            labels.append('updates')
        elif score['paid_shill'] >= 2:
            labels.append('paid_shill')

        # If no clear category, default to inbox (no label)
        return labels

    def categorize_email(self, from_addr: str, subject: str, body: str = '') -> str:
        """
        Categorize email into a single primary category

        Args:
            from_addr: Sender email address
            subject: Email subject line
            body: Email body content (optional)

        Returns:
            Primary category name (inbox, socials, updates, paid_shill, spam, important)
        """
        labels = self.analyze_email(from_addr, subject, body)

        if labels:
            return labels[0]  # Return primary label

        return 'inbox'  # Default to inbox

    def should_mark_important(self, from_addr: str, subject: str, body: str = '') -> bool:
        """
        Determine if email should be marked as important

        Args:
            from_addr: Sender email address
            subject: Email subject line
            body: Email body content (optional)

        Returns:
            True if email should be marked important
        """
        content = f"{subject} {body}".lower()
        return self.contains_keywords(content, self.IMPORTANT_KEYWORDS)

    def should_mark_spam(self, from_addr: str, subject: str, body: str = '') -> bool:
        """
        Determine if email should be marked as spam

        Args:
            from_addr: Sender email address
            subject: Email subject line
            body: Email body content (optional)

        Returns:
            True if email looks like spam
        """
        content = f"{subject} {body}".lower()
        spam_count = sum(1 for keyword in self.SPAM_KEYWORDS if keyword in content)
        return spam_count >= 2  # If 2 or more spam keywords, likely spam


# Create singleton instance
ai_labeling_service = AILabelingService()


# Example usage
if __name__ == '__main__':
    service = AILabelingService()

    # Test cases
    test_emails = [
        ('noreply@facebook.com', 'John Doe tagged you in a photo', ''),
        ('newsletter@techcrunch.com', 'Daily Crypto Digest - Market Updates', ''),
        ('promo@shop.com', 'EXCLUSIVE OFFER: 50% OFF Limited Time!', ''),
        ('security@bank.com', 'URGENT: Verify your account now', ''),
        ('friend@lottery.com', 'Congratulations! You won the lottery!', ''),
        ('updates@ethereum.org', 'Ethereum 2.0 Staking Update', ''),
    ]

    print("AI Email Labeling Test Results:")
    print("=" * 60)

    for from_addr, subject, body in test_emails:
        labels = service.analyze_email(from_addr, subject, body)
        category = service.categorize_email(from_addr, subject, body)
        is_spam = service.should_mark_spam(from_addr, subject, body)
        is_important = service.should_mark_important(from_addr, subject, body)

        print(f"\nFrom: {from_addr}")
        print(f"Subject: {subject}")
        print(f"Category: {category}")
        print(f"Labels: {', '.join(labels) if labels else 'none'}")
        print(f"Spam: {is_spam} | Important: {is_important}")
