import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent.pipeline import ResearchPipeline
from src.fetcher.apify_fetcher import fetch_latest_run_dataset
from src.agent.summarizer import summarize_news
from src.utils.notifier import send_teams_notification

def run_manual_ingestion():
    print("--- Manual Ingestion: Fetching Latest Apify Trial Run ---")
    
    # 1. Initialize Pipeline components
    pipeline = ResearchPipeline()
    active_models, all_models = pipeline._initial_state()
    
    # 2. Fetch Latest Run from the new X Scraper Lite
    # Actor: apidojo/twitter-scraper-lite
    raw_news = fetch_latest_run_dataset("apidojo/twitter-scraper-lite", "X (Twitter) Lite")
    
    if not raw_news:
        print("  Error: No data found in the latest run of 'apidojo/twitter-scraper-lite'.")
        return

    print(f"  Retrieved {len(raw_news)} items from Apify.")

    # 3. Process News (Deduplication and Filtering)
    # We need keywords for discovery/filtering context
    keywords, search_keywords = pipeline._discover_keywords()
    
    unique_news, filtered_news, duplicate_count = pipeline._process_news(raw_news, search_keywords, all_models)
    
    if not filtered_news:
        print("  No new or relevant items found after filtering.")
        return

    # 4. Summarize & Notify
    print(f"  Processing {len(filtered_news)} new items...")
    final_reports = pipeline._summarize_and_notify(filtered_news, keywords, all_models)
    
    # 5. Extraction of new models/keywords (Optional but good for data richness)
    actual_keywords = pipeline._refine_keywords(final_reports, keywords)

    # 6. Save results (DataManager handles 14-day retention and prepending)
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "keywords": actual_keywords,
        "reports": final_reports,
        "debug_stats": {
            "raw_total": len(raw_news),
            "duplicates": duplicate_count,
            "final": len(final_reports)
        }
    }
    
    print("  Saving results and applying 14-day retention...")
    pipeline.data_manager.save_run_results(output_data)
    
    print("--- Ingestion Complete! ---")
    print(f"Summary: {len(final_reports)} new items added to history.")

if __name__ == "__main__":
    run_manual_ingestion()
