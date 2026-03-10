import os
import time
from src.config import Config
from src.agent.model_rotator import get_rotator

def summarize_news(news_list, trending_keywords):
    """
    Filter for technical relevance and summarize news items in Vietnamese.
    Uses model rotation to bypass Free Tier quota limits.
    """
    rotator = get_rotator()
    summaries = []
    
    exclude_domains = [
        "vnexpress.net", "tienphong.vn", "tuoitre.vn", "thanhnien.vn", 
        "cnn.com", "bbc.com", "nytimes.com", "reuters.com", "bloomberg.com"
    ]
    
    filtered_list = [
        item for item in news_list 
        if not any(domain in item['link'] for domain in exclude_domains)
    ]
    
    # Process top candidates (expanded to reach 20+ final items)
    items_to_process = filtered_list[:45] # Slightly more to be safe
    
    for i, item in enumerate(items_to_process):
        print(f"Processing item {i+1}/{len(items_to_process)}: {item['title'][:50]}...")
            
        prompt = f"""
        You are an Expert Technical AI Researcher.
        ANALYSIS TASK:
        - Analyze the news item: {item['title']}
        - Source: {item['source']}
        - Content: {item['summary'][:1500]}
        
        KEYWORDS FOR CONTEXT: {trending_keywords}
        
        1. VALIDATE TECHNICAL DEPTH: 
           - Is this about architectural novelty, algorithmic breakthroughs, math, Agentic Frameworks (e.g., OpenClaw, LangGraph), or AI Infrastructure?
           - If it is just social impact, general AI hype, or PR for a company without technical substance, return 'TECHNICAL: NO'.
           - IF the source is a general news site (not technical), return 'TECHNICAL: NO'.
        
        2. SUMMARIZE (VIETNAMESE):
           - Provide a high-density technical summary (100-150 words).
           - Focus on: "What exactly changed?" and "Why does it matter technically?"
           - Use professional technical Vietnamese vocabulary.
        
        OUTPUT FORMAT:
        TECHNICAL: YES/NO
        SUMMARY: [Vietnamese summary here]
        """
        
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
            
    return summaries
