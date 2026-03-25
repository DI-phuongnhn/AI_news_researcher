"""
Technical news summarization and filtering agent.
This module uses AI to evaluate the technical depth of discovered news 
and provides high-density Vietnamese summaries for relevant items.
"""

import os
import time
from src.config import Config
from src.agent.model_rotator import get_rotator

def summarize_news(news_list, trending_keywords):
    """
    Filters and summarizes news items based on technical signal and global trends.
    
    Args:
        news_list (list): Raw news items from various fetchers.
        trending_keywords (str): Current trending keywords for context.
        
    Returns:
        list: Summarized technical news articles.
    """
    rotator = get_rotator()
    summaries = []
    
    # Domains to exclude based on general/non-technical nature
    exclude_domains = [
        "vnexpress.net", "tienphong.vn", "tuoitre.vn", "thanhnien.vn", 
        "cnn.com", "bbc.com", "nytimes.com", "reuters.com", "bloomberg.com"
    ]
    
    # Step 3.6: Prioritize ScrapeGraph and Facebook FREE items manually in the processing list
    # These are high-value deep scrapes that should always be processed first
    def get_priority_score(item):
        source = item.get("source", "").upper()
        if "SCRAPEGRAPH" in source: return 0
        if "FACEBOOK: FREE" in source: return 1
        if "APIFY" in source: return 2
        return 3

    filtered_list = [
        item for item in news_list 
        if not any(domain in item['link'] for domain in exclude_domains)
    ]

    # Sort the list by priority score
    filtered_list.sort(key=get_priority_score)
    
    # Process top candidates (expanded to reach 20+ final items as per user req)
    items_to_process = filtered_list[:50] 
    
    for i, item in enumerate(items_to_process):
        print(f"Processing item {i+1}/{len(items_to_process)}: {item['title'][:50]}...")
            
        prompt = f"""
        You are an Expert Technical AI Researcher / Senior Software Architect.
        
        VALIDATION TASK:
        Analyze the news item to see if it has REAL technical substance for AI Engineers.
        
        - Title: {item['title']}
        - Source: {item['source']}
        - Content: {item['summary'][:1500]}
        
        TRENDING CONTEXT: {trending_keywords}
        
        CRITERIA FOR 'TECHNICAL: YES':
        1. Architectural novelty: New model architectures (e.g. MLA, MoE updates), training techniques, or optimization algorithms.
        2. Frameworks/Ops: Major updates to Agentic frameworks (LangGraph, CrewAI, Autogen) or AI Infrastructure (vLLM, SGLang).
        3. Research: Math, papers (arXiv), or technical breakdowns from official labs (OpenAI, DeepSeek, Anthropic).
        4. Benchmarks/Performance: Quantitative technical benchmarks (not just "AI is better now").
        
        REJECT ('TECHNICAL: NO') IF:
        - It is just social impact, ethics, or general news.
        - It is "AI Hype" or high-level product announcements without technical documentation.
        - It is a generic news site (CNN, TechCrunch) reporting on a "cool new tool" without technical details.
        - It is merely a fundraising announcement or executive hire.
        
        5. SUMMARIZE (VIETNAMESE):
           - Provide a high-density technical summary (100-150 words).
           - USE technical terms: Agentic, Multi-Agent, RAG, KV Cache, LoRA, etc.
           - Answer: "How does this work technically?" and "What is the specific innovation?"
        
        OUTPUT FORMAT (STRICT):
        TECHNICAL: YES/NO
        SUMMARY: [Vietnamese summary here]
        """
        
        # Rotator handles key rotation internally if 429 occurs
        result = rotator.generate_content(prompt)
        
        if "TECHNICAL: YES" in result.upper():
            summary_content = result.split("SUMMARY:")[-1].strip()
            summaries.append({
                "title": item['title'],
                "link": item['link'],
                "source": item['source'],
                "summary_vn": summary_content,
                "date": item.get('date', '')
            })
            
    print(f"AI Filtering complete. Kept {len(summaries)} out of {len(items_to_process)} technical items.")
    return summaries
