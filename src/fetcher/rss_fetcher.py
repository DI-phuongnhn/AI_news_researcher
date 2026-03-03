import feedparser
from datetime import datetime, timedelta
import time

def fetch_rss_news(rss_url, days=1):
    """Fetch news from an RSS feed for the last N days."""
    feed = feedparser.parse(rss_url)
    news_items = []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for entry in feed.entries:
        # Some feeds use published_parsed, some use updated_parsed
        published_parsed = getattr(entry, 'published_parsed', getattr(entry, 'updated_parsed', None))
        
        if published_parsed:
            published_time = datetime.fromtimestamp(time.mktime(published_parsed))
            if published_time > cutoff_date:
                news_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", ""),
                    "source": rss_url,
                    "date": published_time.isoformat()
                })
        else:
            # Fallback for feeds without dates
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", ""),
                "source": rss_url,
                "date": datetime.now().isoformat()
            })
            
    return news_items

if __name__ == "__main__":
    # Test with arXiv
    test_url = "http://export.arxiv.org/rss/cs.AI"
    items = fetch_rss_news(test_url)
    print(f"Fetched {len(items)} items from {test_url}")
    for item in items[:2]:
        print(f"- {item['title']} ({item['link']})")
