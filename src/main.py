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
import re
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from src.config import Config
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.search_fetcher import search_technical_news
from src.fetcher.apify_fetcher import (
    search_x_apify, 
    fetch_facebook_groups_apify, 
    fetch_x_profiles_apify
)
from src.agent.summarizer import summarize_news

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
    Normalizes text by lowercase, removing non-alphanumerics, and stripping common prefixes.
    """
    if not text:
        return ""
    # Remove brackets like [arXiv], [Social], etc.
    text = re.sub(r'\[.*?\]', '', text)
    # Lowercase and remove all non-word characters except spaces
    text = re.sub(r'[^\w\s]', '', text.lower())
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
    seen_summaries = [] # Used for snippet-level similarity

    if os.path.exists(all_news_file):
        try:
            with open(all_news_file, "r", encoding="utf-8") as f:
                all_historical_data = json.load(f)
                if isinstance(all_historical_data, list):
                    for day_entry in all_historical_data:
                        for report in day_entry.get("reports", []):
                            # Normalize URL from history
                            url = normalize_url(report.get("link", ""))
                            if url:
                                seen_urls.add(url)
                            
                            # Store normalized title
                            title = normalize_text(report.get("title", ""))
                            if title:
                                seen_titles.append(title)
                                
                            # Store summary for cross-check (even if it's Vietnamese)
                            summary = report.get("summary", "")
                            if summary:
                                seen_summaries.append(summary)
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
    
    # 3d. Specialized X Profile Fetcher (via Apify)
    print("  Fetching X Profiles via Apify...")
    all_raw_news.extend(fetch_x_profiles_apify())
    
    print(f"Total raw items fetched: {len(all_raw_news)}")

    # Step 3.5: Extreme Deduplication Step
    print("Step 3.5: Extreme Deduplicating (Strict URL, Normalized Title & Snippets)...")
    unique_raw_news = []
    duplicate_count = 0

    for item in all_raw_news:
        url = normalize_url(item.get("link", ""))
        title = item.get("title", "")
        summary = item.get("summary", "") # Current raw snippet
        
        # 1. Normalized URL match
        if url and url in seen_urls:
            duplicate_count += 1
            continue
            
        # 2. Normalized Title similarity (>85%)
        is_duplicate = False
        if title:
            norm_title = normalize_text(title)
            for seen_title in seen_titles:
                if calculate_similarity(norm_title, seen_title) > 0.85:
                    is_duplicate = True
                    break
        
        # 3. Snippet similarity check if title wasn't enough (>75% similarity)
        if not is_duplicate and summary:
            for seen_sum in seen_summaries:
                if calculate_similarity(summary, seen_sum) > 0.75:
                    is_duplicate = True
                    break

        if not is_duplicate:
            unique_raw_news.append(item)
            if url: seen_urls.add(url)
            if title: seen_titles.append(normalize_text(title))
            if summary: seen_summaries.append(summary)
        else:
            duplicate_count += 1

    print(f"  Filtered out {duplicate_count} duplicate items. Unique items remaining: {len(unique_raw_news)}")
    
    print("Step 4: Filtering & Summarizing with AI (Vietnamese)...")
    # Filters out general news sites and low-signal content
    final_reports = summarize_news(unique_raw_news, keywords)
    
    # Step 4.5: Post-Fetch Keyword Extraction (Actual found news)
    print("Step 4.5: Extracting actual keywords from fetched news...")
    actual_keywords = "N/A"
    if final_reports:
        # Construct a small context of all titles and some summaries for the AI to extract keywords
        context_text = "\n".join([f"- {r['title']}: {r['summary_vn'][:200]}" for r in final_reports[:15]])
        extraction_prompt = f"""
        Based on the following summarized AI news for today, extract the 10 most relevant TECHNICAL keywords.
        Focus on Model names (e.g. Claude, Opus, DeepSeek), Frameworks, and specific techniques mentioned.
        
        NEWS CONTEXT:
        {context_text}
        
        OUTPUT FORMAT (Strict):
        EN: [kw1, kw2, ...]
        VN: [kw1, kw2, ...]
        """
        try:
            from src.agent.model_rotator import get_rotator
            actual_keywords = get_rotator().generate_content(extraction_prompt)
        except Exception as e:
            print(f"Warning: Could not extract final keywords: {e}")
            actual_keywords = keywords # Fallback to discovery phase keywords

    # Create the report payload
    run_time = datetime.now()
    output_data = {
        "timestamp": run_time.isoformat(),
        "keywords": actual_keywords, # Use refined keywords
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
