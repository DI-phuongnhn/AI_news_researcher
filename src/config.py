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
    
    # Budget control: limit items per actor call to conserve $5/month free credits
    # With 13 runs/month, keeping total Apify cost under $0.30/run = ~$3.90/month (safe margin)
    APIFY_X_SEARCH_MAX = 3        # tweets from keyword search
    APIFY_X_PROFILE_MAX = 2       # tweets per profile handle
    APIFY_FB_MAX = 5              # posts per Facebook group run
    
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
    
    # Top AI thought leaders (trimmed to 8 to conserve Apify credits)
    X_ACCOUNTS = [
        "karpathy", "AndrewYNg", "ylecun", "_akhaliq",
        "OpenAI", "AnthropicAI", "GoogleDeepMind", "huggingface"
    ]
    
    # Targeted subreddits for technical AI/ML discussions
    REDDIT_SUBREDDITS = ["MachineLearning"]
    
    # Facebook Groups (trimmed to 2 most relevant to conserve Apify credits)
    FB_GROUPS = [
        "https://www.facebook.com/groups/874728723021553", # AI & Machine Learning group
        "https://www.facebook.com/groups/binhdanhocai"      # Bình dân học AI
    ]
    
    # --- Data Persistence ---
    DATA_FILE = "data/latest_news.json"
    HISTORICAL_DATA_FILE = "data/all_news.json"
