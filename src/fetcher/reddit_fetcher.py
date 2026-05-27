"""
Reddit AI/ML News Fetch Module.

This module scrapes targeted subreddits (e.g. /r/MachineLearning) to find 
high-signal technical discussions and paper announcements. It uses a 
lightweight 'nologin' scraping approach via .json endpoints.
"""

from typing import List, Dict
import requests
from datetime import datetime
from src.config import Config

def fetch_reddit_ml_news() -> List[Dict]:
    """
    Fetches the latest 'Hot' posts from configured subreddits.
    
    Returns:
        List of news items containing title, url, and content.
    """
    results = []
    # Avoid being blocked by using a realistic User-Agent.
    headers = {"User-Agent": "Mozilla/5.0 (AI News Researcher Bot)"}
    
    for sub in Config.REDDIT_SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
        try:
            print(f"  Reddit: Fetching /r/{sub}...")
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            # --- Block: Extraction & Filtering ---
            # We iterate through the 'children' of the Reddit JSON response.
            # We ignore 'Stickied' posts as they are usually rules or mega-threads.
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                p_data = post.get("data", {})
                if p_data.get("stickied"):
                    continue
                
                # --- Block: Schema Alignment ---
                results.append({
                    "title": p_data.get("title"),
                    "link": f"https://www.reddit.com{p_data.get('permalink')}",
                    "summary": p_data.get("selftext", "")[:400] + "...",
                    "source": f"Reddit: r/{sub}",
                    "date": datetime.fromtimestamp(p_data.get("created_utc", datetime.now().timestamp())).isoformat()
                })
        except Exception as e:
            print(f"    Warning: Reddit fetch failed for r/{sub}: {e}")
            
    return results
