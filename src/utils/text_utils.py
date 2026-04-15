"""
Text Utilities for AI News Researcher.
Provides normalization and similarity comparison for URLs and news content.
"""

import re
import difflib
import unicodedata
from datetime import datetime, timedelta
from dateutil import parser
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

def parse_flexible_date(date_input):
    """
    Robustly parses various date formats into a standard datetime object.
    Supports ISO, relative strings ('2 days ago', '4h'), and standard dates.
    Returns None if parsing fails.
    """
    if not date_input:
        return None
        
    if isinstance(date_input, (int, float)):
        # Handle UNIX timestamp
        try:
            return datetime.fromtimestamp(date_input)
        except:
            return None
            
    if isinstance(date_input, datetime):
        return date_input

    date_str = str(date_input).strip()
    
    # Handle relative dates (very common in social media)
    now = datetime.now()
    try:
        if 'ago' in date_str.lower() or 'h' in date_str.lower() or 'd' in date_str.lower():
            match = re.search(r'(\d+)\s*(d|h|m|s|day|hour|min|sec)', date_str.lower())
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                if unit.startswith('d'): return now - timedelta(days=val)
                if unit.startswith('h'): return now - timedelta(hours=val)
                if unit.startswith('m'): return now - timedelta(minutes=val)
                if unit.startswith('s'): return now - timedelta(seconds=val)
    except:
        pass

    # Fallback to dateutil parser
    try:
        return parser.parse(date_str)
    except:
        return None
