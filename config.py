"""
Configuration — edit this file to customise your monitor.

Sub-5-minute mode: the loop tick is 60s (CHECK_INTERVAL). Each URL carries its
own "interval" so aggressive sources stay respectful:
  - visagrader      → every 60s  (lightweight pages, no rate limit observed)
  - checkvisaslots  → every 300s (bot mitigation + 20 sessions/day fair use;
                      hammering it every 60s *will* get the runner blocked)
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file automatically

# ── URLs to watch ──────────────────────────────────────────────────────────────
# "interval" = seconds between checks of THIS url (independent of loop tick)
URLS = [
    {
        "label": "CheckVisaSlots — H1B Regular",
        "url": "https://checkvisaslots.com/latest-us-visa-availability/h-1b-regular/",
        "interval": 300,
    },
    # ── VisaGrader — H1B Biometrics (every 60s) ────────────────────────────────
    {
        "label": "VisaGrader — New Delhi H1B Biometrics",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/new-delhi-P147/h1b-visa-H1B#Biometrics",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Chennai H1B Biometrics",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/chennai-P48/h1b-visa-H1B#Biometrics",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Hyderabad H1B Biometrics",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/hyderabad-P85/h1b-visa-H1B#Biometrics",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Kolkata H1B Biometrics",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/kolkata-P100/h1b-visa-H1B#Biometrics",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Mumbai H1B Biometrics",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/mumbai-P139/h1b-visa-H1B#Biometrics",
        "interval": 60,
    },
    # ── VisaGrader — H1B Interview (every 60s) ─────────────────────────────────
    {
        "label": "VisaGrader — New Delhi H1B Interview",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/new-delhi-P147/h1b-visa-H1B#Interview",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Chennai H1B Interview",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/chennai-P48/h1b-visa-H1B#Interview",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Hyderabad H1B Interview",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/hyderabad-P85/h1b-visa-H1B#Interview",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Kolkata H1B Interview",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/kolkata-P100/h1b-visa-H1B#Interview",
        "interval": 60,
    },
    {
        "label": "VisaGrader — Mumbai H1B Interview",
        "url": "https://visagrader.com/us-visa-time-slots-availability/india-ind/mumbai-P139/h1b-visa-H1B#Interview",
        "interval": 60,
    },
]

# ── Loop tick ──────────────────────────────────────────────────────────────────
# Seconds between loop iterations. Each URL is only fetched when its own
# "interval" has elapsed. 60 = the loop wakes every minute.
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL", 60))

# Commit monitor state back to the repo every N loop iterations (crash safety).
# 30 iterations × 60s tick = every 30 minutes.
STATE_COMMIT_EVERY_N_LOOPS = int(os.getenv("STATE_COMMIT_EVERY", 30))

# ── Notification channels ──────────────────────────────────────────────────────
# Set to True to enable each channel. Configure credentials below or in .env

# 1. Telegram (FREE — recommended)
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")   # From @BotFather
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")     # Your personal chat ID

# 2. WhatsApp via Twilio (needs Twilio account — free sandbox available)
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # Twilio sandbox number
TWILIO_WHATSAPP_TO   = os.getenv("TWILIO_WHATSAPP_TO", "")     # e.g. whatsapp:+919876543210

# 3. SMS via Twilio
SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
TWILIO_SMS_FROM = os.getenv("TWILIO_SMS_FROM", "")   # Your Twilio phone number
TWILIO_SMS_TO   = os.getenv("TWILIO_SMS_TO", "")     # Your mobile number e.g. +919876543210

# ── Files ──────────────────────────────────────────────────────────────────────
STATE_FILE = "state.json"         # Stores page hashes between runs
LOG_FILE   = "monitor.log"        # Log file
DETECTION_LOG = "detections.jsonl"  # Every confirmed change, one JSON per line.
                                    # Committed immediately so a tailing agent
                                    # sees detections within ~1 minute.
