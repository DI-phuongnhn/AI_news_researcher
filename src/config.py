"""
Configuration management for the AI News Researcher.
This module handles environment variables, API keys, model rotations, 
and source definitions for keywords and news.
"""

import os
from dotenv import load_dotenv

# Find the project root directory and load .env
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path)

class Config:
    """
    Central configuration class.
    All system settings including API keys, RSS feeds, and file paths are defined here.
    """
    
    # --- Gemini API Configuration ---
    # Supports multiple keys separated by commas in GEMINI_API_KEYS or a single GEMINI_API_KEY
    GEMINI_API_KEYS = [
        k.strip() for k in os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).split(",") 
        if k.strip()
    ]
    
    # --- Apify Configuration ---
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
    
    # Models to cycle through to maximize Free Tier quota
    GEMINI_MODELS_FALLBACK = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-pro-latest"
    ]
    
    # --- News Source Configuration ---
    # RSS Feeds for official blogs and pre-prints
    RSS_FEEDS = {
        "arXiv": "http://export.arxiv.org/rss/cs.AI",
        "OpenAI": "https://openai.com/news/rss.xml",
        "IEEE_Spectrum": "https://spectrum.ieee.org/rss/robotics/fulltext",
        "HuggingFace": "https://huggingface.co/blog/feed.xml"
    }
    
    # Influential technical figures for potential search context
    X_ACCOUNTS = [
        "AndrewYNg", "karpathy", "OpenAI", "AnthropicAI", 
        "huggingface", "ylecun", "sama", "fchollet"
    ]
    
    # Targeted subreddits for technical AI/ML discussions
    REDDIT_SUBREDDITS = ["MachineLearning"]
    
    # --- Data Persistence ---
    DATA_FILE = "data/latest_news.json"
    HISTORICAL_DATA_FILE = "data/all_news.json"
