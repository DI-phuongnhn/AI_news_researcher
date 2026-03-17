"""
AI News Researcher - Main Entry Point.
This orchestrator runs the full pipeline:
1. Discovering trending technical keywords.
2. Fetching news from multiple sources (RSS, Reddit, Search).
3. Filtering and summarizing news using AI.
4. Persisting results for the Dashboard.
"""

import os
import sys
import json
import time
import difflib
from datetime import datetime

# Adjust path to handle execution from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.search_fetcher import search_technical_news
from src.agent.summarizer import summarize_news
from src.fetcher.apify_fetcher import search_x_apify, fetch_facebook_groups_apify

def calculate_similarity(text1, text2):
    """
    Calculates the similarity ratio between two strings.
    Useful for detecting near-duplicate titles or snippets.
    """
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, str(text1).lower(), str(text2).lower()).ratio()

def run_agent():
    """
    Executes the autonomous research agent pipeline with optimized deduplication and retention.
    
    Returns:
        dict: The final report data containing timestamp, keywords, and summarized news.
    """
    # Step 0: Load Historical Data for Deduplication
    all_news_file = Config.HISTORICAL_DATA_FILE
    all_historical_data = []
    seen_urls = set()
    seen_titles = []

    if os.path.exists(all_news_file):
        try:
            with open(all_news_file, "r", encoding="utf-8") as f:
                all_historical_data = json.load(f)
                if isinstance(all_historical_data, list):
                    for day_entry in all_historical_data:
                        for report in day_entry.get("reports", []):
                            url = report.get("link", "")
                            if url:
                                seen_urls.add(url)
                            title = report.get("title", "")
                            if title:
                                seen_titles.append(title)
        except Exception as e:
            print(f"Warning: Could not load historical data for deduplication: {e}")

    print("Step 1: Discovering global technical AI trending keywords...")
    keywords = get_trending_keywords()
    print(f"Keywords discovered: {keywords[:100]}...")
    
    # Extract English keywords for technical searching (top 5 for broader reach)
    search_keywords = []
    if "EN:" in keywords:
        en_part = keywords.split("EN:")[1].split("\n\n")[0]
        search_keywords = [k.strip() for k in en_part.split(",") if k.strip()][:5]
    
    # Brief pause to reset API quota state between discovery and search
    print("Waiting 30 seconds to reset API quota...")
    time.sleep(30)
    
    print("Step 2: Performing advanced technical search (using EN keywords & Social)...")
    all_raw_news = []
    if search_keywords:
        # 2a. Standard technical search
        all_raw_news.extend(search_technical_news(search_keywords, max_results=10))
        
        # 2b. Specialized social search via Apify (if token exists)
        print("  Running targeted social media search via Apify...")
        apify_posts = search_x_apify(search_keywords[:2], max_items=5)
        if apify_posts:
            all_raw_news.extend(apify_posts)
        else:
            print("  Falling back to DuckDuckGo social search...")
            social_kws = [f"{k} site:x.com OR site:facebook.com OR site:reddit.com" for k in search_keywords[:2]]
            all_raw_news.extend(search_technical_news(social_kws, max_results=5))
    
    print("Step 3: Fetching news from RSS & Reddit...")
    # 3a. RSS Feeds (arXiv, OpenAI, IEEE, etc.)
    for name, url in Config.RSS_FEEDS.items():
        print(f"  Fetching {name}...")
        all_raw_news.extend(fetch_rss_news(url))
        
    # 3b. Specialized Reddit Fetcher
    print("  Fetching Reddit...")
    all_raw_news.extend(fetch_reddit_ml_news())
    
    # 3c. Specialized Facebook Group Fetcher (via Apify)
    print("  Fetching Facebook Groups via Apify...")
    all_raw_news.extend(fetch_facebook_groups_apify(keywords=search_keywords))
    
    print(f"Total raw items fetched: {len(all_raw_news)}")

    # Step 3.5: Deduplication Step
    print("Step 3.5: Deduplicating news against historical data (URL & Title similarity)...")
    unique_raw_news = []
    duplicate_count = 0

    for item in all_raw_news:
        url = item.get("link", "")
        title = item.get("title", "")
        
        # 1. Exact URL match
        if url and url in seen_urls:
            duplicate_count += 1
            continue
            
        # 2. Title similarity (>85%)
        is_title_duplicate = False
        if title:
            for seen_title in seen_titles:
                if calculate_similarity(title, seen_title) > 0.85:
                    is_title_duplicate = True
                    break
        
        if not is_title_duplicate:
            unique_raw_news.append(item)
            if url: seen_urls.add(url)
            if title: seen_titles.append(title)
        else:
            duplicate_count += 1

    print(f"  Filtered out {duplicate_count} duplicate items. Unique items remaining: {len(unique_raw_news)}")
    
    print("Step 4: Filtering & Summarizing with AI (Vietnamese)...")
    # Filters out general news sites and low-signal content
    final_reports = summarize_news(unique_raw_news, keywords)
    
    # Create the report payload
    run_time = datetime.now()
    output_data = {
        "timestamp": run_time.isoformat(),
        "keywords": keywords,
        "reports": final_reports
    }
    
    # Step 5: Data Persistence & 14-day Retention
    # Prepend newest report
    all_historical_data.insert(0, output_data)
    
    # Filter for last 14 days
    print("Step 5.1: Applying 14-day retention policy...")
    current_time = datetime.now()
    retention_period = 14 # days
    
    filtered_historical_data = []
    for entry in all_historical_data:
        try:
            entry_time = datetime.fromisoformat(entry.get("timestamp"))
            if (current_time - entry_time).days <= retention_period:
                filtered_historical_data.append(entry)
        except (ValueError, TypeError):
            # Keep entries with invalid timestamps for safety or if they are the latest
            filtered_historical_data.append(entry)
    
    # Save both historical and latest files
    os.makedirs("data", exist_ok=True)
    with open(all_news_file, "w", encoding="utf-8") as f:
        json.dump(filtered_historical_data, f, ensure_ascii=False, indent=4)
        
    with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully processed {len(final_reports)} items. Historical data retention applied.")
    return output_data

if __name__ == "__main__":
    run_agent()
