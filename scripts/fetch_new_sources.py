import sys
import os
import json
from datetime import datetime
import time

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph
from src.config import Config

def fetch_and_summary_new_sources():
    new_sources = [
        "https://qwen.ai/research#research_latest_advancements",
        "https://mistral.ai/news/",
        "https://ai.meta.com/blog/"
    ]
    
    search_keywords = ["LLM", "Generative AI", "NLP", "Machine Learning", "Model Weights", "MoE"]
    
    # Very detailed prompt to ensure high-quality technical extraction
    specific_prompt = f"""
    Find the latest 3 news items from this technical AI blog/resource.
    STRICT TECHNICAL FILTER: ONLY include articles about model architectures, new releases (weights), training methods, or optimization algorithms. 
    Keywords context: {', '.join(search_keywords)}.
    
    For each relevant item, extract:
    - 'title': The technical headline.
    - 'link': The absolute URL.
    - 'summary_en': A 2-3 sentence deep-dive technical summary in English.
    
    Format: A JSON list of objects.
    """
    
    all_reports = []
    
    for url in new_sources:
        print(f"Scraping: {url}...")
        res = fetch_with_scrapegraph(url, prompt=specific_prompt)
        
        if res:
            # Handle list or dict results
            items = []
            if isinstance(res, list): items = res
            elif isinstance(res, dict):
                for val in res.values():
                    if isinstance(val, list): items = val; break
                if not items: items = [res]
            
            for item in items:
                if isinstance(item, dict) and item.get('title'):
                    all_reports.append({
                        "title": item.get('title'),
                        "link": item.get('link') if item.get('link') else url,
                        "summary_en": item.get('summary_en', item.get('summary', 'No English summary available.')),
                        "source": "ScrapeGraph: " + url.split('//')[-1].split('/')[0]
                    })
        
        # Wait between sources to reset API quotas
        print("Waiting 15 seconds before next source...")
        time.sleep(15)
        
    if not all_reports:
        print("No news items found on the 3 new sources.")
        return

    # Summarize with AI (Vietnamese) - Fallback to simple translation if summary fails
    print(f"Found {len(all_reports)} items. Summarizing in Vietnamese...")
    from src.agent.model_rotator import get_rotator
    rotator = get_rotator()
    
    for report in all_reports:
        vn_prompt = f"""
        Provide a high-density technical summary in Vietnamese for the following AI news:
        Title: {report['title']}
        English Summary: {report['summary_en']}
        
        Guidelines: Use terms like Agentic, RAG, MoE, LoRA where appropriate. Focus on 'How it works'.
        Final result: [Vietnamese Summary Only]
        """
        try:
            vn_sum = rotator.generate_content(vn_prompt)
            if "ERROR:" in vn_sum.upper() or "FAILED:" in vn_sum.upper():
                report['summary_vn'] = report['summary_en'] # Fallback
            else:
                report['summary_vn'] = vn_sum
        except Exception:
            report['summary_vn'] = report['summary_en']

    # Final payload for all_news.json
    today_entry = {
        "timestamp": datetime.now().isoformat(),
        "keywords": f"EN: [{', '.join(search_keywords)}]\nVN: [Lượng tử hóa, Kiến trúc mô hình, Trọng số mới, MoE]",
        "reports": all_reports,
        "debug_stats": {
            "raw_total": len(all_reports),
            "duplicates": 0,
            "final": len(all_reports)
        }
    }
    
    # Update all_news.json
    all_news_file = Config.HISTORICAL_DATA_FILE
    all_historical_data = []
    if os.path.exists(all_news_file):
        with open(all_news_file, "r", encoding="utf-8") as f:
            all_historical_data = json.load(f)
            
    # Prepend
    all_historical_data.insert(0, today_entry)
    
    with open(all_news_file, "w", encoding="utf-8") as f:
        json.dump(all_historical_data, f, ensure_ascii=False, indent=4)
        
    # Also update latest_news.json
    with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(today_entry, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully updated with {len(all_reports)} new items.")

if __name__ == "__main__":
    fetch_and_summary_new_sources()
