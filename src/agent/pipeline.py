"""
Research Pipeline Orchestrator.
Coordinates the end-to-end flow from discovery to notification.
"""

import os
import json
import time
from datetime import datetime
from src.config import Config
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.search_fetcher import search_technical_news
from src.fetcher.apify_fetcher import (
    search_x_apify, 
    fetch_facebook_groups_apify, 
    fetch_x_profiles_apify,
    load_manual_apify_data
)
from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph
from src.agent.summarizer import summarize_news
from src.agent.model_rotator import get_rotator
from src.utils.data_manager import DataManager
from src.utils.text_utils import normalize_text, normalize_url
from src.utils.notifier import send_teams_notification

class ResearchPipeline:
    """
    Main orchestrator for the AI News Research process.
    """
    
    def __init__(self):
        self.data_manager = DataManager()
        self.output_data = {}
        
    def filter_relevance(self, news_list, search_keywords):
        """
        Stricter pre-AI filter that uses Regex word boundaries to avoid false matches.
        """
        import re
        if not search_keywords:
            return news_list
            
        filtered = []
        excluded_patterns = [
            r"\boscar\b", r"\bhoạt hình\b", r"\bstopmotion\b", r"\banimation\b",
            r"\bbán hàng\b", r"\bgom đơn\b", r"\bquảng cáo\b", r"\bkhóa học\b",
            r"\bmovie\b", r"\bcinema\b", r"\bphim\b",
            r"có được không", r"ai có ý tưởng", r"dạy làm", r"tìm người", r"cần tư vấn",
            r"hỏi đáp", r"giúp em", r"giúp mình", r"ask", r"hỏi",
            r"bấm sign in", r"không được", r"không phản hồi", r"quota", r"tình trạng", 
            r"có ai bị", r"ai gặp", r"lỗi rồi", r"nhờ hỗ trợ", r"chào mng", r"mọi người ơi"
        ]
        
        norm_keywords = [normalize_text(kw) for kw in search_keywords if normalize_text(kw)]
        
        for item in news_list:
            title = item.get("title", "")
            summary = item.get("summary", "")
            text_to_check = normalize_text(f"{title} {summary}")
            
            is_noise = False
            for pattern in excluded_patterns:
                if re.search(pattern, text_to_check):
                    is_noise = True
                    break
            if is_noise:
                continue

            is_relevant = False
            for kw in norm_keywords:
                if kw in text_to_check:
                    is_relevant = True
                    break
            
            source_lower = item.get("source", "").lower()
            if not is_relevant:
                if "arxiv" in source_lower or "scrapegraph" in source_lower:
                    is_relevant = True
                
            if is_relevant:
                filtered.append(item)
                
        print(f"  Filtering: Kept {len(filtered)} out of {len(news_list)} items.")
        return filtered

    def run(self):
        """
        Main execution method for the pipeline.
        """
        # Step 0: Initial State
        self.data_manager.load_history()
        
        # Step 1: Discover Keywords
        print("Step 1: Discovering trending AI technical keywords...")
        keywords = get_trending_keywords()
        search_keywords = []
        if "EN:" in keywords:
            en_part = keywords.split("EN:")[1].split("\n\n")[0]
            search_keywords = [k.strip() for k in en_part.split(",") if k.strip()][:5]
        
        print("Step 1: Waiting for API quota reset (30s)...")
        time.sleep(30)
        
        # Step 2: Search and Scrape
        print("Step 2: Technical Search & Deep Scraping...")
        all_raw_news = []
        if search_keywords:
            # Standard search
            raw_tech = search_technical_news(search_keywords, max_results=10)
            all_raw_news.extend(raw_tech)
            
            # Apify search
            apify_posts = search_x_apify(search_keywords[:2])
            if apify_posts:
                all_raw_news.extend(apify_posts)
            else:
                manual_data = load_manual_apify_data("data/manual_import.json")
                if manual_data:
                    all_raw_news.extend(manual_data)
                else:
                    social_kws = [f"{k} site:x.com OR site:facebook.com" for k in search_keywords[:2]]
                    all_raw_news.extend(search_technical_news(social_kws, max_results=5))

            # ScrapeGraphAI Enhancement
            top_tech_leads = [item for item in all_raw_news if item.get('source') != 'Apify'][:3]
            for lead in top_tech_leads:
                print(f"    Pipeline: Deep scraping lead: {lead['title']}...")
                enhance_prompt = f"Analyze article and extract technical title/summary related to: {', '.join(search_keywords)}"
                deep_res = fetch_with_scrapegraph(lead['link'], prompt=enhance_prompt)
                if deep_res and isinstance(deep_res, dict) and deep_res.get('title'):
                    lead['summary'] = deep_res.get('summary', lead['summary'])

        # Step 3: Fetch RSS, Reddit, FB, X
        print("Step 3: Fetching RSS, Reddit, Social Media...")
        for name, url in Config.RSS_FEEDS.items():
            all_raw_news.extend(fetch_rss_news(url))
        
        all_raw_news.extend(fetch_reddit_ml_news())
        
        # Facebook Group Fetcher
        if Config.APIFY_API_TOKENS:
            all_raw_news.extend(fetch_facebook_groups_apify(keywords=search_keywords))
        
        # Specialized X Profile Fetcher
        all_raw_news.extend(fetch_x_profiles_apify())
        
        # Step 3.5: Deduplication
        unique_news = []
        duplicate_count = 0
        for item in all_raw_news:
            if not self.data_manager.is_duplicate(item):
                unique_news.append(item)
                self.data_manager.add_to_seen(item)
            else:
                duplicate_count += 1
        
        print(f"  Pipeline: Removed {duplicate_count} duplicates. {len(unique_news)} unique remaining.")

        # Step 3.6: Order & Filter
        social_items = [i for i in unique_news if "Apify" in i.get("source", "")]
        arxiv_items = [i for i in unique_news if "arxiv" in i.get("source", "").lower()][:10]
        other_items = [i for i in unique_news if i not in social_items and i not in arxiv_items]
        
        diverse_news = social_items + arxiv_items + other_items
        filtered_news = self.filter_relevance(diverse_news, search_keywords)[:20]

        # Step 4: Summarize
        print("Step 4: AI Summarization (Vietnamese)...")
        final_reports = summarize_news(filtered_news, keywords)
        
        # Fallback if AI summarization fails
        if not final_reports and filtered_news:
            for raw in filtered_news[:5]:
                final_reports.append({
                    "title": raw['title'],
                    "link": raw['link'],
                    "source": raw.get('source', 'Unknown'),
                    "summary_vn": raw.get('summary', '')[:300] + "...",
                    "date": raw.get('date', datetime.now().isoformat())
                })

        # Step 4.2: Teams Notification
        try:
            official_labs = ["meta", "qwen", "mistral", "nvidia", "openai", "deepmind", "anthropic", "deepseek", "arxiv"]
            priority_items = sorted(final_reports, key=lambda x: 0 if any(lab in x.get("source", "").lower() or lab in x.get("link", "").lower() for lab in official_labs) else 1)
            send_teams_notification(priority_items)
        except Exception as e:
            print(f"  Warning: Teams notification failed: {e}")

        # Step 4.5: Refine Keywords
        actual_keywords = keywords
        if final_reports:
            context = "\n".join([f"- {r['title']}: {r['summary_vn'][:200]}" for r in final_reports[:15]])
            prompt = f"Extract 10 TECHNICAL keywords from these news summaries.\n\nCONTEXT:\n{context}\n\nOUTPUT FORMAT:\nEN: [kw1, kw2, ...]\nVN: [kw1, kw2, ...]"
            try:
                ai_res = get_rotator().generate_content(prompt)
                if not any(bs in ai_res.upper() for bs in ["ERROR", "EXHAUSTED", "FAILED"]):
                    actual_keywords = ai_res
            except Exception as e:
                print(f"  Warning: Keyword extraction failed: {e}")

        # Step 5: Save
        self.output_data = {
            "timestamp": datetime.now().isoformat(),
            "keywords": actual_keywords,
            "reports": final_reports,
            "debug_stats": {
                "raw_total": len(all_raw_news),
                "duplicates": duplicate_count,
                "final": len(final_reports)
            }
        }
        self.data_manager.save_run_results(self.output_data)
        
        return self.output_data
