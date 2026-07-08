"""
Technical keyword discovery agent.
This module leverages AI to identify trending technical topics in the AI/ML space 
across different languages to guide the news fetching process.
"""

import os
import time
from datetime import datetime
from src.config import Config
from src.agent.model_rotator import generate_content
from src.agent.grounded_search import generate_grounded_content


def _build_prompt(languages, grounded: bool):
    """
    Builds the keyword-discovery prompt.

    Args:
        grounded: If True, explicitly instructs the model to use live web
            search (only effective when called via generate_grounded_content,
            which enables the google_search tool). If False, the model has
            no search capability and is relying on training data alone, so
            we don't pretend it can see "today's" news.
    """
    search_instruction = (
        f"Use your Google Search tool to look up ACTUAL AI news from the last 2-3 days "
        f"(today is {datetime.now().strftime('%Y-%m-%d')}). Base your answer strictly on what "
        f"you find, not on your training data."
        if grounded else
        "Base your answer on the most recent AI trends you are aware of."
    )

    return f"""
    You are an AI Trend Analyst specializing in AGENTIC WORKFLOWS and PRACTICAL AI APPLICATIONS.
    Your task is to identify the most significant TECHNICAL AI keywords/topics AND business events happening right now.

    {search_instruction}

    CRITICAL CONSTRAINTS:
    1. AVOID GENERIC TERMS: Do NOT return 'LLM', 'AI', 'Generative AI', 'Chatbot', 'Large Language Model'. These are too broad and low-signal.
    2. FOCUS ON SPECIFICITY: Identify specific model versions (e.g., 'Claude 3.7', 'DeepSeek-R1', 'O3-mini') or specific agentic patterns (e.g., 'MCP Servers', 'Browser-use', 'Computer-use', 'Multi-agent Orchestration').
    3. APPLICATION FOCUS: Look for real-world application success stories, solo-agency automation, and AI business workflows.
    4. BUSINESS SIGNAL: Separately identify concrete AI BUSINESS events — partnerships, acquisitions, integrations, funding rounds, enterprise deals (e.g., 'Microsoft-Anthropic partnership', 'Together AI Series C'). Name the specific companies/entities involved.

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
    BUSINESS: [event1, event2, event3, ...]

    Keep keywords concise (1-3 words max). BUSINESS entries can be short phrases (e.g. "Microsoft-Anthropic deal").
    """


def get_trending_keywords(languages=None):
    """
    Identifies high-signal technical keywords using the Gemini API.

    Tries a Google Search-grounded query first (real-time discovery of
    genuinely current news), then falls back to an ungrounded query, then
    to a static list derived from previously known model names.

    Args:
        languages (list, optional): List of target languages.
                                   Defaults to ["English", "Japanese"].

    Returns:
        str: A formatted string containing keywords grouped by language,
             plus a BUSINESS section listing partnership/deal entities.
    """
    if languages is None:
        languages = ["English", "Japanese"]

    # --- Block: Grounded Discovery (Primary) ---
    # Real search grounding lets us catch things that happened today,
    # rather than the model guessing from its training cutoff.
    try:
        res = generate_grounded_content(_build_prompt(languages, grounded=True))
        if res and not any(err in res.lower() for err in ["execut", "exhaust", "error"]):
            return res
    except Exception as e:
        print(f"Warning: Grounded keyword discovery failed ({e}). Falling back to ungrounded query...")

    # Brief pause to avoid immediate rate limiting on startup
    time.sleep(2)

    prompt = _build_prompt(languages, grounded=False)

    try:
        res = generate_content(prompt)
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
