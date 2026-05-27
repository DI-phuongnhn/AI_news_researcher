"""
Data Persistence and History Management.

This module handles the saving and loading of historical news data, 
deduplication state, and discovered AI model names. It ensures that 
the pipeline remembers what it has already processed.
"""

import json
import os
from typing import List, Dict, Set
from src.config import Config

class DataManager:
    """
    State Manager for persistent data.
    
    Handles file-based storage of JSON datasets with basic safety checks 
    to prevent file corruption.
    """
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.history_dir = os.path.dirname(Config.HISTORICAL_DATA_FILE)
        
        # --- Block: Directory Initialization ---
        # Ensure the data directory exists before any read/write operations.
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def load_history(self) -> List[Dict]:
        """
        Loads the 'seen' URL cache from the historical data file.
        
        This prevents the pipeline from processing the same article multiple times.
        """
        if not os.path.exists(Config.HISTORICAL_DATA_FILE):
            return []
            
        try:
            with open(Config.HISTORICAL_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # --- Block: URL Cache Hydration ---
                # We store only the 'link' IDs in memory for O(1) duplicate lookup.
                self.seen_urls = {item.get("link") for item in data if item.get("link")}
                return data
        except Exception as e:
            print(f"  Warning: Failed to load history: {e}")
            return []

    def is_duplicate(self, item: Dict) -> bool:
        """
        Fast lookup to check if a news item's URL is already in history.
        """
        return item.get("link") in self.seen_urls

    def add_to_seen(self, item: Dict):
        """
        Updates the in-memory deduplication cache.
        """
        if item.get("link"):
            self.seen_urls.add(item.get("link"))

    def save_run_results(self, output: Dict):
        """
        Appends new results to the historical file and saves currently 
        found news to the 'latest' dashboard file.
        """
        # --- Block: Latest Data Update ---
        # Overwrites the 'latest' file used by the frontend dashboard.
        try:
            with open(Config.DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  Error: Failed to save latest results: {e}")

        # --- Block: Historical Append ---
        # Merges the current run's reports into the long-term archive.
        history = self.load_history()
        # Only add new unique items to history.
        new_items = output.get("reports", [])
        updated_history = history + [item for item in new_items if item.get("link") not in {h.get("link") for h in history}]
        
        try:
            with open(Config.HISTORICAL_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(updated_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  Error: Failed to append to history: {e}")

    def load_model_names(self) -> Dict[str, List[str]]:
        """
        Loads the current list of 'Active' and 'Legacy' AI models.
        """
        model_file = "data/model_names.json"
        if os.path.exists(model_file):
            with open(model_file, "r", encoding="utf-8") as f:
                return json.load(f)
        # Default starting list if no file exists.
        return {"active": ["Gemini 1.5", "GPT-4o", "Claude 3.5 Sonnet"], "legacy": []}

    def save_model_names(self, new_models: List[str]):
        """
        Updates the model knowledge base with newly discovered names.
        """
        model_file = "data/model_names.json"
        current = self.load_model_names()
        
        # --- Block: Deduplication & Merge ---
        # Moves previously seen models to legacy if they aren't on the new 'active' list.
        existing_active = set(current.get("active", []))
        for m in new_models:
            if m not in existing_active:
                current["active"].append(m)
        
        with open(model_file, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
