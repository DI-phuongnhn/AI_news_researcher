from scrapegraphai.graphs import SmartScraperGraph
from src.config import Config

def fetch_with_scrapegraph(url, prompt=None):
    """
    Scrapes a target technical URL using ScrapeGraphAI's SmartScraperGraph.
    With multiple key rotation for robustness.
    """
    if not prompt:
        prompt = "Extract the main technical points, title, and a summary of this article."

    keys = Config.GEMINI_API_KEYS
    if not keys:
        print("Error: No GEMINI_API_KEYS found in Config.")
        return None

    for api_key in keys:
        for model_name in Config.GEMINI_MODELS_FALLBACK:
            full_model_name = f"google_genai/{model_name}"
            
            graph_config = {
                "llm": {
                    "api_key": api_key,
                    "model": full_model_name,
                },
                "verbose": False,
                "headless": True
            }

            try:
                print(f"  ScrapeGraphAI: Trying {model_name}...")
                smart_scraper_graph = SmartScraperGraph(
                    prompt=prompt,
                    source=url,
                    config=graph_config
                )
                
                result = smart_scraper_graph.run()
                if result:
                    return result
            except Exception as e:
                err_msg = str(e).upper()
                if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg or "TOKEN" in err_msg:
                    print(f"  {model_name} exhausted or rate limited. Waiting 10s then rotating...")
                    import time
                    time.sleep(10)
                    continue
                print(f"ScrapeGraphAI error for {url} with {model_name}: {e}")
                
    return None
            
def fetch_technical_blog_posts(url, max_items=3):
    """
    Specifically designed for ScrapeGraphAI to extract a LIST of recent technical 
    news items from a blog landing page.
    """
    prompt = f"""
    Find the latest {max_items} technical AI/ML blog posts or model releases from this page.
    STRICT TECHNICAL FILTER: ONLY include articles about model architectures, new LLM weights, 
    training methods, or deep-dive optimizations. Skip 'Company News', 'Culture', or 'Hiring'.
    
    For each valid item, extract:
    - 'title': The technical headline.
    - 'link': The absolute URL to the article.
    - 'summary': A 2-sentence technical summary in English.
    - 'date': The publication date as it appears on the page. Use ISO-8601 when explicit.

    IMPORTANT: If a post does not have a clear publication date, set 'date' to null.
    Format: Return a JSON list of objects.
    """
    
    raw_res = fetch_with_scrapegraph(url, prompt=prompt)
    if not raw_res:
        return []
        
    # Standardize result format (ScrapeGraph sometimes returns nested dicts or lists)
    items = []
    if isinstance(raw_res, list):
        items = raw_res
    elif isinstance(raw_res, dict):
        # Look for the first list value in the dict
        for val in raw_res.values():
            if isinstance(val, list):
                items = val
                break
        if not items:
            items = [raw_res]
            
    # Post-process to ensure source is tagged correctly
    domain = url.split("//")[-1].split("/")[0]
    final_items = []
    for it in items:
        if isinstance(it, dict) and it.get('title'):
            final_items.append({
                "title": it.get('title'),
                "link": it.get('link') if it.get('link') and it.get('link').startswith("http") else url,
                "summary": it.get('summary', ''),
                "source": "ScrapeGraph: " + domain,
                "date": it.get('date')
            })
    return final_items

if __name__ == "__main__":
    # Test with a known technical blog post
    test_url = "https://openai.com/index/hello-gpt-4o/"
    test_prompt = """
    Extract the latest 3-5 technical AI news articles, blog posts, or model releases from this page.
    For each item, provide:
    - 'title': The headline
    - 'summary': A concise 1-2 sentence technical summary
    - 'date': The publication date if explicitly available on the page, otherwise null.
    
    IMPORTANT: Focus ONLY on technical news like new LLMs, AI agents, architecture, or developer tools. Ignore company culture, hiring, or marketing fluff.
    CRITICAL: If scanning Anthropic's news page, ONLY extract articles explicitly categorized as 'Product' (e.g., model releases like Claude 3.5/3.7, api updates, computer use). Skip 'Company' or generic news.
    """
    print(f"Testing ScrapeGraphAI on: {test_url}")
    res = fetch_with_scrapegraph(test_url, test_prompt)
    print(res)
