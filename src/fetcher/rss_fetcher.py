"""
RSS Feed Fetching Module.

This module provides a lightweight way to consume standard RSS/Atom feeds 
from official entities like OpenAI or Hugging Face. it uses 'feedparser' 
for robust handling of different XML standards.
"""

from typing import List, Dict
import feedparser
from datetime import datetime

def fetch_rss_news(feed_url: str) -> List[Dict]:
    """
    Parses an RSS feed and returns normalized news items.
    
    Args:
        feed_url: The URL of the XML RSS/Atom feed.
        
    Returns:
        List of dictionaries with standardized news schema.
    """
    results = []
    try:
        # --- Block: Parsing ---
        # feedparser handles the heavy lifting of XML/Atom standard compatibility.
        print(f"  RSS: Fetching {feed_url}...")
        feed = feedparser.parse(feed_url)
        
        # --- Block: Extraction ---
        for entry in feed.entries:
            # Map RSS fields (published, title, summary) to our internal schema.
            # We use .get() and fallbacks to handle feeds with missing fields.
            results.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "source": f"RSS: {feed.feed.get('title', 'Unknown Source')}",
                "date": entry.get("published", entry.get("updated", datetime.now().isoformat()))
            })
    except Exception as e:
        print(f"    Warning: RSS fetch failed for {feed_url}: {e}")
        
    return results
