"""
Text Utilities for AI News Researcher.
Provides normalization and similarity comparison for URLs and news content.
"""

import re
import difflib
import unicodedata
from urllib.parse import urlparse, urlunparse

def normalize_url(url):
    """
    Strips tracking parameters and fragments from a URL for robust comparison.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # Keep only scheme, netloc, and path
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, '', '', ''))
    except Exception:
        return url.lower()

def normalize_text(text):
    """
    Normalizes text by lowercase, stripping accents, and removing non-alphanumerics.
    """
    if not text:
        return ""
    # Strip accents
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                  if unicodedata.category(c) != 'Mn')
    # Replace common Vietnamese-specific characters not handled by Mn (like đ)
    text = text.replace('đ', 'd')
    # Lowercase and remove all non-word characters except spaces
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def calculate_similarity(text1, text2):
    """
    Calculates the similarity ratio between two strings using normalized versions.
    """
    n1 = normalize_text(text1)
    n2 = normalize_text(text2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()
