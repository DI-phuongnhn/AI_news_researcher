import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent.pipeline import ResearchPipeline


def build_item(title, days_ago=None, date_value=None):
    if date_value is None and days_ago is not None:
        date_value = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {
        "title": title,
        "link": f"https://example.com/{title.lower().replace(' ', '-')}",
        "summary": "Test item for date filtering.",
        "source": "Verification",
        "date": date_value,
    }


def main():
    pipeline = ResearchPipeline()
    sample_items = [
        build_item("Today", days_ago=0),
        build_item("Three Days Ago", days_ago=3),
        build_item("Five Days Ago", days_ago=5),
        build_item("Unknown Date", date_value=None),
        build_item("Relative Date", date_value="2 days ago"),
    ]

    fresh_items, stale_count, undated_count = pipeline._filter_recent_news(sample_items)
    kept_titles = [item["title"] for item in fresh_items]

    print(f"Kept: {kept_titles}")
    print(f"Stale count: {stale_count}")
    print(f"Undated count: {undated_count}")

    assert "Today" in kept_titles
    assert "Three Days Ago" in kept_titles
    assert "Relative Date" in kept_titles
    assert "Five Days Ago" not in kept_titles
    assert "Unknown Date" not in kept_titles
    assert stale_count == 1
    assert undated_count == 1
    print("Date filter verification passed.")


if __name__ == "__main__":
    main()
