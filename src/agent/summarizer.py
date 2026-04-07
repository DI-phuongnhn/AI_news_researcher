"""
Technical news summarization and filtering agent.
This module uses AI to evaluate the technical depth of discovered news 
and provides high-density Vietnamese summaries for relevant items.
"""

import os
import time
from src.config import Config
from src.agent.model_rotator import get_rotator

def summarize_news(news_list, trending_keywords, known_models=None):
    """
    Filters and summarizes news items based on technical signal, global trends, and known models.
    
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

    # Sources that we TRUST to be technical (ArXiv, official blogs)
    # These will bypass the strict "TECHNICAL: YES" check if AI fails or is uncertain
    trusted_sources = ["ARXIV", "SCRAPEGRAPH", "OPENAI", "DEEPMIND", "ANTHROPIC", "NVIDIA"]

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
        
        # Check if source is trusted
        source_upper = item.get("source", "").upper()
        is_trusted = any(ts in source_upper for ts in trusted_sources)
            
        models_context = ""
        if known_models:
            import random
            sample_models = random.sample(known_models, min(15, len(known_models)))
            models_context = f"\n        KNOWN AI MODELS: {', '.join(sample_models)} (and others)"

        prompt = f"""
        You are an Expert Technical AI Researcher / Senior Software Architect.
        
        VALIDATION TASK:
        Analyze the news item to see if it has REAL technical substance for AI Engineers.
        
        - Title: {item['title']}
        - Source: {item['source']}
        - Content: {item['summary'][:1500]}
        
        TRENDING CONTEXT: {trending_keywords}{models_context}
        
        CRITERIA FOR 'TECHNICAL: YES':
        1. Architectural novelty: New model architectures (e.g. MLA, MoE updates), training techniques, or optimization algorithms.
        2. Frameworks/Ops: Major updates to Agentic frameworks (LangGraph, CrewAI, Autogen) or AI Infrastructure (vLLM, SGLang).
        3. Research: Math, papers (arXiv), or technical breakdowns from official labs (OpenAI, DeepSeek, Anthropic).
        4. Benchmarks/Performance: Quantitative technical benchmarks.
        5. Implicit AI Context: If an item discusses KNOWN AI MODELS performing technical tasks (e.g., segmentation, routing, vision), mark it TECHNICAL: YES even if 'AI' or 'model' is missing.
        
        REJECT ('TECHNICAL: NO') IF:
        - It is just social impact, ethics, or general news.
        - It is "AI Hype" or high-level product announcements without technical documentation.
        - It is merely a fundraising announcement or executive hire.
        - **IMPORTANT: REJECT Community Q&A / Technical Support / Troubleshooting / Bug Reports.**
          Examples: "How to sign in?", "Antigravity not working on M1", "Is anyone experiencing login issues?", "Need help with API quota", "Can someone help me fix this?".
          Reject even if it mentions technical terms like MacBook, M1, vLLM, or Sign-in.
        
        5. SUMMARIZE (VIETNAMESE):
           - Provide a high-density technical summary (100-150 words).
           - USE technical terms: Agentic, Multi-Agent, RAG, KV Cache, LoRA, etc.
           - Answer: "How does this work technically?" and "What is the specific innovation?"
        
        OUTPUT FORMAT (STRICT):
        TECHNICAL: YES/NO
        SUMMARY: [Vietnamese summary here]
        """
        
        try:
            # Rotator handles key rotation internally if 429 occurs
            result = rotator.generate_content(prompt)
            
            # Detect AI failure string from rotator
            is_ai_failure = result.startswith("Error:") or result.startswith("Execution failed:")
            
            if is_ai_failure:
                print(f"  !!! AI Failure for this item. Fallback triggered. Reason: {result[:50]}...")
                # FALLBACK: If it's a trusted source, we MUST keep it even if AI failed
                if is_trusted:
                    summaries.append({
                        "title": item['title'],
                        "link": item['link'],
                        "source": item['source'],
                        "summary_vn": item['summary'] if item['summary'] else "AI summarization failed. High-trust source kept as fallback.",
                        "date": item.get('date', '')
                    })
                continue

            if "TECHNICAL: YES" in result.upper() or (is_trusted and "TECHNICAL: NO" not in result.upper()):
                summary_content = result.split("SUMMARY:")[-1].strip()
                if not summary_content or len(summary_content) < 10:
                    summary_content = item['summary'] # Fallback to original summary if AI output is broken
                
                summaries.append({
                    "title": item['title'],
                    "link": item['link'],
                    "source": item['source'],
                    "summary_vn": summary_content,
                    "date": item.get('date', '')
                })
        except Exception as e:
            print(f"  !!! Critical error processing item: {e}")
            if is_trusted:
                summaries.append({
                    "title": item['title'],
                    "link": item['link'],
                    "source": item['source'],
                    "summary_vn": item['summary'],
                    "date": item.get('date', '')
                })
            
    print(f"AI Filtering complete. Kept {len(summaries)} out of {len(items_to_process)} technical items.")
    return summaries
