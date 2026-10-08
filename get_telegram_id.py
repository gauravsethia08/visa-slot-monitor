"""
Run this ONCE after creating your Telegram bot to get your Chat ID.
Usage: python get_telegram_id.py
"""

import sys
import urllib.request
import json

token = input("Paste your Telegram Bot Token: ").strip()

url = f"https://api.telegram.org/bot{token}/getUpdates"
try:
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
except Exception as e:
    print(f"❌ Could not reach Telegram API: {e}")
    sys.exit(1)

if not data.get("ok"):
    print(f"❌ Telegram error: {data}")
    sys.exit(1)

updates = data.get("result", [])
if not updates:
    print("\n⚠️  No messages found.")
    print("Please send ANY message to your bot first, then re-run this script.")
    sys.exit(0)

# Get chat ID from the latest message
chat = updates[-1]["message"]["chat"]
chat_id = chat["id"]
name = chat.get("first_name", "") + " " + chat.get("last_name", "")

print(f"\n✅ Found your Chat ID!")
print(f"   Name    : {name.strip()}")
print(f"   Chat ID : {chat_id}")
print(f"\nAdd these to your .env file:")
print(f"   TELEGRAM_BOT_TOKEN={token}")
print(f"   TELEGRAM_CHAT_ID={chat_id}")
