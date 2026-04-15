"""
Research Pipeline Orchestrator.
Coordinates the end-to-end flow from discovery to notification.
"""

import time
import random
from datetime import datetime
from src.config import Config
from src.fetcher.keyword_discovery import get_trending_keywords
from src.fetcher.rss_fetcher import fetch_rss_news
from src.fetcher.reddit_fetcher import fetch_reddit_ml_news
from src.fetcher.search_fetcher import search_technical_news
from src.fetcher.apify_fetcher import (
    search_x_apify, 
    fetch_facebook_posts_apify, 
    fetch_x_profiles_apify
)
from src.fetcher.scrapegraph_fetcher import fetch_with_scrapegraph, fetch_technical_blog_posts
from src.agent.summarizer import summarize_news
from src.agent.model_rotator import get_rotator
from src.utils.data_manager import DataManager
from src.utils.text_utils import normalize_text, parse_flexible_date
from src.utils.notifier import send_teams_notification

class ResearchPipeline:
    """
    Main orchestrator for the AI News Research process.
    """
    
    def __init__(self):
        self.data_manager = DataManager()
        self.output_data = {}
        
    def filter_relevance(self, news_list, search_keywords, known_models=None):
        """
        Stricter pre-AI filter that uses Regex word boundaries to avoid false matches.
        """
        import re
        if not search_keywords:
            return news_list
            
        filtered = []
        excluded_patterns = [
            r"\boscar\b", r"\bhoat hinh\b", r"\bstopmotion\b", r"\banimation\b",
            r"\bban hang\b", r"\bgom don\b", r"\bquang cao\b", r"\bkhoa hoc\b",
            r"\bmovie\b", r"\bcinema\b", r"\bphim\b",
            r"co duoc khong", r"ai co y tuong", r"day lam", r"tim nguoi", r"can tu van",
            r"hoi dap", r"giup em", r"giup minh", r"ask", r"hoi",
            r"bam sign in", r"khong duoc", r"khong phan hoi", r"quota", r"tinh trang", 
            r"co ai bi", r"ai gap", r"loi roi", r"nho ho tro", r"chao mng", r"moi nguoi oi"
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
            
            if not is_relevant and known_models:
                for km in known_models:
                    if re.search(r'\b' + re.escape(normalize_text(km)) + r'\b', text_to_check, re.IGNORECASE):
                        is_relevant = True
                        break
            
            # Source-based bypass for Official Leads and Trusted Social Profiles
            source_lower = item.get("source", "").lower()
            if not is_relevant:
                # 1. Official Lab Blogs (ScrapeGraph) or ArXiv
                if "arxiv" in source_lower or "scrapegraph" in source_lower:
                    is_relevant = True
                
                # 2. Trusted Social Profiles (X Profile handles)
                if "x profile" in source_lower:
                    is_relevant = True

                # 3. Known Official Keyword Match
                official_labs = ["openai", "anthropic", "google", "meta", "nvidia", "deepseek", "mistral", "qwen", "huggingface"]
                if any(lab in source_lower or lab in item.get("link", "").lower() for lab in official_labs):
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
        active_models, all_models = self._initial_state()
        
        # Step 1: Discover Keywords
        keywords, search_keywords = self._discover_keywords()
        
        # Step 2 & 3: Fetching
        all_raw_news = self._fetch_all_sources(search_keywords, active_models)
        
        # Deduplication and Filtering
        unique_news, filtered_news, duplicate_count = self._process_news(all_raw_news, search_keywords, all_models)

        # Step 4: Summarize & Notify
        final_reports = self._summarize_and_notify(filtered_news, keywords, all_models)
        
        # Step 4.5: Refine Keywords/Models
        actual_keywords = self._refine_keywords(final_reports, keywords)

        # Step 5: Save
        return self._save_results(actual_keywords, final_reports, all_raw_news, duplicate_count)

    def _initial_state(self):
        """Step 0: Load data and model names."""
        self.data_manager.load_history()
        known_models_dict = self.data_manager.load_model_names()
        active_models = known_models_dict.get("active", [])
        all_models = active_models + known_models_dict.get("legacy", [])
        return active_models, all_models

    def _discover_keywords(self):
        """Step 1: Trending keyword discovery."""
        print("Step 1: Discovering trending AI technical keywords...")
        keywords = get_trending_keywords()
        search_keywords = []
        if "EN:" in keywords:
            en_part = keywords.split("EN:")[1].split("\n\n")[0]
            en_clean = en_part.replace('[', '').replace(']', '')
            search_keywords = [k.strip() for k in en_clean.split(",") if k.strip()][:5]
        
        print("Step 1: Waiting for API quota reset (30s)...")
        time.sleep(30)
        return keywords, search_keywords

    def _fetch_all_sources(self, search_keywords, active_models):
        """Step 2 & 3: Aggregate news from all integrated sources."""
        print("Step 2 & 3: Fetching from all sources...")
        all_raw_news = []
        
        # 2a. Search-based discovery
        if search_keywords:
            all_raw_news.extend(search_technical_news(search_keywords, max_results=10))
            apify_posts = search_x_apify(search_keywords[:2])
            if apify_posts:
                all_raw_news.extend(apify_posts)
            else:
                # Scraper AI Fallback: Use ScrapeGraph to get news from high-signal sites
                # instead of manual import.
                print("  Apify failed. Using ScrapeGraphAI fallback for technical leads...")
                # We reuse the first few targets from config if available, or use fixed ones
                fallback_targets = ["https://simonwillison.net/", "https://arxiv.org/list/cs.AI/recent"]
                if hasattr(Config, "SCRAPEGRAPH_TARGETS") and Config.SCRAPEGRAPH_TARGETS:
                    fallback_targets = Config.SCRAPEGRAPH_TARGETS[:2]
                
                for url in fallback_targets:
                    try:
                        all_raw_news.extend(fetch_technical_blog_posts(url, max_items=2))
                    except Exception as e:
                        print(f"    Fallback ScrapeGraph failed for {url}: {e}")
                
                # Second fallback: Search-based X discovery via Search Engine
                social_kws = [f"{k} site:x.com" for k in search_keywords[:2]]
                all_raw_news.extend(search_technical_news(social_kws, max_results=5))

        # 2b. Active Model Trackers (OR-batching to save quota)
        if active_models:
            print(f"  Batching {len(active_models)} active models for quota-efficient search...")
            batched_queries = []
            for i in range(0, len(active_models), 10):
                chunk = active_models[i:i+10]
                query = "(" + " OR ".join([f'"{k}"' for k in chunk]) + ")"
                batched_queries.append(query)

            all_raw_news.extend(search_technical_news(batched_queries, max_results=5))
            apify_model_posts = search_x_apify(batched_queries, max_items=5)
            if apify_model_posts:
                all_raw_news.extend(apify_model_posts)

        # 2c. ScrapeGraph Lead Enhancement
        top_tech_leads = [item for item in all_raw_news if item.get('source') != 'Apify'][:3]
        for lead in top_tech_leads:
            enhance_prompt = f"Analyze article and extract technical title/summary related to AI/ML context."
            deep_res = fetch_with_scrapegraph(lead['link'], prompt=enhance_prompt)
            if deep_res and isinstance(deep_res, dict) and deep_res.get('title'):
                lead['summary'] = deep_res.get('summary', lead['summary'])

        # 2d. SCRAPEGRAPH Deep Blog Scraping (Rotating targets to save quota)
        if hasattr(Config, "SCRAPEGRAPH_TARGETS") and Config.SCRAPEGRAPH_TARGETS:
            num_targets = getattr(Config, "MAX_SCRAPE_TARGETS_PER_RUN", 3)
            
            # Prioritize Hugging Face Blog as requested (it aggregates many others)
            hf_url = "https://huggingface.co/blog"
            other_targets = [t for t in Config.SCRAPEGRAPH_TARGETS if t != hf_url]
            
            targets = [hf_url] if hf_url in Config.SCRAPEGRAPH_TARGETS else []
            num_needed = num_targets - len(targets)
            
            if num_needed > 0 and other_targets:
                targets.extend(random.sample(other_targets, min(len(other_targets), num_needed)))
                
            print(f"  ScrapeGraphAI: Scraping {len(targets)} technical blogs (HF Priority: YES)...")
            for blog_url in targets:
                try:
                    blog_news = fetch_technical_blog_posts(blog_url)
                    if blog_news:
                        all_raw_news.extend(blog_news)
                except Exception as e:
                    print(f"    Warning: ScrapeGraph failed for {blog_url}: {e}")

        # 3. Static Sources (RSS, Reddit, Social Profiles)
        for name, url in Config.RSS_FEEDS.items():
            all_raw_news.extend(fetch_rss_news(url))
        
        all_raw_news.extend(fetch_reddit_ml_news())
        if Config.APIFY_API_TOKENS:
            all_raw_news.extend(fetch_facebook_posts_apify())
        all_raw_news.extend(fetch_x_profiles_apify())
        
        return all_raw_news

    def _process_news(self, all_raw_news, search_keywords, all_models):
        """Step 3.5 & 3.6: Deduplication, Ordering, and Relevance Filtering."""
        # Freshness gate runs before deduplication so stale items never enter the pipeline.
        fresh_news, stale_count, undated_count = self._filter_recent_news(all_raw_news)
        print(
            f"  Pipeline: Removed {stale_count} stale items and {undated_count} items without a trusted date. "
            f"{len(fresh_news)} candidates remain."
        )

        # Deduplication
        unique_news = []
        duplicate_count = 0
        for item in fresh_news:
            if not self.data_manager.is_duplicate(item):
                unique_news.append(item)
                self.data_manager.add_to_seen(item)
            else:
                duplicate_count += 1
        print(f"  Pipeline: Removed {duplicate_count} duplicates. {len(unique_news)} unique remaining.")

        # Diverse Filtering
        # Diverse Filtering and Re-ordering
        # Priority 1: Technical Blogs (ScrapeGraph) & ArXiv
        tech_leads = [i for i in unique_news if "scrapegraph" in i.get("source", "").lower() or "arxiv" in i.get("source", "").lower()]
        
        # Priority 2: General Technical Search
        search_leads = [i for i in unique_news if "search" in i.get("source", "").lower() and i not in tech_leads]
        
        # Priority 3: Social Media (Apify) - Limited to ensure variety
        social_items = [i for i in unique_news if "apify" in i.get("source", "").lower()]
        
        # Priority 4: Everything else (RSS, Reddit)
        other_items = [i for i in unique_news if i not in tech_leads and i not in search_leads and i not in social_items]
        
        # Re-concatenate in order of "Technical Depth"
        diverse_news = tech_leads + search_leads + other_items + social_items
        filtered_news = self.filter_relevance(diverse_news, search_keywords, all_models)[:20]
        return unique_news, filtered_news, duplicate_count

    def _filter_recent_news(self, news_items):
        """Keep only items with a trusted date inside the configured freshness window."""
        max_age_days = getattr(Config, "MAX_NEWS_AGE_DAYS", 4)
        now = datetime.now()
        fresh_items = []
        stale_count = 0
        undated_count = 0

        for item in news_items:
            parsed_date = parse_flexible_date(item.get("date"))
            if parsed_date is None:
                undated_count += 1
                continue

            age_days = (now - parsed_date).total_seconds() / 86400
            if age_days < 0 or age_days > max_age_days:
                stale_count += 1
                continue

            normalized_item = dict(item)
            normalized_item["date"] = parsed_date.isoformat()
            fresh_items.append(normalized_item)

        return fresh_items, stale_count, undated_count

    def _summarize_and_notify(self, filtered_news, keywords, all_models):
        """Step 4 & 4.2: AI Summarization and Teams Ping."""
        print("Step 4: AI Summarization (Vietnamese)...")
        final_reports = summarize_news(filtered_news, keywords, all_models)
        
        if not final_reports and filtered_news:
            for raw in filtered_news[:5]:
                final_reports.append({
                    "title": raw['title'], "link": raw['link'], "source": raw.get('source', 'Unknown'),
                    "summary_vn": raw.get('summary', '')[:300] + "...",
                    "date": raw.get('date', datetime.now().isoformat())
                })

        try:
            official_labs = ["meta", "qwen", "mistral", "nvidia", "openai", "deepmind", "anthropic", "deepseek", "arxiv"]
            priority_items = sorted(final_reports, key=lambda x: 0 if any(lab in x.get("source", "").lower() or lab in x.get("link", "").lower() for lab in official_labs) else 1)
            send_teams_notification(priority_items)
        except Exception as e:
            print(f"  Warning: Teams notification failed: {e}")
            
        return final_reports

    def _refine_keywords(self, final_reports, keywords):
        """Step 4.5: Extract trending keywords and new model names."""
        actual_keywords = keywords
        if final_reports:
            context = "\n".join([f"- {r['title']}: {r['summary_vn'][:200]}" for r in final_reports[:15]])
            prompt = (
                f"Extract 10 TECHNICAL keywords AND explicitly a list of any new AI MODEL NAMES you see in these news summaries.\n\n"
                f"CONTEXT:\n{context}\n\nOUTPUT FORMAT:\nEN: [kw1, kw2, ...]\nVN: [kw1, kw2, ...]\nMODELS: [model1, model2, ...]"
            )
            try:
                ai_res = get_rotator().generate_content(prompt)
                if not any(bs in ai_res.upper() for bs in ["ERROR", "EXHAUSTED", "FAILED"]):
                    actual_keywords = ai_res
                    if "MODELS:" in ai_res:
                        models_str = ai_res.split("MODELS:")[1].strip().split("\n")[0]
                        models_str_clean = models_str.replace('[', '').replace(']', '')
                        models_list = [m.strip() for m in models_str_clean.split(',') if m.strip()]
                        if models_list:
                            self.data_manager.save_model_names(models_list)
            except Exception as e:
                print(f"  Warning: Keyword extraction failed: {e}")
        return actual_keywords

    def _save_results(self, actual_keywords, final_reports, all_raw_news, duplicate_count):
        """Step 5: Persist run metrics and report data."""
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
