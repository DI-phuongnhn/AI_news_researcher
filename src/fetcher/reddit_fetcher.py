import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def fetch_reddit_ml_news():
    """Fetch latest posts from r/MachineLearning using public JSON endpoint."""
    url = "https://www.reddit.com/r/MachineLearning/new.json?limit=25"
    headers = {"User-Agent": "AI-News-Researcher-Agent/1.0"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        posts = []
        for post in data['data']['children']:
            p = post['data']
            posts.append({
                "title": p['title'],
                "link": f"https://www.reddit.com{p['permalink']}",
                "summary": p.get('selftext', '')[:500],
                "source": "Reddit r/MachineLearning",
                "date": datetime.fromtimestamp(p['created_utc']).isoformat() if 'created_utc' in p else None
            })
        return posts
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
        return []

if __name__ == "__main__":
    from datetime import datetime
    print(fetch_reddit_ml_news())
