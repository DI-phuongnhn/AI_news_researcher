import requests
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import Config

def send_teams_notification(news_items):
    """
    Sends a formatted summary of the latest AI news to Microsoft Teams.
    
    Args:
        news_items (list): A list of summarized news dictionaries.
    """
    if not Config.TEAMS_WEBHOOK_URL:
        print("[Teams Notifier] TEAMS_WEBHOOK_URL not configured. Skipping notification.")
        return False
        
    if not news_items:
        print("[Teams Notifier] No news items to push. Skipping notification.")
        return False

    # Limit to top 5 as per user request
    top_items = news_items[:5]
    
    # Constructing a legacy MessageCard (widely supported by Teams Incoming Webhooks)
    # We use a structured format with sections for better readability
    
    sections = []
    for item in top_items:
        sections.append({
            "activityTitle": f"**{item['title']}**",
            "activitySubtitle": f"Source: {item['source']} | {item.get('date', 'Recent')[:10]}",
            "text": item['summary_vn'],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Read Original",
                    "targets": [{"os": "default", "uri": item['link']}]
                }
            ]
        })

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0078D7",
        "summary": "Daily Technical AI News Summary",
        "sections": [
            {
                "startGroup": True,
                "title": "🚀 Top Technical AI News Today",
                "text": f"Found {len(news_items)} relevant items. Here are the top 5 priority technical updates."
            },
            *sections
        ]
    }

    try:
        response = requests.post(
            Config.TEAMS_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"[Teams Notifier] Successfully pushed {len(top_items)} items to Teams.")
            return True
        else:
            print(f"[Teams Notifier] Failed to push to Teams. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"[Teams Notifier] Error sending notification: {e}")
        return False

if __name__ == "__main__":
    # Test notification
    test_items = [
        {
            "title": "{Test} DeepSeek-V3 Released",
            "source": "Manual Test",
            "summary_vn": "DeepSeek-V3 là mô hình Mixture-of-Experts (MoE) mạnh mẽ với 671 tỷ tham số, tối ưu hóa cho suy luận và mã nguồn.",
            "link": "https://github.com/deepseek-ai/DeepSeek-V3"
        }
    ]
    send_teams_notification(test_items)
