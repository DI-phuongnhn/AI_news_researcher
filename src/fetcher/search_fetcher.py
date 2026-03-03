import time
from duckduckgo_search import DDGS
from datetime import datetime

def search_technical_news(keywords_list, max_results=5):
    """
    Search for technical news using English keywords to find high-depth sources.
    Excludes general news sites.
    """
    results = []
    ddgs = DDGS()
    
    # Negative keywords to filter out general news sites
    exclude_sites = [
        "vnexpress.net", "tienphong.vn", "cnn.com", "bbc.com", "nytimes.com", 
        "foxnews.com", "reuters.com", "bloomberg.com", "tuoitre.vn", "thanhnien.vn"
    ]
    exclude_query = " " + " ".join([f"-site:{site}" for site in exclude_sites])
    
    for kw in keywords_list:
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
                    "date": datetime.now().isoformat()
                })
            time.sleep(1) # Be polite
        except Exception as e:
            print(f"    Search error for {kw}: {e}")
            
    return results

if __name__ == "__main__":
    test_kws = ["DeepSeek-V3 architecture", "Mamba-2 efficiency"]
    print(search_technical_news(test_kws, max_results=2))
