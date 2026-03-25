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
    1. DEEP SCAN: Do NOT just look at hashtags (#). Scan the FULL content of posts and headlines for hidden technical signals.
    2. MODEL FOCUS: Always identify specific model versions or products (e.g., 'Claude 3.5 Opus', 'Claude 3.7', 'DeepSeek-V3', 'OpenClaw', 'Llama-4', 'SeeDance').
    3. TECHNICAL DEPTH: Focus on architectural novelty (e.g., 'Linear Attention', 'Sparse Mixture of Experts', 'Agentic Reasoners').
    4. ECOSYSTEM & TOOLS: Look for AI infrastructure, Orchestration & Automation tools (e.g., 'n8n', 'LangGraph', 'CrewAI', 'Flowise', 'Vector Databases', 'Dify').
    5. Provide keywords for these languages: {', '.join(languages)}.
    
    OUTPUT FORMAT:
    EN: [keyword1, keyword2, keyword3, ...]
    VN: [keyword1, keyword2, keyword3, ...]
    JP: [keyword1, keyword2, keyword3, ...]
    
    Keep keywords concise (1-3 words max).
    """
    
    try:
        res = rotator.generate_content(prompt)
        # Check if response is empty or an error message
        if not res or "execut" in res.lower() or "exhaust" in res.lower() or "error" in res.lower():
            raise ValueError(f"Invalid AI response: {res}")
        return res
    except Exception as e:
        print(f"Warning: Keyword discovery failed ({e}). Using technical fallback...")
        # High-signal fallback keywords to ensure search never stops
        fallback = """
        EN: [DeepSeek-V3, Claude 3.5, Gemini 2.0 Flash, Agentic Workflow, Large Language Models, RAG, Vector Database, NVIDIA, OpenAI, Anthropic]
        VN: [Mô hình ngôn ngữ lớn, Kỹ thuật RAG, Cơ sở dữ liệu Vector, Quy trình Agentic, Trí tuệ nhân tạo, DeepSeek, Claude, n8n]
        """
        return fallback.strip()

if __name__ == "__main__":
    # Test execution
    print(get_trending_keywords())
