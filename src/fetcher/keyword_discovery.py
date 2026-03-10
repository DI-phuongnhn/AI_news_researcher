"""
Technical keyword discovery agent.
This module leverages AI to identify trending technical topics in the AI/ML space 
across different languages to guide the news fetching process.
"""

import os
import time
from src.config import Config
from src.agent.model_rotator import get_rotator

def get_trending_keywords(languages=None):
    """
    Identifies high-signal technical keywords using the Gemini API.
    
    Args:
        languages (list, optional): List of target languages. 
                                   Defaults to ["English", "Vietnamese", "Japanese"].
                                   
    Returns:
        str: A formatted string containing keywords grouped by language.
    """
    if languages is None:
        languages = ["English", "Vietnamese", "Japanese"]
        
    rotator = get_rotator()
    
    # Brief pause to avoid immediate rate limiting on startup
    time.sleep(2)
    
    prompt = f"""
    You are an AI Trend Analyst. Your task is to identify the most significant TECHNICAL AI keywords/topics today.
    
    SOURCES TO CONSIDER:
    - Social Media: Trending developer discussions on X (Twitter), Reddit (r/MachineLearning, r/LocalLLaMA), and Facebook AI groups.
    - IT Blogs: Latest posts from TechCrunch, VentureBeat, Wired, and official company blogs (OpenAI, Anthropic, Google).
    
    REQUIREMENTS:
    1. Focus ONLY on high-technical relevance (e.g., 'Quantization', 'MoE', 'Agentic Workflows').
    2. ALWAYS include specific names of new Models, Versions, or Frameworks (e.g., 'GPT-5', 'Claude 4', 'OpenClaw', 'DeepSeek-V3', 'Llama-4-70B').
    3. Provide keywords for these languages: {', '.join(languages)}.
    4. For Vietnamese (VN), prioritize terms that are globally trending in English but relevant to the local tech community.
    
    OUTPUT FORMAT:
    EN: [keyword1, keyword2, keyword3, ...]
    VN: [keyword1, keyword2, keyword3, ...]
    JP: [keyword1, keyword2, keyword3, ...]
    
    Separate languages with double newlines.
    """
    
    return rotator.generate_content(prompt)

if __name__ == "__main__":
    # Test execution
    print(get_trending_keywords())
