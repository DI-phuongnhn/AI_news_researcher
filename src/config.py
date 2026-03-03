import os
from dotenv import load_dotenv

# Find the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path)

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.0-flash-lite" 
    # Fallback models to maximize Free Tier quota
    GEMINI_MODELS_FALLBACK = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-pro-latest"
    ]
    
    # RSS Feeds
    RSS_FEEDS = {
        "arXiv": "http://export.arxiv.org/rss/cs.AI",
        "OpenAI": "https://openai.com/news/rss.xml",
        "IEEE_Spectrum": "https://spectrum.ieee.org/rss/robotics/fulltext",
        "HuggingFace": "https://huggingface.co/blog/feed.xml"
    }
    
    # X Accounts to monitor
    X_ACCOUNTS = [
        "AndrewYNg", "karpathy", "OpenAI", "AnthropicAI", 
        "huggingface", "ylecun", "sama", "fchollet"
    ]
    
    # Reddit
    REDDIT_SUBREDDITS = ["MachineLearning"]
    
    # Output
    REPORT_DIR = "reports"
    DATA_FILE = "data/latest_news.json"
