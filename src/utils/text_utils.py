"""
Text Utilities for AI News Researcher.
Provides normalization and similarity comparison for URLs and news content.
"""

import re
import difflib
import unicodedata
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
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
    Parse common absolute and relative date formats into a naive local datetime.
    Returns None when the input cannot be trusted as a publication date.
    """
    if date_input in (None, ""):
        return None

    if isinstance(date_input, datetime):
        parsed = date_input
    elif isinstance(date_input, (int, float)):
        try:
            parsed = datetime.fromtimestamp(date_input)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(date_input).strip()
        if not text:
            return None

        normalized = text.lower()
        relative_match = re.fullmatch(
            r"(?:(?P<a>an?|one)\s+)?(?P<value>\d+|an?|one)?\s*"
            r"(?P<unit>minute|minutes|min|hour|hours|day|days|week|weeks|month|months)"
            r"\s+ago",
            normalized,
        )
        if relative_match:
            raw_value = relative_match.group("value") or relative_match.group("a") or "1"
            value = 1 if raw_value in {"a", "an", "one"} else int(raw_value)
            unit = relative_match.group("unit")
            if unit.startswith("min"):
                delta = timedelta(minutes=value)
            elif unit.startswith("hour"):
                delta = timedelta(hours=value)
            elif unit.startswith("day"):
                delta = timedelta(days=value)
            elif unit.startswith("week"):
                delta = timedelta(weeks=value)
            else:
                delta = timedelta(days=value * 30)
            return datetime.now() - delta

        iso_candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
        except ValueError:
            parsed = None

        if parsed is None:
            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%b %d, %Y",
                "%B %d, %Y",
                "%d %b %Y",
                "%d %B %Y",
            ):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue

        if parsed is None:
            try:
                parsed = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)

    if parsed > datetime.now() + timedelta(days=1):
        return None

    return parsed
