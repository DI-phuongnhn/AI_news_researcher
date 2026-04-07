"""
Data Manager for AI News Researcher.
Handles JSON persistence, historical data loading, and 14-day retention policy.
"""

import os
import json
from datetime import datetime
from src.config import Config
from src.utils.text_utils import normalize_url, normalize_text, calculate_similarity

class DataManager:
    """
    Manages the data pipeline, including historical comparison and persistence.
    """
    
    def __init__(self):
        self.all_news_file = Config.HISTORICAL_DATA_FILE
        self.latest_news_file = Config.DATA_FILE
        self.model_names_file = "data/model_names.json"
        self.all_historical_data = []
        self.seen_urls = set()
        self.seen_titles = []
        self.seen_summaries = []
        
    def load_history(self):
        """
        Loads historical data for deduplication and sets the initial state.
        """
        if os.path.exists(self.all_news_file):
            try:
                with open(self.all_news_file, "r", encoding="utf-8") as f:
                    self.all_historical_data = json.load(f)
                    if isinstance(self.all_historical_data, list):
                        for day_entry in self.all_historical_data:
                            for report in day_entry.get("reports", []):
                                url = normalize_url(report.get("link", ""))
                                if url: self.seen_urls.add(url)
                                
                                title = normalize_text(report.get("title", ""))
                                if title: self.seen_titles.append(title)
                                
                                summary = report.get("summary_vn", "")
                                if summary: self.seen_summaries.append(summary)
                print(f"  DataManager: Loaded {len(self.seen_urls)} historical URLs for deduplication.")
            except Exception as e:
                print(f"Warning: Could not load historical data: {e}")
        return self.all_historical_data

    def load_model_names(self):
        """
        Loads the dynamic list of known AI model names.
        Returns a dict with 'active' and 'legacy' keys.
        """
        default_models = {
            "active": ["Gemma", "Claude", "GPT", "DeepSeek", "Llama", "Mistral", "Qwen", "Gemini", "SAM", "RF-DETR"],
            "legacy": []
        }
        if os.path.exists(self.model_names_file):
            try:
                with open(self.model_names_file, "r", encoding="utf-8") as f:
                    models = json.load(f)
                    if isinstance(models, dict) and "active" in models:
                        return models
                    elif isinstance(models, list):
                        return {"active": models, "legacy": []}
            except Exception as e:
                print(f"Warning: Could not load model names: {e}")
        return default_models
        
    def save_model_names(self, new_models):
        """
        Deduplicates and appends newly discovered models to the 'active' tier in model_names.json.
        """
        if not new_models:
            return
            
        current_models = self.load_model_names()
        all_existing = current_models.get("active", []) + current_models.get("legacy", [])
        
        # Case insensitive deduplication
        existing_lower = {m.lower() for m in all_existing}
        
        added_count = 0
        for m in new_models:
            m_clean = m.strip()
            if m_clean and m_clean.lower() not in existing_lower:
                current_models.setdefault("active", []).append(m_clean)
                existing_lower.add(m_clean.lower())
                added_count += 1
                
        if added_count > 0:
            os.makedirs(os.path.dirname(self.model_names_file), exist_ok=True)
            with open(self.model_names_file, "w", encoding="utf-8") as f:
                json.dump(current_models, f, ensure_ascii=False, indent=4)
            print(f"  DataManager: Saved {added_count} new active model names.")

    def is_duplicate(self, item):
        """
        Checks if a news item is a duplicate based on URL, title similarity, or snippet similarity.
        """
        url = normalize_url(item.get("link", ""))
        title = item.get("title", "")
        summary = item.get("summary", "")
        
        # 1. URL match
        if url and url in self.seen_urls:
            return True
            
        # 2. Title similarity (>85%)
        if title:
            norm_title = normalize_text(title)
            for seen_title in self.seen_titles:
                if calculate_similarity(norm_title, seen_title) > 0.85:
                    return True
        
        # 3. Snippet similarity (>75%)
        if summary:
            for seen_sum in self.seen_summaries:
                if calculate_similarity(summary, seen_sum) > 0.75:
                    return True
                    
        return False

    def add_to_seen(self, item):
        """Track the item to avoid sub-run duplicates."""
        url = normalize_url(item.get("link", ""))
        title = item.get("title", "")
        summary = item.get("summary", "")
        
        if url: self.seen_urls.add(url)
        if title: self.seen_titles.append(normalize_text(title))
        if summary: self.seen_summaries.append(summary)

    def save_run_results(self, output_data):
        """
        Persists the latest run data and updates historical records with 14-day retention.
        """
        # Prepend newest report
        self.all_historical_data.insert(0, output_data)
        
        # Applying 14-day retention
        current_time = datetime.now()
        retention_period = 14
        
        filtered_historical_data = []
        for entry in self.all_historical_data:
            try:
                entry_time = datetime.fromisoformat(entry.get("timestamp"))
                if (current_time - entry_time).days <= retention_period:
                    filtered_historical_data.append(entry)
            except (ValueError, TypeError):
                filtered_historical_data.append(entry)
        
        # Ensure 'data/' directory exists
        os.makedirs(os.path.dirname(self.all_news_file), exist_ok=True)
        
        # Save historical data
        with open(self.all_news_file, "w", encoding="utf-8") as f:
            json.dump(filtered_historical_data, f, ensure_ascii=False, indent=4)
            
        # Save latest run results
        with open(self.latest_news_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"  DataManager: Results saved. Total historical days: {len(filtered_historical_data)}")
