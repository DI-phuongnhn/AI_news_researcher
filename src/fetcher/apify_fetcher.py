from apify_client import ApifyClient
from src.config import Config
from datetime import datetime
import json
import os

def fetch_latest_run_dataset(actor_id: str, platform_name: str):
    """
    Feches items from the LATEST run of an actor.
    Useful when the user has scheduled runs or manual runs on the Apify dashboard.
    """
    if not Config.APIFY_API_TOKENS:
        return []

    for token in Config.APIFY_API_TOKENS:
        try:
            client = ApifyClient(token)
            print(f"  [Apify] Fetching latest run for: {actor_id} ({platform_name})...")
            
            # Get the last run of the actor
            runs = client.actor(actor_id).runs().list(limit=1, desc=True)
            if not runs.items:
                print(f"    No runs found for {actor_id}.")
                continue
                
            last_run = runs.items[0]
            if last_run["status"] != "SUCCEEDED":
                print(f"    Last run status: {last_run['status']}. Still fetching items...")
                
            dataset_id = last_run["defaultDatasetId"]
            posts = []
            for item in client.dataset(dataset_id).iterate_items():
                text_content = item.get("full_text") or item.get("text") or item.get("fullText") or item.get("message") or item.get("content") or ""
                url = item.get("url") or item.get("post_url") or item.get("postUrl") or item.get("twitterUrl") or ""
                date_raw = item.get("created_at") or item.get("date") or item.get("time") or item.get("createdAt") or datetime.now().isoformat()
                
                title = item.get("title")
                if not title:
                    title = text_content[:80] + "..." if text_content else "No Title"
                    
                posts.append({
                    "title": title,
                    "link": url,
                    "summary": text_content[:500],
                    "source": f"Apify: {platform_name} (Latest Run)",
                    "date": date_raw
                })
            
            if posts:
                print(f"    [{platform_name}] Successfully retrieved {len(posts)} items from last run.")
                return posts
                
        except Exception as e:
            print(f"    [Apify] Error fetching last run for {actor_id}: {e}")
            continue
            
    return []

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
    if not Config.APIFY_API_TOKENS:
        print(f"[{platform_name}] APIFY_API_TOKENS is not set. Skipping Apify fetch.")
        return []

    posts = []
    
    for token in Config.APIFY_API_TOKENS:
        try:
            client = ApifyClient(token)
            print(f"  Starting Apify Actor: {actor_id} for {platform_name} (Token: {token[:4]}...)...")
            print(f"  Input: {run_input}")
            # Run the actor and wait for it to finish
            run = client.actor(actor_id).call(run_input=run_input)
            
            # Fetch results from the actor's default dataset
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                text_content = item.get("full_text") or item.get("text") or item.get("fullText") or item.get("message") or item.get("content") or ""
                url = item.get("url") or item.get("post_url") or item.get("postUrl") or item.get("twitterUrl") or ""
                date_raw = item.get("created_at") or item.get("date") or item.get("time") or item.get("createdAt") or datetime.now().isoformat()
                
                title = item.get("title")
                if not title:
                    title = text_content[:80] + "..." if text_content else "No Title"
                    
                posts.append({
                    "title": title,
                    "link": url,
                    "summary": text_content[:500],
                    "source": f"Apify: {platform_name}",
                    "date": date_raw
                })
                
                
            print(f"  [{platform_name}] Successfully fetched {len(posts)} items from Apify.")
            return posts
            
        except Exception as e:
            err_msg = str(e).lower()
            print(f"  [{platform_name}] Error running Apify Actor {actor_id}: {type(e).__name__}: {e}")
            
            # If it's a quota or limit error, try the NEXT token
            if "usage" in err_msg or "limit" in err_msg or "quota" in err_msg or "429" in err_msg:
                print("  -> Token exhausted or quota reached. Trying next Apify token...")
                continue
            else:
                # For other errors (e.g. invalid input), don't try other tokens as they will likely fail too
                break
                
    # If we are here, it means all tokens failed OR we broke out of the loop
    # ONLY now we try the fallback to the latest already-existing run
    print(f"  -> All Apify tokens exhausted or failed for {platform_name}. Attempting to fetch LATEST ALREADY-EXISTING RUN as final fallback...")
    latest_posts = fetch_latest_run_dataset(actor_id, platform_name)
    if latest_posts:
        return latest_posts
        
    print(f"  [{platform_name}] All Apify tokens and fallbacks failed.")
    return []

