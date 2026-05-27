"""
Search-Engine Discovery Module.

This module uses duckduckgo_search (a lightweight, no-API-key search tool) 
to find recent technical news and releases. It enables the pipeline to 
discover news from domains not explicitly listed in static targets.
"""

from typing import List, Dict
from duckduckgo_search import DDGS
from datetime import datetime

def search_technical_news(queries: List[str], max_results: int = 5) -> List[Dict]:
    """
    Performs a live web search for technical AI news.
    
    Args:
        queries: List of search keywords or technical phrases.
        max_results: Number of search hits to return per query.
        
    Returns:
        List of standardized news items.
    """
    results = []
    # Exclude forums, social media (handled by specific fetchers), and Q&A sites.
    EXCLUDED_DOMAINS = [
        "zhihu.com", "csdn.net", "jinritoutiao.com", "juejin.cn", "baike.baidu.com",
        "ask.com", "quora.com", "reddit.com", "stackoverflow.com", "stackexchange.com",
        "facebook.com", "twitter.com", "x.com", "medium.com"
    ]
    
    # --- Block: Client Context ---
    with DDGS() as ddgs:
        for query in queries:
            try:
                # --- Block: Search Execution ---
                # We use .news() which provides reliable 'date' metadata.
                print(f"  Search (News): Querying '{query}' in us-en region...")
                search_results = ddgs.news(query, region="us-en", safesearch="moderate", timelimit="w")
                
                # --- Block: Normalization & Filtering ---
                count = 0
                for r in search_results:
                    if count >= max_results:
                        break
                    
                    link = r.get("url", r.get("href", ""))
                    if any(domain in link for domain in EXCLUDED_DOMAINS):
                        continue
                    
                    # Extract the actual publication date from the News API.
                    # If missing, we leave it as None so the pipeline filters it out.
                    pub_date = r.get("date")
                    
                    results.append({
                        "title": r.get("title"),
                        "link": link,
                        "summary": r.get("body", r.get("snippet", "")),
                        "source": f"Search: {query}",
                        "date": pub_date
                    })
                    count += 1
            except Exception as e:
                print(f"    Warning: Search failed for '{query}': {e}")
                
    return results
