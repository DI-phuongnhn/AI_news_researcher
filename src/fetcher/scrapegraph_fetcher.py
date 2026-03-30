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

    for i, api_key in enumerate(keys):
        graph_config = {
            "llm": {
                "api_key": api_key,
                "model": "google_genai/gemini-2.0-flash",
            },
            "verbose": False,
            "headless": True
        }

        try:
            print(f"  ScrapeGraphAI: Trying with Key Index {i}...")
            smart_scraper_graph = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=graph_config
            )
            
            result = smart_scraper_graph.run()
            if result:
                return result
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                print(f"  Key {i} exhausted. Rotating...")
                continue
            print(f"ScrapeGraphAI error for {url} with Key {i}: {e}")
            
    return None

if __name__ == "__main__":
    # Test with a known technical blog post
    test_url = "https://openai.com/index/hello-gpt-4o/"
    test_prompt = """
    Extract the latest 3-5 technical AI news articles, blog posts, or model releases from this page.
    For each item, provide:
    - 'title': The headline
    - 'summary': A concise 1-2 sentence technical summary
    - 'release_date': The date of the news (if available) or the current date.
    
    IMPORTANT: Focus ONLY on technical news like new LLMs, AI agents, architecture, or developer tools. Ignore company culture, hiring, or marketing fluff.
    CRITICAL: If scanning Anthropic's news page, ONLY extract articles explicitly categorized as 'Product' (e.g., model releases like Claude 3.5/3.7, api updates, computer use). Skip 'Company' or generic news.
    """
    print(f"Testing ScrapeGraphAI on: {test_url}")
    res = fetch_with_scrapegraph(test_url, test_prompt)
    print(res)
