#!/usr/bin/env python3
"""
Email Sanitizer - Active Sanitization (Priority 1, Feature 1.3)

Removes tracking pixels and rewrites suspicious links before email rendering.
Prevents phishing and privacy invasion.
"""

from bs4 import BeautifulSoup
from urllib.parse import quote, unquote, urlparse
import re
from typing import Dict, List


class EmailSanitizer:
    """
    Sanitize HTML emails to remove tracking and security threats.

    Features:
    - Remove tracking pixels (1x1 images)
    - Rewrite suspicious links through safe proxy
    - Remove external stylesheets
    - Remove inline scripts
    """

    # Tracking pixel patterns
    TRACKING_PIXEL_PATTERNS = [
        r'width=["\']?1["\']?.*height=["\']?1["\']?',
        r'height=["\']?1["\']?.*width=["\']?1["\']?',
        r'\.gif\?.*campaign',
        r'tracking\..*\.(png|gif|jpg)',
        r'open\..*\.(png|gif|jpg)',
        r'pixel\..*\.(png|gif|jpg)',
        r'beacon\..*\.(png|gif|jpg)'
    ]

    # Suspicious domains (URL shorteners, known tracking)
    SUSPICIOUS_DOMAINS = [
        'bit.ly', 'tinyurl.com', 'goo.gl', 't.co',
        'ow.ly', 'buff.ly', 'is.gd', 'tiny.cc',
        'click.', 'track.', 'redirect.', 'open.'
    ]

    # Tracking keywords in URLs
    TRACKING_KEYWORDS = [
        'utm_source', 'utm_medium', 'utm_campaign',
        'utm_content', 'utm_term', 'fbclid', 'gclid',
        'mc_cid', 'mc_eid', '_hsenc', '_hsmi'
    ]

    def sanitize_html(self, html_content: str, user_email: str = None) -> Dict:
        """
        Sanitize email HTML content.

        Args:
            html_content: Raw HTML email body
            user_email: User's email (for tracking proxy)

        Returns:
            {
                "sanitized_html": str,
                "removed_pixels": int,
                "rewritten_links": int,
                "removed_scripts": int,
                "warnings": list
            }
        """
        if not html_content:
            return {
                "sanitized_html": "",
                "removed_pixels": 0,
                "rewritten_links": 0,
                "removed_scripts": 0,
                "warnings": []
            }

        soup = BeautifulSoup(html_content, 'html.parser')

        removed_pixels = 0
        rewritten_links = 0
        removed_scripts = 0
        warnings = []

        # 1. Remove tracking pixels
        for img in soup.find_all('img'):
            if self._is_tracking_pixel(img):
                # Replace with placeholder or remove entirely
                img.decompose()
                removed_pixels += 1

        # 2. Rewrite suspicious links
        for link in soup.find_all('a'):
            href = link.get('href', '')

            if href and self._is_suspicious_link(href):
                # Rewrite through safe proxy
                safe_url = self._create_safe_url(href, user_email)
                link['href'] = safe_url
                link['data-original-url'] = href
                link['class'] = link.get('class', []) + ['privra-sanitized-link']
                link['target'] = '_blank'  # Open in new tab
                link['rel'] = 'noopener noreferrer'  # Security
                rewritten_links += 1
                warnings.append(f"Suspicious link rewritten: {href[:50]}...")

            # Remove tracking parameters from all links
            if href:
                cleaned_href = self._remove_tracking_params(href)
                if cleaned_href != href:
                    link['href'] = cleaned_href

        # 3. Remove external stylesheets (can be used for tracking)
        for style_link in soup.find_all('link', rel='stylesheet'):
            if 'http' in style_link.get('href', ''):
                style_link.decompose()

        # 4. Remove all inline scripts (security)
        for script in soup.find_all('script'):
            script.decompose()
            removed_scripts += 1

        # 5. Remove event handlers (onclick, onload, etc.)
        for tag in soup.find_all(True):
            for attr in list(tag.attrs.keys()):
                if attr.startswith('on'):  # onclick, onload, onerror, etc.
                    del tag[attr]

        # 6. Sanitize iframes (prevent embedding malicious content)
        for iframe in soup.find_all('iframe'):
            # Only allow YouTube/Vimeo embeds
            src = iframe.get('src', '')
            if not any(domain in src for domain in ['youtube.com', 'vimeo.com']):
                iframe.decompose()
            else:
                # Add security attributes
                iframe['sandbox'] = 'allow-scripts allow-same-origin'

        return {
            "sanitized_html": str(soup),
            "removed_pixels": removed_pixels,
            "rewritten_links": rewritten_links,
            "removed_scripts": removed_scripts,
            "warnings": warnings
        }

    def _is_tracking_pixel(self, img_tag) -> bool:
        """Detect if image is a tracking pixel"""
        width = str(img_tag.get('width', ''))
        height = str(img_tag.get('height', ''))
        src = img_tag.get('src', '')
        style = img_tag.get('style', '')

        # Check 1x1 dimensions
        if (width in ['1', '0'] and height in ['1', '0']):
            return True

        # Check style for 1px dimensions
        if 'width:1px' in style or 'height:1px' in style:
            return True
        if 'width: 1px' in style or 'height: 1px' in style:
            return True

        # Check for tracking keywords in src
        if any(keyword in src.lower() for keyword in ['track', 'pixel', 'beacon', 'analytics', 'open']):
            return True

        # Pattern matching
        for pattern in self.TRACKING_PIXEL_PATTERNS:
            if re.search(pattern, str(img_tag), re.IGNORECASE):
                return True

        return False

    def _is_suspicious_link(self, url: str) -> bool:
        """Detect if URL is suspicious"""
        url_lower = url.lower()

        # Check suspicious domains
        for domain in self.SUSPICIOUS_DOMAINS:
            if domain in url_lower:
                return True

        # Check for URL shorteners (short URLs are suspicious)
        parsed = urlparse(url)
        if len(url) < 30 and parsed.scheme in ['http', 'https']:
            # Very short URL = likely shortened
            return True

        # Check for data URLs (can be used for XSS)
        if url.startswith('data:'):
            return True

        # Check for javascript: URLs
        if url.startswith('javascript:'):
            return True

        return False

    def _remove_tracking_params(self, url: str) -> str:
        """Remove tracking parameters from URL"""
        if '?' not in url:
            return url

        parsed = urlparse(url)
        query_parts = parsed.query.split('&')

        # Filter out tracking parameters
        clean_parts = [
            part for part in query_parts
            if not any(keyword in part for keyword in self.TRACKING_KEYWORDS)
        ]

        # Reconstruct URL
        if clean_parts:
            clean_query = '&'.join(clean_parts)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
        else:
            # No query params left
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def _create_safe_url(self, original_url: str, user_email: str = None) -> str:
        """
        Create safe proxy URL for suspicious links.

        Format: /click/safe?url=<encoded_url>
        """
        encoded_url = quote(original_url, safe='')

        # Use relative URL (no hardcoded domain)
        safe_url = f"/click/safe?url={encoded_url}"

        return safe_url

    def decode_safe_url(self, encoded_url: str) -> str:
        """Decode URL from safe proxy format"""
        return unquote(encoded_url)


# Global instance
email_sanitizer = EmailSanitizer()