def search_x_apify(keywords_list, max_items=None):
    """
    Search X/Twitter by keywords using the official Apify Twitter Scraper.
    Actor: apify/twitter-scraper
    """
    if max_items is None:
        max_items = Config.APIFY_X_SEARCH_MAX
    
    # Updated to use apidojo/tweet-scraper (official successor to the deprecated one)
    actor_id = "apidojo/tweet-scraper"
    
    run_input = {
        "searchTerms": keywords_list,
        "maxItems": max_items,
        "sort": "Latest",
        "tweetLanguage": "en"
    }
    return fetch_apify_posts(actor_id, run_input, "X (Twitter)")

def fetch_facebook_posts_apify(target_urls=None, max_items=None):
    """
    Scrape posts from Facebook Pages or Groups using the official Facebook Posts Scraper.
    Actor: apify/facebook-posts-scraper
    """
    if max_items is None:
        max_items = Config.APIFY_FB_MAX
    
    if not target_urls:
        target_urls = Config.FB_URLS
        
    if not target_urls:
        print("  [Facebook Post] No target URLs configured. Skipping.")
        return []
        
    # Standardize to {url: ...} format for the official scraper
    urls_input = [{"url": url} for url in target_urls if url]
    
    actor_id = "apify/facebook-posts-scraper"
    run_input = {
        "startUrls": urls_input,
        "resultsLimit": max_items,
    }
    
    return fetch_apify_posts(actor_id, run_input, "Facebook")

def fetch_x_profiles_apify(handles=None, max_items_per_profile=None):
    """
    Scrapes specific X (Twitter) profiles by their handles using the apidojo scraper.
    Actor: apidojo/tweet-scraper
    """
    if max_items_per_profile is None:
        max_items_per_profile = Config.APIFY_X_PROFILE_MAX
    
    if not handles:
        handles = Config.X_ACCOUNTS
        
    if not handles:
        return []

    actor_id = "apidojo/tweet-scraper"
    
    # Update to newer schema: twitterHandles and maxItems
    run_input = {
        "twitterHandles": handles,
        "maxItems": max_items_per_profile * len(handles),
        "sort": "Latest",
        "tweetLanguage": "en"
    }
    
    return fetch_apify_posts(actor_id, run_input, "X Profiles")

def load_manual_apify_data(file_path="data/manual_import.json"):
    """
    Helper to load manually downloaded Apify JSON data.
    This allows the user to still feed data manually if automation fails (e.g. quota).
    """
    import json
    import os
    if not os.path.exists(file_path):
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        posts = []
        for item in raw_data:
            text_content = item.get("full_text") or item.get("text") or item.get("fullText") or item.get("message") or item.get("content") or ""
            url = item.get("url") or item.get("post_url") or item.get("postUrl") or ""
            date_raw = item.get("created_at") or item.get("date") or item.get("time") or item.get("createdAt") or datetime.now().isoformat()
            
            title = item.get("title")
            if not title:
                title = text_content[:80] + "..." if text_content else "Manual Import"
                
            posts.append({
                "title": title,
                "link": url,
                "summary": text_content[:500],
                "source": "Apify: Manual Import",
                "date": date_raw
            })
        print(f"  [Manual] Successfully loaded {len(posts)} items from {file_path}.")
        return posts
    except Exception as e:
        print(f"  [Manual] Error loading manual data: {e}")
        return []

if __name__ == "__main__":
    # Test script: you need a valid APIFY_API_TOKEN in your .env
    test_keywords = ["DeepSeek", "AI Researcher"]
    print(search_x_apify(test_keywords, max_items=2))
