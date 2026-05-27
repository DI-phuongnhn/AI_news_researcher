"""
ScrapeGraphAI Deep Scraping Module.

This module uses ScrapeGraphAI to perform AI-driven extraction from complex 
technical blogs. It handles lead enhancement and automated parsing of 
HTML structures that don't provide clean APIs or RSS feeds.
"""

import os
import random
from typing import List, Dict, Any
from scrapegraphai.graphs import SmartScraperGraph
from src.config import Config
from src.agent.model_rotator import get_rotator

def fetch_with_scrapegraph(url: str, prompt: str) -> Dict[str, Any]:
    """
    Executes a single ScrapeGraphAI 'SmartScraper' run.
    
    Args:
        url: The webpage to scrape.
        prompt: Natural language instructions for what to extract.
        
    Returns:
        JSON-like dictionary of extracted data.
    """
    # --- Block: Graph Configuration ---
    # We use Gemini as the reasoning engine for the scraper graph.
    # We use a random API key from our rotatable list to avoid broken/ratelimited keys.
    all_keys = Config.GEMINI_API_KEYS or os.getenv("GEMINI_API_KEY", "").split(",")
    api_key = random.choice([k.strip() for k in all_keys if k.strip()]) if all_keys else ""
    
    graph_config = {
        "llm": {
            "api_key": api_key,
            "model": "gemini-1.5-flash",
        },
    }

    # --- Block: Execution ---
    smart_scraper_graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=graph_config
    )

    try:
        # The .run() method performs automated navigation and extraction.
        print(f"  ScrapeGraph: Analyzing {url}...")
        result = smart_scraper_graph.run()
        return result
    except Exception as e:
        print(f"    Warning: ScrapeGraph failed for {url}: {e}")
        return {}

def fetch_technical_blog_posts(blog_url: str, max_items: int = 5) -> List[Dict]:
    """
    Scrapes the last N technical posts from a specific blog.
    
    Args:
        blog_url: Homepage or news page of the AI lab blog.
        max_items: Number of recent items to attempt to extract.
    """
    # --- Block: Extraction Instruction ---
    # natural language prompt used to guide the ScrapeGraph engine.
    prompt = f"""
    Extract the {max_items} most recent technical blog posts or news items.
    For each item, provide:
    - title: the technical title
    - link: absolute URL to the full post
    - summary: a short 2-sentence technical summary
    - date: the publication date string
    """
    
    raw_results = fetch_with_scrapegraph(blog_url, prompt)
    
    # --- Block: Schema Normalization ---
    # The graph might return the items under a 'posts' or 'news' key depending 
    # on its reasoning. We attempt to normalize this into our internal List[Dict] format.
    normalized = []
    items = []
    
    if isinstance(raw_results, dict):
        # Look for common keys in AI-generated JSON.
        for key in ["posts", "news", "articles", "items", "results"]:
            if key in raw_results:
                items = raw_results[key]
                break
        if not items:
            # Maybe the results are at the root?
            items = raw_results.get("posts", raw_results.get("news", []))
            
    if not isinstance(items, list):
        # Fallback if the AI returned a single object incorrectly.
        items = [raw_results] if raw_results else []

    for item in items:
        if isinstance(item, dict) and item.get('title') and item.get('link'):
            normalized.append({
                "title": item.get('title'),
                "link": item.get('link'),
                "summary": item.get('summary', ""),
                "source": f"ScrapeGraph: {blog_url.split('//')[1].split('/')[0]}",
                "date": item.get('date')
            })
            
    return normalized[:max_items]
