import os
import time
from src.config import Config
from src.agent.model_rotator import get_rotator

def get_trending_keywords(languages=["English", "Vietnamese", "Japanese"]):
    """
    Use Gemini to discover trending AI technical keywords with model rotation.
    """
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        return "Error: GEMINI_API_KEY not found in .env"
        
    rotator = get_rotator()
    
    time.sleep(2)
    
    prompt = f"""
    You are an AI Trend Analyst. Your task is to identify the most significant TECHNICAL AI keywords/topics today.
    
    SOURCES TO CONSIDER:
    - Social Media: Trending developer discussions on X (Twitter), Reddit (r/MachineLearning, r/LocalLLaMA), and Facebook AI groups.
    - IT Blogs: Latest posts from TechCrunch, VentureBeat, Wired, and official company blogs (OpenAI, Anthropic, Google).
    
    REQUIREMENTS:
    1. Focus ONLY on high-technical relevance (e.g., 'Quantization techniques', 'DeepSeek-V3 architecture', 'Reasoning models').
    2. Provide keywords for these languages: {', '.join(languages)}.
    3. For Vietnamese (VN), prioritize terms that are globally trending in English but relevant to the local tech community.
    
    OUTPUT FORMAT:
    EN: [keyword1, keyword2, keyword3, ...]
    VN: [keyword1, keyword2, keyword3, ...]
    JP: [keyword1, keyword2, keyword3, ...]
    
    Separate languages with double newlines.
    """
    
    return rotator.generate_content(prompt)

if __name__ == "__main__":
    print(get_trending_keywords())
