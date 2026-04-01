import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph
from src.config import Config

def test_new_sources():
    new_sources = [
        "https://qwen.ai/research#research_latest_advancements",
        "https://mistral.ai/news/",
        "https://ai.meta.com/blog/"
    ]
    
    search_keywords = ["LLM", "Generative AI", "NLP", "Machine Learning"]
    
    specific_prompt = f"""
    Extract a list of the latest 3-5 news articles, blog posts, or model releases. 
    STRICT FILTER: ONLY include articles strictly related to these keywords: {', '.join(search_keywords)}.
    
    SOURCE SPECIFIC RULES:
    - Qwen/Mistral/Meta: Focus on model weights, paper releases, and technical advancements.
    
    For each relevant article, provide 'title', 'link', and 'summary' (technical depth).
    """
    
    all_results = {}
    
    for url in new_sources:
        print(f"Scraping: {url}...")
        res = fetch_with_scrapegraph(url, prompt=specific_prompt)
        all_results[url] = res
        print(f"Result for {url}: {json.dumps(res, indent=2, ensure_ascii=False) if res else 'None'}")
        
        # Delay between different source URLs to reset key quotas
        print("Waiting 15 seconds before next source...")
        import time
        time.sleep(15)
        
    # Save results for inspection
    with open("data/test_new_sources_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)
    
    print("\nTest completed. Results saved to data/test_new_sources_results.json")

if __name__ == "__main__":
    test_new_sources()
