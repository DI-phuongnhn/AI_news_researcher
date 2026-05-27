"""
Apify-based Social Media Fetching Module.

This module integrates with the Apify platform to scrape X (Twitter) and 
Facebook. It handles actor orchestration, keyword searching, and payload 
normalization.
"""

import os
import json
from typing import List, Dict
from apify_client import ApifyClient
from src.config import Config

def get_apify_client():
    """Returns an ApifyClient, rotating through available API tokens."""
    tokens = Config.APIFY_API_TOKENS
    if not tokens:
        return None
        
    state_file = "data/apify_token_idx.json"
    idx = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                idx = json.load(f).get("token_idx", 0)
        except:
            pass
            
    client = ApifyClient(tokens[idx % len(tokens)])
    
    # Update state for next run
    next_idx = (idx + 1) % len(tokens)
    try:
        os.makedirs("data", exist_ok=True)
        with open(state_file, "w") as f:
            json.dump({"token_idx": next_idx}, f)
    except:
        pass
        
    return client

def search_x_apify(queries: List[str], max_items: int = None) -> List[Dict]:
    """
    Searches X (Twitter) for trending technical content using an Apify actor.
    
    Args:
        queries: List of search query strings (e.g. ['Gemini 1.5', 'OpenAI news']).
        max_items: Optional override for the maximum number of items to fetch.
        
    Returns:
        List of normalized news items.
    """
    if not Config.APIFY_API_TOKENS:
        return []

    # --- Block: Client Initialization ---
    client = get_apify_client()
    if not client:
        return []
    max_count = max_items or Config.APIFY_X_SEARCH_MAX
    results = []

    # --- Block: Actor Execution ---
    # We use 'apidojo/twitter-scraper-lite' for its balance of speed and cost.
    run_input = {
        "searchTerms": queries,
        "maxTweets": max_count,
        "addUserInfo": True,
        "sort": "Latest"
    }

    try:
        print(f"  Apify X: Searching for {queries[:2]}...")
        run = client.actor("apidojo/twitter-scraper-lite").call(run_input=run_input)
        
        # --- Block: Data Normalization ---
        # Map the actor-specific fields ('full_text', 'created_at') to our standard schema.
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "title": item.get("full_text", "")[:100] + "...",
                "link": f"https://x.com/i/web/status/{item.get('id_str')}",
                "summary": item.get("full_text", ""),
                "source": f"Apify X: {item.get('user', {}).get('screen_name', 'Unknown')}",
                "date": item.get("created_at")
            })
    except Exception as e:
        print(f"    Warning: Apify X search failed: {e}")
        
    return results

def fetch_facebook_posts_apify() -> List[Dict]:
    """
    Scrapes specific Facebook pages or groups for AI community news.
    
    Target URLs are defined in Config.FB_URLS.
    """
    if not Config.APIFY_API_TOKENS or not Config.FB_URLS:
        return []

    client = get_apify_client()
    if not client:
        return []
    results = []

    # --- Block: Actor Configuration ---
    # 'apify/facebook-post-scraper' is used to monitor specific groups/pages.
    run_input = {
        "startUrls": [{"url": url} for url in Config.FB_URLS],
        "resultsLimit": Config.APIFY_FB_MAX,
        "viewOption": "CHRONOLOGICAL"
    }

    try:
        print(f"  Apify FB: Scrapping {len(Config.FB_URLS)} targets...")
        run = client.actor("apify/facebook-post-scraper").call(run_input=run_input)
        
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "title": item.get("text", "")[:80] + "...",
                "link": item.get("url"),
                "summary": item.get("text", ""),
                "source": f"Apify FB: {item.get('userName', 'Unknown')}",
                "date": item.get("time")
            })
    except Exception as e:
        print(f"    Warning: Apify Facebook scraping failed: {e}")
        
    return results

def fetch_x_profiles_apify() -> List[Dict]:
    """
    Tracks specific technical thought leaders on X for high-signal updates.
    
    Account handles are defined in Config.X_ACCOUNTS.
    """
    if not Config.APIFY_API_TOKENS or not Config.X_ACCOUNTS:
        return []

    client = get_apify_client()
    if not client:
        return []
    results = []

    # --- Block: Account Batching ---
    # Fetch 5 accounts per run to save Apify quota, cycling through the list
    state_file = "data/apify_account_idx.json"
    idx = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                idx = json.load(f).get("account_idx", 0)
        except:
            pass
            
    batch_size = 5
    start_idx = idx % len(Config.X_ACCOUNTS)
    end_idx = start_idx + batch_size
    
    if end_idx > len(Config.X_ACCOUNTS):
        batch_accounts = Config.X_ACCOUNTS[start_idx:] + Config.X_ACCOUNTS[:end_idx % len(Config.X_ACCOUNTS)]
    else:
        batch_accounts = Config.X_ACCOUNTS[start_idx:end_idx]
        
    next_idx = end_idx % len(Config.X_ACCOUNTS)
    try:
        os.makedirs("data", exist_ok=True)
        with open(state_file, "w") as f:
            json.dump({"account_idx": next_idx}, f)
    except:
        pass

    # Map handles to full profile URLs.
    profile_urls = [f"https://x.com/{account}" for account in batch_accounts]
    
    run_input = {
        "startUrls": [{"url": url} for url in profile_urls],
        "maxTweets": Config.APIFY_X_PROFILE_MAX,
        "addUserInfo": True,
        "sort": "Latest"
    }

    try:
        print(f"  Apify X Profile: Tracking {len(batch_accounts)} leaders (Batch: {batch_accounts})...")
        run = client.actor("quacker/twitter-scraper").call(run_input=run_input)
        
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "title": f"Update from @{item.get('user', {}).get('screen_name')}",
                "link": f"https://x.com/i/web/status/{item.get('id_str')}",
                "summary": item.get("full_text", ""),
                "source": f"X Profile: {item.get('user', {}).get('screen_name')}",
                "date": item.get("created_at")
            })
    except Exception as e:
        print(f"    Warning: Apify X Profile tracking failed: {e}")
        
    return results
