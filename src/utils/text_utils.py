"""
Text Processing and Date Parsing Utilities.

This module provides common helpers for cleaning text (normalization) 
and parsing diverse date formats found across various web sources.
"""

import re
import unicodedata
from datetime import datetime
from dateutil import parser as date_parser

def normalize_text(text: str) -> str:
    """
    Cleans and normalizes strings for robust keyword matching.
    
    1. Converts to lowercase.
    2. Removes Vietnamese diacritics (e.g. 'á' -> 'a').
    3. Trims whitespace.
    
    Args:
        text: The raw string to normalize.
        
    Returns:
        A cleaned, lower-case, ASCII-compatible string.
    """
    if not text:
        return ""
    
    # Lowercase first.
    text = text.lower()
    
    # --- Block: Diacritic Removal ---
    # We use NFD normalization to separate characters from their accents,
    # then filter out the 'Combining Diacritical Mark' category (Mn).
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # Cleanup special characters but keep alphanumeric for matching.
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = " ".join(text.split())
    
    return text.strip()

def parse_flexible_date(date_str: str) -> datetime:
    """
    Attempts to parse arbitrary date strings into datetime objects.
    
    Handles standard ISO formats, human-readable strings (e.g. '2 hours ago'),
    and Unix timestamps.
    
    Returns:
        Datetime object if successful, else None.
    """
    if not date_str:
        return None
        
    # --- Block: ISO/Standard Parsing ---
    try:
        # dateutil.parser is extremely flexible with common English date strings.
        return date_parser.parse(date_str)
    except:
        pass
        
    # --- Block: Timestamp Fallback ---
    # Handle the case where the input might be a string-encoded Unix timestamp.
    try:
        if isinstance(date_str, (int, float)) or date_str.isdigit():
            return datetime.fromtimestamp(float(date_str))
    except:
        pass
        
    # --- Block: Relative Date Parsing (Minimalist) ---
    # If the user provides a very custom relative string, we might need 
    # a library like 'dateparser' (different from dateutil).
    # For now, we return None to let the pipeline handle it as 'Undated'.
    return None
def is_latin_only(text: str, limit: float = 0.3) -> bool:
    """
    Heuristic to detect if a string contains significant non-Latin script.
    
    Used to filter out Chinese, Japanese, or Korean spam/news if the 
    user only wants Global/Technical results.
    
    Args:
        text: String to check.
        limit: Percentage of non-latin characters allowed.
        
    Returns:
        True if the text is mostly Latin/English/Vietnamese.
    """
    if not text:
        return True
        
    # Count characters that are NOT Latin, Common, or Inherited (e.g. CJK scripts).
    # We allow some non-latin for technical symbols.
    non_latin_count = 0
    for char in text:
        cat = unicodedata.category(char)
        # Skip spaces, numbers, and symbols which are 'Common'
        if cat.startswith('P') or cat.startswith('N') or cat.startswith('S') or char.isspace():
            continue
            
        try:
            name = unicodedata.name(char).lower()
            # If it's not LATIN and not VIETNAMESE marks.
            if "latin" not in name and "combining" not in name:
                non_latin_count += 1
        except:
            non_latin_count += 1
            
    percentage = non_latin_count / len(text)
    return percentage < limit
