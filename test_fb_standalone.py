import sys
import os
from urllib.parse import urlparse

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph
from src.config import Config

def test_fb():
    fb_url = "https://m.facebook.com/groups/j2team.community"
    search_keywords = ["DeepSeek", "Claude", "AI", "Agent"]
    
    prompt = f"""
    Find recent public posts related to these keywords: {', '.join(search_keywords)}. 
    STRICT FILTER: 
    1. ONLY include posts sharing news, technical updates, or research.
    2. IGNORE any posts that are questions, Q&A, or help requests.
    Return 'title', 'link', and 'summary'.
    """
    print(f"Testing ScrapeGraph on: {fb_url}")
    res = fetch_with_scrapegraph(fb_url, prompt=prompt)
    print("Result:")
    print(res)

if __name__ == "__main__":
    test_fb()
