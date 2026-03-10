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
from datetime import datetime

# Adjust path to handle execution from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.search_fetcher import search_technical_news
from src.agent.summarizer import summarize_news

def run_agent():
    """
    Executes the autonomous research agent pipeline.
    
    Returns:
        dict: The final report data containing timestamp, keywords, and summarized news.
    """
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
        # 2b. Targeted social search (X, FB, Reddit)
        print("  Running targeted social media search...")
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
    
    print(f"Total raw items fetched: {len(all_raw_news)}")
    
    print("Step 4: Filtering & Summarizing with AI (Vietnamese)...")
    # Filters out general news sites and low-signal content
    final_reports = summarize_news(all_raw_news, keywords)
    
    # Create the report payload
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "keywords": keywords,
        "reports": final_reports
    }
    
    # Step 5: Data Persistence
    all_news_file = Config.HISTORICAL_DATA_FILE
    all_historical_data = []
    
    # Load and merge with historical data
    if os.path.exists(all_news_file):
        try:
            with open(all_news_file, "r", encoding="utf-8") as f:
                all_historical_data = json.load(f)
                if not isinstance(all_historical_data, list):
                    all_historical_data = []
        except Exception as e:
            print(f"Warning: Could not load historical data: {e}")
            all_historical_data = []
            
    # Prepend newest report
    all_historical_data.insert(0, output_data)
    
    # Save both historical and latest files
    os.makedirs("data", exist_ok=True)
    with open(all_news_file, "w", encoding="utf-8") as f:
        json.dump(all_historical_data, f, ensure_ascii=False, indent=4)
        
    with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully processed {len(final_reports)} high-quality technical news items.")
    return output_data

if __name__ == "__main__":
    run_agent()
