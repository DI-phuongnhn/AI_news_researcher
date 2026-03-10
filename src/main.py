import os
import sys
import json
import time
from datetime import datetime

# Fix path to allow running from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.search_fetcher import search_technical_news
from src.agent.summarizer import summarize_news

def run_agent():
    print("Step 1: Discovering global technical AI trending keywords...")
    keywords = get_trending_keywords()
    print(f"Keywords discovered: {keywords[:100]}...")
    
    # Extract English keywords for technical searching
    # We assume 'EN:' is the start of the list
    search_keywords = []
    if "EN:" in keywords:
        en_part = keywords.split("EN:")[1].split("\n\n")[0]
        search_keywords = [k.strip() for k in en_part.split(",") if k.strip()][:5] # Limit to top 5 for broader search
    
    print("Waiting 30 seconds to reset API quota...")
    time.sleep(30)
    
    print("Step 2: Performing advanced technical search (using EN keywords & Social)...")
    all_raw_news = []
    if search_keywords:
        # Standard technical search
        all_raw_news.extend(search_technical_news(search_keywords, max_results=10))
        # Targeted social search to ensure X, FB, Reddit presence
        social_kws = [f"{k} site:x.com OR site:facebook.com OR site:reddit.com" for k in search_keywords[:2]]
        print("  Running targeted social media search...")
        all_raw_news.extend(search_technical_news(social_kws, max_results=5))
    
    print("Step 3: Fetching news from RSS & Reddit...")
    # RSS Sources
    for name, url in Config.RSS_FEEDS.items():
        print(f"  Fetching {name}...")
        all_raw_news.extend(fetch_rss_news(url))
        
    # Reddit
    print("  Fetching Reddit...")
    all_raw_news.extend(fetch_reddit_ml_news())
    
    print(f"Total raw items fetched: {len(all_raw_news)}")
    
    print("Step 4: Filtering & Summarizing with AI (Vietnamese)...")
    # This step already excludes general news sites via summarizer logic
    final_reports = summarize_news(all_raw_news, keywords)
    
    # Save results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "keywords": keywords,
        "reports": final_reports
    }
    
    # Accumulate results in all_news.json
    all_news_file = "data/all_news.json"
    all_historical_data = []
    
    if os.path.exists(all_news_file):
        try:
            with open(all_news_file, "r", encoding="utf-8") as f:
                all_historical_data = json.load(f)
                if not isinstance(all_historical_data, list):
                    all_historical_data = []
        except Exception as e:
            print(f"Warning: Could not load historical data: {e}")
            all_historical_data = []
            
    # Prepend new report to the beginning of the list (newest first)
    all_historical_data.insert(0, output_data)
    
    # Save both files
    os.makedirs("data", exist_ok=True)
    with open(all_news_file, "w", encoding="utf-8") as f:
        json.dump(all_historical_data, f, ensure_ascii=False, indent=4)
        
    with open("data/latest_news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully processed {len(final_reports)} high-quality technical news items.")
    return output_data

if __name__ == "__main__":
    run_agent()
