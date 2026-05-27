"""
Configuration Management Module.

This module centralizes all system settings, including API keys, cost-control metrics, 
social media targets, and data persistence paths. It uses python-dotenv to securely 
load sensitive credentials from a local .env file.
"""

import os
from dotenv import load_dotenv

# --- Environment Setup ---
# Automatically resolve the project root and load the .env file.
# This ensures path consistency regardless of where the script is executed from.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path)

class Config:
    """
    Centralized Configuration Repository.
    
    Attributes:
        GEMINI_API_KEYS (list): Rotatable keys for Google Gemini API to maximize free-tier limits.
        APIFY_API_TOKENS (list): Tokens for Apify actors (X/Twitter, Facebook scraping).
        RSS_FEEDS (dict): High-signal technical blog feeds.
        SCRAPEGRAPH_TARGETS (list): URLs for deep scraping using ScrapeGraphAI.
    """
    
    # --- 1. API CREDENTIALS ---
    # We support multiple keys to handle the aggressive ratelimiting of Free Tiers.
    # The pipeline will cycle through these if a 429 (Too Many Requests) is encountered.
    GEMINI_API_KEYS = [
        k.strip() for k in os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", "")).replace("\n", ",").split(",") 
        if k.strip()
    ]
    
    APIFY_API_TOKENS = [
        k.strip() for k in os.getenv("APIFY_API_TOKENS", os.getenv("APIFY_API_TOKEN", "")).replace("\n", ",").split(",") 
        if k.strip()
    ]
    
    # --- 2. COST & BUDGET CONTROL (APIFY) ---
    # To stay within a ~$5/month budget, we strictly limit the items fetched per run.
    # Each 'tweet' or 'post' has a specific cost associated with proxy use and execution time.
    # APIFY_X_SEARCH_MAX = 20       # [DISABLED] Maximum tweets to fetch per keyword search (~$0.008)
    APIFY_X_PROFILE_MAX = 2         # Tweets per profile in specialized tracking list (~$0.009)
    APIFY_FB_MAX = 5                # Maximum Facebook posts (Reduced to 5)
    
    # --- 3. MODEL SELECTION ---
    # Prefer newer 'Flash' models for speed/cost, falling back to Pro for complex reasoning.
    GEMINI_MODELS_FALLBACK = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-pro-latest"
    ]
    
    # --- 4. DATA SOURCES (TECHNICAL) ---
    RSS_FEEDS = {
        "OpenAI": "https://openai.com/news/rss.xml",
        "HuggingFace": "https://huggingface.co/models"
    }
    
    # Technical subreddits for high-density ML news.
    REDDIT_SUBREDDITS = ["MachineLearning"]
    
    # --- 5. SOCIAL MEDIA TARGETS ---
    # Focused list of AI labs and researchers for real-time trending news.
    X_ACCOUNTS = [
        # Organizations & Existing Focus (Temporarily commented out to save quota)
        # "OpenAI", "AnthropicAI", "claudeai", "GoogleDeepMind", "huggingface",
        # "ai_hakase_", "so_ainsight", "Kohaku_NFT", "AravSrinivas", "gdb",
        
        # 15 AI Key Researchers & Figures (Prioritized)
        "karpathy", "fchollet", "ylecun", "AndrewYNg", "rasbt",
        "dair_ai", "lilianweng", "jeremyphoward", "simonw", "_akhaliq",
        "ID_AA_Carmack", "gwern", "goodside", "drfeifei", "demishassabis"
    ]
    
    # Vietnamese-specific tech communities for localized context.
    FB_URLS = [
        "https://www.facebook.com/tinix.vn/",
        "https://www.facebook.com/groups/j2team.community"
    ]
    
    # --- 6. SCRAPEGRAPHAI TARGETS ---
    # Official blogs that don't have reliable RSS/APIs. We use ScrapeGraphAI 
    # to navigate their complex HTML structures.
    SCRAPEGRAPH_TARGETS = [
        "https://openai.com/news/",
        "https://deepmind.google/blog/",
        "https://anthropic.com/news",
        "https://deepseek.com/en/blog",
        "https://build.nvidia.com/explore/discover",
        "https://qwen.ai/research#research_latest_advancements",
        "https://mistral.ai/news/",
        "https://ai.meta.com/blog/",
        "https://huggingface.co/blog"
    ]
    MAX_SCRAPE_TARGETS_PER_RUN = 5 # How many blogs to scrape in a single session.
    
    # --- 7. NOTIFICATIONS & PERSISTENCE ---
    # Teams Webhook (Prioritizing Chat/Flow Bot as requested).
    TEAMS_WEBHOOK_URL = os.getenv("TEAMS_CHAT_WEBHOOK_URL", "")
    
    # File paths for saving local data state.
    DATA_FILE = "data/latest_news.json"
    HISTORICAL_DATA_FILE = "data/all_news.json"

    # --- 8. FILTRATION PARAMETERS ---
    # News older than 72 hours (3 days) is considered stale and ignored.
    MAX_NEWS_AGE_DAYS = 3
