"""
Apify-based social media and generic web scraper.
This module uses the Apify client to scrape data from platforms like X (Twitter),
Facebook, or even general technical blogs depending on the Actor used.
"""

from apify_client import ApifyClient
from src.config import Config
from datetime import datetime

def fetch_apify_posts(actor_id: str, run_input: dict, platform_name: str):
    """
    Generic run function for an Apify Actor.
    
    Args:
        actor_id (str): The ID of the Apify Actor (e.g., 'apify/twitter-scraper').
        run_input (dict): The input specification for the Actor.
        platform_name (str): The name of the platform (e.g., 'X', 'Facebook') for standardized source tagging.
        
    Returns:
        list: A list of unified post dictionaries.
    """
    if not Config.APIFY_API_TOKEN:
        print(f"[{platform_name}] APIFY_API_TOKEN is not set. Skipping Apify fetch.")
        return []

    client = ApifyClient(Config.APIFY_API_TOKEN)
    posts = []
    
    try:
        print(f"  Starting Apify Actor: {actor_id} for {platform_name}...")
        print(f"  Input: {run_input}")
        # Run the actor and wait for it to finish
        run = client.actor(actor_id).call(run_input=run_input)
        
        # Fetch results from the actor's default dataset
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # Standardize output format
            # Different actors have different output schemas; we extract common conceptual fields
            
            # Example heuristic mapping for typical social media actors:
            # - tweet/post text is usually in 'full_text', 'text', or 'content'
            # - URLs are usually in 'url', 'post_url'
            # - dates are usually 'created_at', 'timestamp'
            
            text_content = item.get("full_text") or item.get("text") or item.get("message") or item.get("content") or ""
            url = item.get("url") or item.get("post_url") or item.get("postUrl") or ""
            date_raw = item.get("created_at") or item.get("date") or item.get("time") or datetime.now().isoformat()
            
            # Use the first 50 chars of text as title if title is missing
            title = item.get("title")
            if not title:
                title = text_content[:80] + "..." if text_content else "No Title"
                
            posts.append({
                "title": title,
                "link": url,
                "summary": text_content[:500],  # Keep a snippet
                "source": f"Apify: {platform_name}",
                "date": date_raw
            })
            
        print(f"  [{platform_name}] Successfully fetched {len(posts)} items from Apify.")
        return posts
        
    except Exception as e:
        print(f"  [{platform_name}] Error running Apify Actor {actor_id}: {type(e).__name__}: {e}")
        return []

def search_x_apify(keywords_list, max_items=5):
    """
    Search X/Twitter by keywords using the official Apify Twitter Scraper.
    Actor: apify/twitter-scraper
    """
    actor_id = "apify/twitter-scraper"
    
    run_input = {
        "searchTerms": keywords_list,
        "maxItems": max_items,
        "sort": "Latest",
        "tweetLanguage": "en"
    }
    return fetch_apify_posts(actor_id, run_input, "X (Twitter)")

def fetch_facebook_groups_apify(group_urls=None, max_items=10, keywords=None):
    """
    Scrape posts from Facebook Groups using the official Apify Facebook Groups Scraper.
    Actor: apify/facebook-groups-scraper
    """
    if not group_urls:
        group_urls = Config.FB_GROUPS
        
    if not group_urls:
        print("  [Facebook Group] No group URLs configured. Skipping.")
        return []

    actor_id = "apify/facebook-groups-scraper"
    
    # Standardize input for the official Facebook Groups Scraper
    run_input = {
        "startUrls": [{"url": url} for url in group_urls if url],
        "resultsLimit": max_items,
    }
    
    return fetch_apify_posts(actor_id, run_input, "Facebook Group")

def fetch_x_profiles_apify(handles=None, max_items_per_profile=5):
    """
    Scrapes specific X (Twitter) profiles by their handles.
    Actor: apify/twitter-scraper
    """
    if not handles:
        handles = Config.X_ACCOUNTS
        
    if not handles:
        return []

    actor_id = "apify/twitter-scraper"
    
    # Use twitterHandles for profile scraping
    run_input = {
        "twitterHandles": handles,
        "maxItems": max_items_per_profile * len(handles),
        "sort": "Latest"
    }
    
    return fetch_apify_posts(actor_id, run_input, "X Profiles")

if __name__ == "__main__":
    # Test script: you need a valid APIFY_API_TOKEN in your .env
    test_keywords = ["DeepSeek", "AI Researcher"]
    print(search_x_apify(test_keywords, max_items=2))
