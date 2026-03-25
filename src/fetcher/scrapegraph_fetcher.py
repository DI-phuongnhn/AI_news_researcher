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
    test_prompt = "Extract the 'title', 'summary' (max 2 sentences), and 'release_date' from this post."
    print(f"Testing ScrapeGraphAI on: {test_url}")
    res = fetch_with_scrapegraph(test_url, test_prompt)
    print(res)
