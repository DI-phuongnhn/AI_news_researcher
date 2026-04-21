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
    
    # Construct an Adaptive Card as the root object for best integration with Power Automate Flow Bot
    body_elements = [
        {
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "text": "🚀 Top Technical AI News Today"
        },
        {
            "type": "TextBlock",
            "wrap": True,
            "text": f"Found {len(news_items)} relevant items. Here are the top 5 priority technical updates."
        }
    ]

    for item in top_items:
        body_elements.append({
            "type": "Container",
            "items": [
                {
                    "type": "TextBlock",
                    "weight": "Bolder",
                    "text": item['title'],
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "spacing": "None",
                    "text": f"Source: {item['source']} | {item.get('date', 'Recent')[:10]}",
                    "isSubtle": True,
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": item['summary_vn'],
                    "wrap": True
                }
            ],
            "style": "default",
            "spacing": "Medium"
        })
        body_elements.append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Read Original",
                    "url": item['link']
                }
            ]
        })

    # The payload is now a pure Adaptive Card object, which satisfies the Flow Bot's JSON requirement
    payload = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": body_elements
    }

    try:
        response = requests.post(
            Config.TEAMS_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code in (200, 202):
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
            "title": "[Test] Connection Verification",
            "source": "System",
            "summary_vn": "This is a simplified test message to verify the Microsoft Teams chat webhook is active and working.",
            "link": "https://github.com/DI-phuongnhn/AI_news_researcher"
        }
    ]
    send_teams_notification(test_items)
