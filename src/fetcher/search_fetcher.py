"""
Search-based technical news discovery.
Leverages DuckDuckGo search with English keywords and negative filters 
to find high-depth technical articles, excluding general news sites.
"""

import time
from duckduckgo_search import DDGS

def search_technical_news(keywords_list, max_results=5):
    """
    Performs a targeted technical search for a list of keywords.
    
    Args:
        keywords_list (list): List of strings identifying specific topics to search.
        max_results (int): Maximum number of results per keyword. Defaults to 5.
        
    Returns:
        list: A aggregated list of discovered news item dictionaries.
    """
    results = []
    ddgs = DDGS()
    
    # Negative keywords to filter out general/non-technical news sites
    exclude_sites = [
        "vnexpress.net", "tienphong.vn", "cnn.com", "bbc.com", "nytimes.com", 
        "foxnews.com", "reuters.com", "bloomberg.com", "tuoitre.vn", "thanhnien.vn"
    ]
    exclude_query = " " + " ".join([f"-site:{site}" for site in exclude_sites])
    
    for kw in keywords_list:
        # Refine query with technical depth modifiers
        query = f"{kw} technical deep dive research" + exclude_query
        print(f"  Searching for: {kw}...")
        
        try:
            search_results = ddgs.text(query, max_results=max_results)
            for r in search_results:
                results.append({
                    "title": r['title'],
                    "link": r['href'],
                    "summary": r['body'],
                    "source": "Search: " + kw,
                    "date": r.get('date')
                })
            # Respect search engine rate limits
            time.sleep(1) 
        except Exception as e:
            print(f"    Search error for {kw}: {e}")
            
    return results

if __name__ == "__main__":
    # Test search
    test_kws = ["nvidia", "NemoClaw"]
    print(search_technical_news(test_kws, max_results=2))
