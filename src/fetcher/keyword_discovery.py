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
                                   Defaults to ["English", "Japanese"].
                                   
    Returns:
        str: A formatted string containing keywords grouped by language.
    """
    if languages is None:
        languages = ["English", "Japanese"]
        
    rotator = get_rotator()
    
    # Brief pause to avoid immediate rate limiting on startup
    time.sleep(2)
    
    prompt = f"""
    You are an AI Trend Analyst specializing in AGENTIC WORKFLOWS and PRACTICAL AI APPLICATIONS. 
    Your task is to identify the most significant TECHNICAL AI keywords/topics today.
    
    CRITICAL CONSTRAINTS:
    1. AVOID GENERIC TERMS: Do NOT return 'LLM', 'AI', 'Generative AI', 'Chatbot', 'Large Language Model'. These are too broad and low-signal.
    2. FOCUS ON SPECIFICITY: Identify specific model versions (e.g., 'Claude 3.7', 'DeepSeek-R1', 'O3-mini') or specific agentic patterns (e.g., 'MCP Servers', 'Browser-use', 'Computer-use', 'Multi-agent Orchestration').
    3. APPLICATION FOCUS: Look for real-world application success stories, solo-agency automation, and AI business workflows.
    
    SOURCES TO CONSIDER:
    - Social Media: Trending developer discussions on X (Twitter), Reddit (r/MachineLearning, r/LocalLLaMA), and Facebook groups.
    - IT Blogs: Latest posts from HuggingFace, Nvidia, and official company blogs (OpenAI, Anthropic, Google).
    
    REQUIREMENTS:
    1. DEEP SCAN: Scan the FULL content of posts for hidden technical signals.
    2. ECOSYSTEM & TOOLS: Look for Orchestration & Automation tools (e.g., 'n8n', 'LangGraph', 'CrewAI', 'Flowise', 'Dify', 'Claude Code').
    3. SECURITY: Include AI cybersecurity signals (e.g., 'Project Glasswing', secure builds, provenance).
    4. Provide keywords for these languages: {', '.join(languages)}.
    
    OUTPUT FORMAT:
    EN: [keyword1, keyword2, keyword3, ...]
    JP: [keyword1, keyword2, keyword3, ...]
    
    Keep keywords concise (1-3 words max).
    """
    
    try:
        res = rotator.generate_content(prompt)
        # Check if response is empty or an error message
        if not res or any(err in res.lower() for err in ["execut", "exhaust", "error"]):
            raise ValueError(f"Invalid AI response: {res}")
        return res
    except Exception as e:
        print(f"Warning: Keyword discovery failed ({e}). Using dynamic model-based fallback...")
        try:
            from src.utils.data_manager import DataManager
            dm = DataManager()
            models = dm.load_model_names().get("active", [])
            import random
            fallback_models = random.sample(models, min(len(models), 8)) if models else ["Claude", "DeepSeek", "Agentic Workflow"]
            return f"EN: [{', '.join(fallback_models)}]"
        except:
            return "EN: [Claude, DeepSeek, Agentic Workflow, MCP, Automation]"

if __name__ == "__main__":
    # Test execution
    print(get_trending_keywords())
