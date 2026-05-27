"""
Microsoft Teams Notification Module.

This module formats and sends AI news summaries to a Microsoft Teams 
webhook. It supports the modern Adaptive Cards format, providing a 
rich, interactive viewing experience compared to legacy MessageCards.
"""

import requests
import json
from typing import List, Dict
from datetime import datetime
from src.config import Config

def send_teams_notification(news_items: List[Dict]):
    """
    Sends a burst of news cards to the configured Teams webhook.
    
    Args:
        news_items: List of summarized news (title, summary_vn, source, link).
    """
    if not Config.TEAMS_WEBHOOK_URL or not news_items:
        print("  Warning: Teams Webhook URL not configured or no news to send.")
        return

    # --- Block: Payload construction ---
    # We use the Adaptive Card schema (version 1.4) which is the modern 
    # standard for Teams Flow bots and Workflows.
    adaptive_card = {
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "🚀 AI NEWS RESEARCH - DAILY UPDATE",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent"
            },
            {
                "type": "TextBlock",
                "text": f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "isSubtle": True,
                "spacing": "None"
            }
        ],
        "actions": []
    }

    # --- Block: Item Mapping ---
    # We add each news item as a container block with a title, summary, and 'View' button.
    for item in news_items[:10]: # Limit to top 10 to avoid massive payloads.
        item_block = {
            "type": "Container",
            "separator": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": item.get('title', 'Unknown Title'),
                    "weight": "Bolder",
                    "wrap": True
                },
                {
                    "type": "TextBlock",
                    "text": (
                        "🏆 OFFICIAL LAB: " + item.get('source', 'Unknown') 
                        if any(lab in item.get('source', '').lower() or lab in item.get('link', '').lower() 
                               for lab in ["openai", "anthropic", "google", "meta", "nvidia", "deepseek", "mistral", "qwen", "huggingface"])
                        else "🔍 TECH DISCOVERY: " + item.get('source', 'Unknown')
                    ),
                    "isSubtle": True,
                    "spacing": "Small",
                    "color": "Accent"
                },
                {
                    "type": "TextBlock",
                    "text": item.get('summary_vn', 'No summary available.'),
                    "wrap": True,
                    "maxLines": 5
                }
            ]
        }
        adaptive_card["body"].append(item_block)
        
        # Add a direct action button for each link.
        adaptive_card["actions"].append({
            "type": "Action.OpenUrl",
            "title": f"View: {item.get('title', 'Link')[:20]}...",
            "url": item.get("link")
        })

    # --- Block: Dispatch ---
    # Teams Workflows (Power Automate) often returns 202 Accepted.
    try:
        response = requests.post(
            Config.TEAMS_WEBHOOK_URL,
            json=adaptive_card,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if response.status_code in [200, 202]:
            print(f"  Teams: Success! Notification sent ({response.status_code}).")
        else:
            print(f"  Error: Teams notification failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  Error: Failed to send Teams notification: {e}")

def send_test_notification():
    """
    Sends a simple minimalist card to verify the webhook connection.
    """
    test_card = {
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "[Test] Teams Connection Check",
                "weight": "Bolder"
            },
            {
                "type": "TextBlock",
                "text": "If you see this, the Flow Bot is correctly receiving Adaptive Cards.",
                "wrap": True
            }
        ]
    }
    requests.post(Config.TEAMS_WEBHOOK_URL, json=test_card)
