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

# Ensure project root is in sys.path for 'src' package resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph
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
    Normalizes text by lowercase, removing non-alphanumerics.
    """
    if not text:
        return ""
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

def filter_relevance(news_list, search_keywords):
    """
    Stricter pre-AI filter that uses Regex word boundaries to avoid false matches
    (e.g., matching 'ai' in 'cô gái'). Also excludes common noise patterns.
    """
    if not search_keywords:
        return news_list
        
    filtered = []
    # Keywords to EXCLUDE (Noise blacklist)
    excluded_patterns = [
        r"\boscar\b", r"\bhoạt hình\b", r"\bstopmotion\b", r"\banimation\b",
        r"\bbán hàng\b", r"\bgom đơn\b", r"\bquảng cáo\b", r"\bkhóa học\b",
        r"\bmovie\b", r"\bcinema\b", r"\bphim\b",
        r"có được không", r"ai có ý tưởng", r"dạy làm", r"tìm người", r"cần tư vấn",
        r"hỏi đáp", r"giúp em", r"giúp mình"
    ]
    
    # Normalize keywords for comparison and escape for regex
    norm_keywords = [normalize_text(kw) for kw in search_keywords if normalize_text(kw)]
    print(f"  Debug: Normalized keywords for filtering: {norm_keywords}")
    
    for item in news_list:
        title = item.get("title", "")
        summary = item.get("summary", "")
        # Check against normalized full text
        text_to_check = normalize_text(f"{title} {summary}")
        
        # 1. Strict Exclusion (Noise)
        is_noise = False
        for pattern in excluded_patterns:
            if re.search(pattern, text_to_check):
                is_noise = True
                break
        if is_noise:
            continue

        # 2. Keyphrase Matching (Less strict, no \b for better non-ASCII support)
        is_relevant = False
        for kw in norm_keywords:
            if kw in text_to_check: # Simpler inclusion check
                is_relevant = True
                break
        
        # 3. Source-specific trust (ArXiv and ScrapeGraph are trusted/pre-filtered)
        source_lower = item.get("source", "").lower()
        if not is_relevant:
            if "arxiv" in source_lower or "scrapegraph" in source_lower:
                is_relevant = True
            
        if is_relevant:
            filtered.append(item)
            
    print(f"  Strict Filtering: Kept {len(filtered)} out of {len(news_list)} items.")
    return filtered

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
        print(f"  Searching DuckDuckGo for: {', '.join(search_keywords)}...")
        raw_tech = search_technical_news(search_keywords, max_results=10)
        all_raw_news.extend(raw_tech)
        print(f"  -> Found {len(raw_tech)} technical items.")
        
        # 2b. Specialized social search via Apify (if token exists)
        print(f"  Running targeted social media search via Apify for: {', '.join(search_keywords[:2])}...")
        apify_posts = search_x_apify(search_keywords[:2])
        if apify_posts:
            all_raw_news.extend(apify_posts)
            print(f"  -> Found {len(apify_posts)} Apify social posts.")
        else:
            print("  -> Apify social search returned 0 items, falling back to DuckDuckGo social...")
            social_kws = [f"{k} site:x.com OR site:facebook.com OR site:reddit.com" for k in search_keywords[:2]]
            social_news = search_technical_news(social_kws, max_results=5)
            all_raw_news.extend(social_news)
            print(f"  -> Found {len(social_news)} fallback social items.")
        
        # 2c. Deep Scrape with ScrapeGraphAI on top tech leads
        print("  Enhancing top technical results with ScrapeGraphAI...")
        top_tech_leads = raw_tech[:3] # Deep scan top 3 findings
        for lead in top_tech_leads:
            print(f"    Deep scraping: {lead['title']}...")
            
            # Use keywords for internal filtering during deep scrape
            enhance_prompt = f"""
            Analyze the following article and extract key technical information. 
            ONLY return data if the article is related to these keywords: {', '.join(search_keywords)}.
            If not related, return an empty object.
            Fields to extract: 'title', 'summary' (technical depth).
            """
            deep_res = fetch_with_scrapegraph(lead['link'], prompt=enhance_prompt)
            if deep_res and isinstance(deep_res, dict) and deep_res.get('title'):
                # Update summary with high-quality AI extraction
                lead['summary'] = deep_res.get('summary', lead['summary'])
                lead['title'] = deep_res.get('title', lead['title']) # Sometimes useful
        
        # 2d. Scrape specific high-priority targets from config
        print("  Scraping specific high-priority targets via ScrapeGraphAI...")
        for target_url in Config.SCRAPEGRAPH_TARGETS:
            print(f"    Scraping: {target_url}...")
            # Prompt specifically to extract news items from a list/blog page
            specific_prompt = f"""
            Extract a list of the latest 3-5 news articles or blog posts. 
            STRICT FILTER: ONLY include articles strictly related to these keywords: {', '.join(search_keywords)}.
            For each relevant article, provide 'title', 'link', and 'summary'.
            """
            specific_res = fetch_with_scrapegraph(target_url, prompt=specific_prompt)
            
            if specific_res:
                # Handle potential list or dict results from SmartScraperGraph
                items = []
                if isinstance(specific_res, list):
                    items = specific_res
                elif isinstance(specific_res, dict):
                    # Try to find a list within the dict (common for SmartScraperGraph)
                    for val in specific_res.values():
                        if isinstance(val, list):
                            items = val
                            break
                    if not items: items = [specific_res]
                
                for item in items:
                    if isinstance(item, dict) and item.get('title') and item.get('link'):
                        all_raw_news.append({
                            "title": item.get('title'),
                            "link": item.get('link'),
                            "summary": item.get('summary', ''),
                            "source": "ScrapeGraph: " + urlparse(target_url).netloc,
                            "date": datetime.now().isoformat()
                        })
    
    print("Step 3: Fetching news from RSS & Reddit...")
    # 3a. RSS Feeds (arXiv, OpenAI, IEEE, etc.)
    for name, url in Config.RSS_FEEDS.items():
        print(f"  Fetching {name}...")
        rss_items = fetch_rss_news(url)
        all_raw_news.extend(rss_items)
        print(f"    -> {len(rss_items)} items.")
        
    # 3b. Specialized Reddit Fetcher
    print("  Fetching Reddit r/MachineLearning...")
    reddit_items = fetch_reddit_ml_news()
    all_raw_news.extend(reddit_items)
    print(f"    -> {len(reddit_items)} items.")
    
    # 3c. Specialized Facebook Group Fetcher (via Apify and Fallback to ScrapeGraphAI)
    print("  Fetching Facebook Groups...")
    fb_items = []
    
    # Try Apify first if token exists (more reliable but paid)
    if Config.APIFY_API_TOKEN:
        print("    Using Apify for Facebook Groups...")
        fb_items = fetch_facebook_groups_apify(keywords=search_keywords)
        all_raw_news.extend(fb_items)
        print(f"      -> Found {len(fb_items)} items via Apify.")
    
    # FREE FALLBACK: If Apify failed, returned 0 items, or no token exists
    if not fb_items:
        print("    Apify returned no results (or no token). Using FREE ScrapeGraphAI (Mobile URL) fallback...")
        for fb_url in Config.FB_GROUPS:
            # Transform to mobile link for easier scraping
            mobile_url = fb_url.replace("www.facebook.com", "m.facebook.com")
            print(f"      Scraping Mobile FB: {mobile_url}...")
            
            fb_prompt = f"""
            Find recent public posts related to these keywords: {', '.join(search_keywords)}. 
            STRICT FILTER: 
            1. ONLY include posts sharing news, technical updates, or research.
            2. IGNORE any posts that are:
               - Questions or Q&A (e.g., "cho mình hỏi", "giúp em với", "tư vấn dùm", "Question", "How to")
               - Discussion/Help requests (e.g., "ai biết cách", "fix lỗi", "cần tìm")
               - Advertisements, personal life updates, or recruitment.
            Return 'title' (first 80 chars), 'link' (absolute URL), and 'summary'.
            """
            fb_res = fetch_with_scrapegraph(mobile_url, prompt=fb_prompt)
            
            # Similar processing as Step 2d
            items = []
            if isinstance(fb_res, list): items = fb_res
            elif isinstance(fb_res, dict):
                for val in fb_res.values():
                    if isinstance(val, list): items = val; break
                if not items: items = [fb_res]
            
            for item in items:
                if isinstance(item, dict) and item.get('title'):
                    all_raw_news.append({
                        "title": item.get('title'),
                        "link": item.get('link') if item.get('link') else fb_url,
                        "summary": item.get('summary', ''),
                        "source": "Facebook: FREE (" + mobile_url + ")",
                        "date": datetime.now().isoformat()
                    })
    
    # 3d. Specialized X Profile Fetcher (via Apify)
    print("  Fetching X Profiles via Apify...")
    x_items = fetch_x_profiles_apify()
    all_raw_news.extend(x_items)
    print(f"    -> {len(x_items)} items.")
    
    # Ensure ScrapeGraph items are at the FRONT of all_raw_news for deduplication priority 
    # (first seen is kept in current dedupe logic)
    print("  Prioritizing ScrapeGraph items for deduplication...")
    sg_items = [i for i in all_raw_news if "ScrapeGraph" in i.get("source", "")]
    non_sg_items = [i for i in all_raw_news if "ScrapeGraph" not in i.get("source", "")]
    all_raw_news = sg_items + non_sg_items
    
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
    
    # Step 3.6: Source-Diverse Ordering & ArXiv Limiting
    # Prioritize social media (Apify) and limit ArXiv to exactly 10 items as requested
    print("Step 3.6: Prioritizing Apify and limiting ArXiv...")
    social_items = [item for item in unique_raw_news if "Apify" in item.get("source", "")]
    
    # ArXiv items (from RSS)
    arxiv_items = [item for item in unique_raw_news if "arxiv" in item.get("source", "").lower() or "arxiv" in item.get("link", "").lower()]
    limited_arxiv = arxiv_items[:10]
    
    # Other items (Reddit, other RSS feeds not from ArXiv)
    other_items = [item for item in unique_raw_news if "Apify" not in item.get("source", "") and item not in arxiv_items]
    
    # Final ordering: Social (Priority) -> Limited ArXiv -> Others
    diverse_news = social_items + limited_arxiv + other_items
    
    print(f"  Priority (Social/Apify): {len(social_items)}")
    print(f"  ArXiv (Limited): {len(limited_arxiv)} (from {len(arxiv_items)})")
    print(f"  Others: {len(other_items)}")
    
    # Step 3.7: Pre-AI Relevance Filtering
    # Filter diverse_news by discovered keywords before calling AI to save quota and improve relevance
    print("Step 3.7: Pre-AI Relevance filtering...")
    filtered_news = filter_relevance(diverse_news, search_keywords)
    
    print("Step 4: Filtering & Summarizing with AI (Vietnamese)...")
    # Filters out general news sites and low-signal content
    final_reports = summarize_news(filtered_news, keywords)
    
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
