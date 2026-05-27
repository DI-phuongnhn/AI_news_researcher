"""
Research Pipeline Orchestrator.

This module coordinates the end-to-end flow of the AI News Research Agent.
It handles keyword discovery, prioritized multi-source fetching, 
deduplication, relevance filtering, and coordination with the 
summarization and notification systems.
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
from src.utils.text_utils import normalize_text, parse_flexible_date, is_latin_only
from src.utils.notifier import send_teams_notification

class ResearchPipeline:
    """
    Main Orchestrator for the AI News Research process.
    
    This class manages the internal state including deduplication history
    and coordinates the sequence of execution phases.
    """
    
    def __init__(self):
        """Initialize data manager and local state containers."""
        self.data_manager = DataManager()
        self.output_data = {}
        
    def filter_relevance(self, news_list, search_keywords, known_models=None):
        """
        Applies strict relevance and noise filtering.
        
        Uses keyword matching, regex word boundaries, and source-based bypassing 
        to separate high-signal technical news from social media 'noise' or 
        unrelated discussions.
        
        Args:
            news_list (list): Raw news dictionaries to filter.
            search_keywords (list): Current trending keywords to match against.
            known_models (list): List of known AI model names to prioritize.
            
        Returns:
            list: Filtered and validated news items.
        """
        import re
        if not search_keywords:
            return news_list
            
        filtered = []
        
        # Noise patterns commonly found in social media or unrelated Vietnamese tech groups.
        excluded_patterns = [
            r"\boscar\b", r"\bhoat hinh\b", r"\bstopmotion\b", r"\banimation\b",
            r"\bban hang\b", r"\bgom don\b", r"\bquang cao\b", r"\bkhoa hoc\b",
            r"\bmovie\b", r"\bcinema\b", r"\bphim\b",
            r"co duoc khong", r"ai co y tuong", r"day lam", r"tim nguoi", r"can tu van",
            r"hoi dap", r"giup em", r"giup minh", r"ask", r"hoi",
            r"bam sign in", r"khong duoc", r"khong phan hoi", r"quota", r"tinh trang", 
            r"co ai bi", r"ai gap", r"loi roi", r"nho ho tro", r"chao mng", r"moi nguoi oi"
        ]
        
        # High-signal keywords for AI applications and agentic workflows.
        application_keywords = [
            "agent", "workflow", "automation", "solo agency", "mcp", "case study", 
            "use case", "business impact", "practical ai", "real-world", "browser-use", "orchestration"
        ]
        
        norm_keywords = [normalize_text(kw) for kw in search_keywords if normalize_text(kw)]
        norm_app_keywords = [normalize_text(kw) for kw in application_keywords]
        
        for item in news_list:
            title = item.get("title", "")
            summary = item.get("summary", "")
            text_to_check = normalize_text(f"{title} {summary}")
            
            # --- Block: Language Guard ---
            # Filter out entries with significant non-Latin script (noise).
            if not is_latin_only(title) or not is_latin_only(summary):
                continue

            # --- Block: Noise Check ---
            is_noise = False
            for pattern in excluded_patterns:
                if re.search(pattern, text_to_check):
                    is_noise = True
                    break
            if is_noise:
                continue

            # --- Block: Relevance Check ---
            is_relevant = False
            # 1. Check Application/Workflow keywords (High Signal)
            for ak in norm_app_keywords:
                if ak in text_to_check:
                    is_relevant = True
                    item["is_application"] = True
                    break

            # 2. Check Model names
            if not is_relevant and known_models:
                for km in known_models:
                    if re.search(r'\b' + re.escape(normalize_text(km)) + r'\b', text_to_check, re.IGNORECASE):
                        is_relevant = True
                        break

            # 3. Check Trending keywords
            if not is_relevant:
                for kw in norm_keywords:
                    if kw in text_to_check:
                        is_relevant = True
                        break
            
            # --- Block: Source-based Bypass ---
            # Some sources are inherently high-signal (official labs, arxiv).
            source_lower = item.get("source", "").lower()
            if not is_relevant:
                # 1. Official Lab Blogs or ArXiv
                if "arxiv" in source_lower or "scrapegraph" in source_lower:
                    is_relevant = True
                
                # 2. Trusted Social Profiles (REMOVED BYPASS: Now forcing AI relevance check for profiles)
                # if "x profile" in source_lower:
                #     is_relevant = True

                # 3. Known Official Keyword Match in source/link
                official_labs = ["openai", "anthropic", "google", "meta", "nvidia", "deepseek", "mistral", "qwen", "huggingface"]
                if any(lab in source_lower or lab in item.get("link", "").lower() for lab in official_labs):
                    is_relevant = True
                
            if is_relevant:
                filtered.append(item)
                
        print(f"  Filtering: Kept {len(filtered)} out of {len(news_list)} items.")
        return filtered

    def run(self, preview_mode: bool = False):
        """
        End-to-End Pipeline Execution.
        
        Coordinates the workflow: 
        1. Initialize state.
        2. Discover keywords.
        3. Prioritized fetching (Official first, Apify fallback).
        4. Processing (Deduplication/Freshness).
        5. Summarization.
        6. Notification (Skipped if preview_mode is True).
        7. Persistence.
        """
        # Step 0: Initial State (Load history and models)
        active_models, all_models = self._initial_state()
        
        # Step 1: Discover Keywords (Trending technical topics)
        keywords, search_keywords = self._discover_keywords()
        
        # Step 2: Fetch Official/Technical Sources (Primary Signals)
        # This includes ScrapeGraph, RSS, and Reddit. High-signal, low-noise.
        print("Step 2: Fetching from Official & Technical sources (ScraperAI, RSS, Reddit)...")
        official_raw_news = self._fetch_official_sources(search_keywords, active_models)
        
        # --- Block: Intelligence Gate (REMOVED) ---
        # We check if Phase 1 found any TRULY NEW news.
        unique_official, _, _ = self._process_news(official_raw_news, search_keywords, all_models, dry_run=True)
        
        # Always run Apify as requested
        print("  Result: Fetching Step 3: Apify Social Fallback (Always ON)...")
        social_raw_news = self._fetch_social_fallback(search_keywords, active_models)
        
        # Prepend social_raw_news so that Apify sources are evaluated FIRST during deduplication.
        # If there's a duplicate between Apify and Official, the Apify one will be kept.
        all_raw_news = social_raw_news + official_raw_news
        
        # --- Block: Final Processing ---
        # Full run (dry_run=False) which updates 'seen' history for url deduplication.
        unique_news, filtered_news, duplicate_count = self._process_news(all_raw_news, search_keywords, all_models)
        
        # --- Block: AI Summarization ---
        # We perform the summarization first.
        final_reports = self._summarize(filtered_news, keywords, all_models)
        
        # --- Block: Conditional Notification ---
        # TEMPORARILY DISABLED as per user request: Skipping Teams notification.
        # Run without --preview would normally notify, but we bypass for now.
        if False and not preview_mode:
            self._notify(final_reports)
        else:
            print("  Pipeline: Teams notification is TEMPORARILY DISABLED.")
        
        # Step 4.5: Refine Keywords/Models (Feedback loop for next run)
        actual_keywords = self._refine_keywords(final_reports, keywords)

        # Step 5: Save (Local persistence)
        return self._save_results(actual_keywords, final_reports, all_raw_news, duplicate_count)

    def _initial_state(self):
        """Step 0: Load data and model names from local files."""
        self.data_manager.load_history()
        known_models_dict = self.data_manager.load_model_names()
        active_models = known_models_dict.get("active", [])
        all_models = active_models + known_models_dict.get("legacy", [])
        return active_models, all_models

    def _discover_keywords(self):
        """Step 1: Trending technical keyword discovery using AI."""
        print("Step 1: Discovering trending AI technical keywords...")
        keywords = get_trending_keywords()
        search_keywords = []
        if "EN:" in keywords:
            en_part = keywords.split("EN:")[1].split("\n\n")[0]
            en_clean = en_part.replace('[', '').replace(']', '')
            search_keywords = [k.strip() for k in en_clean.split(",") if k.strip()][:5]
        
        # Rate limit safety delay for external technical search engines.
        print("Step 1: Waiting for API quota reset (30s)...")
        time.sleep(30)
        return keywords, search_keywords

    def _fetch_official_sources(self, search_keywords, active_models):
        """
        Phase 1 Fetching: Official blogs, RSS, and technical forums.
        
        These are prioritized because they contain technical documentation 
        and first-party announcements.
        """
        all_raw_news = []
        
        # --- Block: Active Model Tracking (Priority 1) ---
        # We prioritize specific models over generic technical keywords.
        if active_models:
            print(f"  Batching {len(active_models)} active models for priority search...")
            batched_queries = []
            for i_m in range(0, len(active_models), 10):
                chunk = active_models[i_m:i_m+10]
                query = "(" + " OR ".join([f'"{k}"' for k in chunk]) + ")"
                batched_queries.append(query)
            all_raw_news.extend(search_technical_news(batched_queries, max_results=10))

        # --- Block: Technical Search Discovery (Priority 2) ---
        if search_keywords:
            all_raw_news.extend(search_technical_news(search_keywords, max_results=5))

        # --- Block: Lead Enhancement ---
        # Enhance the first few leads using ScrapeGraphAI for deeper technical summaries.
        top_tech_leads = [item for item in all_raw_news if item.get('source') != 'Apify'][:3]
        for lead in top_tech_leads:
            enhance_prompt = f"Analyze article and extract technical title/summary related to AI/ML context."
            try:
                deep_res = fetch_with_scrapegraph(lead['link'], prompt=enhance_prompt)
                if deep_res and isinstance(deep_res, dict) and deep_res.get('title'):
                    lead['summary'] = deep_res.get('summary', lead['summary'])
            except: pass

        # --- Block: Deep Blog Scraping ---
        # Rotate through official lab blogs (OpenAI, Anthropic, etc.) using ScrapeGraphAI.
        if hasattr(Config, "SCRAPEGRAPH_TARGETS") and Config.SCRAPEGRAPH_TARGETS:
            num_targets = getattr(Config, "MAX_SCRAPE_TARGETS_PER_RUN", 3)
            hf_url = "https://huggingface.co/blog"
            other_targets = [t for t in Config.SCRAPEGRAPH_TARGETS if t != hf_url]
            targets = [hf_url] if hf_url in Config.SCRAPEGRAPH_TARGETS else []
            num_needed = num_targets - len(targets)
            if num_needed > 0 and other_targets:
                import random
                targets.extend(random.sample(other_targets, min(len(other_targets), num_needed)))
                
            print(f"  ScrapeGraphAI: Scraping {len(targets)} technical blogs...")
            for blog_url in targets:
                try:
                    blog_news = fetch_technical_blog_posts(blog_url)
                    if blog_news:
                        all_raw_news.extend(blog_news)
                except Exception as e:
                    print(f"    Warning: ScrapeGraph failed for {blog_url}: {e}")

        # --- Block: Static Feeds ---
        # Fast, low-resource RSS and Reddit fetching.
        for name, url in Config.RSS_FEEDS.items():
            all_raw_news.extend(fetch_rss_news(url))
        all_raw_news.extend(fetch_reddit_ml_news())
        
        return all_raw_news

    def _fetch_social_fallback(self, search_keywords, active_models):
        """
        Phase 2 Fetching: Social Fallback (Apify).
        
        Executed only if Phase 1 found no new items. Focuses on social 
        sentiment on X/Twitter.
        """
        social_news = []
        
        # --- Block: X Search (DISABLED to save Apify Quota) ---
        # if search_keywords:
        #     from src.fetcher.apify_fetcher import search_x_apify
        #     apify_posts = search_x_apify(search_keywords[:2])
        #     if apify_posts:
        #         social_news.extend(apify_posts)
        
        # --- Block: ScrapeGraphAI Fallback ---
        print("  Using ScrapeGraphAI fallback for technical leads (X Search disabled)...")
        fallback_targets = ["https://simonwillison.net/", "https://arxiv.org/list/cs.AI/recent"]
        if hasattr(Config, "SCRAPEGRAPH_TARGETS") and Config.SCRAPEGRAPH_TARGETS:
            fallback_targets = Config.SCRAPEGRAPH_TARGETS[:2]
        for url in fallback_targets:
            try:
                social_news.extend(fetch_technical_blog_posts(url, max_items=2))
            except: pass

        # --- Block: Specialized X Tracking (DISABLED to save Apify Quota) ---
        # if active_models:
        #     from src.fetcher.apify_fetcher import search_x_apify
        #     batched_queries = []
        #     for i_m in range(0, len(active_models), 10):
        #         chunk = active_models[i_m:i_m+10]
        #         query = "(" + " OR ".join([f'"{k}"' for k in chunk]) + ")"
        #         batched_queries.append(query)
        #     apify_model_posts = search_x_apify(batched_queries, max_items=5)
        #     if apify_model_posts:
        #         social_news.extend(apify_model_posts)

        # --- Block: Global Context ---
        # Fetch ONLY from specific influential X profiles.
        if Config.APIFY_API_TOKENS:
            from src.fetcher.apify_fetcher import fetch_x_profiles_apify
            # social_news.extend(fetch_facebook_posts_apify()) # DISABLED
            social_news.extend(fetch_x_profiles_apify())
        
        return social_news

    def _process_news(self, all_raw_news, search_keywords, all_models, dry_run=False):
        """
        Step 3.5 & 3.6: Deduplication, Ordering, and Relevance Filtering.
        
        Args:
            all_raw_news (list): Merged list of news items.
            dry_run (bool): If True, detects duplicates but DOES NOT update the seen history.
        """
        # --- Block: Freshness Gate ---
        # Runs before deduplication so stale items never enter the pipeline metrics.
        fresh_news, stale_count, undated_count = self._filter_recent_news(all_raw_news)
        if not dry_run:
            print(
                f"  Pipeline: Removed {stale_count} stale items and {undated_count} items without a trusted date. "
                f"{len(fresh_news)} candidates remain."
            )

        # --- Block: Deduplication ---
        unique_news = []
        duplicate_count = 0
        for item in fresh_news:
            if not self.data_manager.is_duplicate(item):
                unique_news.append(item)
                if not dry_run:
                    self.data_manager.add_to_seen(item)
            else:
                duplicate_count += 1
        
        if not dry_run:
            print(f"  Pipeline: Removed {duplicate_count} duplicates. {len(unique_news)} unique remaining.")

        # --- Block: Diversity Ranking & Final Selection ---
        # Priority 1: AI Application news (manually boosted)
        app_items = [i for i in unique_news if i.get("is_application")]
        
        # Priority 2: Technical Blogs (ScrapeGraph) & ArXiv
        tech_leads = [i for i in unique_news if ("scrapegraph" in i.get("source", "").lower() or "arxiv" in i.get("source", "").lower()) and i not in app_items]
        
        # Priority 3: General Technical Search & Others
        other_items = [i for i in unique_news if i not in app_items and i not in tech_leads]
        
        # Re-concatenate in order of interest
        diverse_news = app_items + tech_leads + other_items
        
        # --- Block: Per-Query Diversity Filter ---
        # We prevent a single search query (like 'LLM') from dominating the top 20.
        final_filtered = []
        query_counts = {}
        for item in diverse_news:
            source = item.get("source", "")
            # Only apply limit to search-based sources
            if source.startswith("Search:"):
                query_counts[source] = query_counts.get(source, 0) + 1
                if query_counts[source] > 3: # Max 3 items per search query
                    continue
            
            final_filtered.append(item)
            if len(final_filtered) >= 20:
                break
        
        filtered_news = self.filter_relevance(final_filtered, search_keywords, all_models)
        return unique_news, filtered_news, duplicate_count

    def _filter_recent_news(self, news_items):
        """Validates publication dates against the Config.MAX_NEWS_AGE_DAYS window."""
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

            # Ensure both datetimes are offset-naive for subtraction.
            if parsed_date.tzinfo is not None:
                parsed_date = parsed_date.replace(tzinfo=None)
                
            age_days = (now - parsed_date).total_seconds() / 86400
            if age_days < 0 or age_days > max_age_days:
                stale_count += 1
                continue

            # --- Block: Safety Filter (Month Check) ---
            # Extra safety: If the title explicitly mentions a different month/year 
            # from several months ago, reject it even if the metadata is weird.
            current_month_year = now.strftime("%Y")
            bad_months_en = ["January", "February", "March", "Jan", "Feb", "Mar"]
            bad_months_vn = ["Tháng 1", "Tháng 2", "Tháng 3"]
            
            title_summary = (item.get("title", "") + " " + item.get("summary", "")).lower()
            # If current month is April, and text mentions Jan/Feb/Mar 2026, it's likely stale.
            if any(m.lower() in title_summary for m in bad_months_en + bad_months_vn):
                if current_month_year in title_summary:
                    stale_count += 1
                    continue

            normalized_item = dict(item)
            normalized_item["date"] = parsed_date.isoformat()
            fresh_items.append(normalized_item)

        return fresh_items, stale_count, undated_count

    def _summarize(self, filtered_news, keywords, all_models):
        """Step 4: AI Summarization (Vietnamese Translation)."""
        print("Step 4: AI Summarization (Vietnamese Translation)...")
        final_reports = summarize_news(filtered_news, keywords, all_models)
        
        # Fallback if summarization fails for all items.
        if not final_reports and filtered_news:
            for raw in filtered_news[:5]:
                final_reports.append({
                    "title": raw['title'], "link": raw['link'], "source": raw.get('source', 'Unknown'),
                    "summary_vn": raw.get('summary', '')[:300] + "...",
                    "date": raw.get('date', datetime.now().isoformat())
                })
        return final_reports

    def _notify(self, final_reports):
        """Step 4.1: MS Teams notification."""
        if not final_reports:
            print("  Pipeline: No news to notify.")
            return

        print("Step 4.1: Sending Teams Notification...")
        # --- Block: Priority Notification ---
        # Send summarized news to Teams. Sort by lab official status first.
        try:
            official_labs = ["meta", "qwen", "mistral", "nvidia", "openai", "deepmind", "anthropic", "deepseek", "arxiv"]
            priority_items = sorted(final_reports, key=lambda x: 0 if any(lab in x.get("source", "").lower() or lab in x.get("link", "").lower() for lab in official_labs) else 1)
            send_teams_notification(priority_items)
        except Exception as e:
            print(f"  Warning: Teams notification failed: {e}")

    def _refine_keywords(self, final_reports, keywords):
        """Step 4.5: Analyze current news to extract keywords for the NEXT run."""
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
                    
                    # Update local model knowledge if AI found new launches.
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
        """Step 5: Persist metrics and data for the web dashboard."""
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
