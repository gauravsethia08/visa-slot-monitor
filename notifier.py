"""
Notification dispatcher — Telegram, WhatsApp (Twilio), SMS (Twilio)
"""

import logging
import aiohttp

from config import (
    TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    WHATSAPP_ENABLED, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO,
    SMS_ENABLED, TWILIO_SMS_FROM, TWILIO_SMS_TO,
)

log = logging.getLogger(__name__)


# ── Telegram ───────────────────────────────────────────────────────────────────
async def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured — skipping.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                log.info("   📨 Telegram notification sent ✅")
            else:
                body = await resp.text()
                log.error(f"   Telegram error {resp.status}: {body}")


# ── Twilio helper (shared for WhatsApp & SMS) ──────────────────────────────────
async def _send_twilio(from_: str, to: str, body: str):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        log.warning("Twilio credentials not configured — skipping.")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {"From": from_, "To": to, "Body": body}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, data=data,
            auth=aiohttp.BasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        ) as resp:
            result = await resp.json()
            if resp.status in (200, 201):
                log.info(f"   📨 Twilio message sent ✅  SID: {result.get('sid')}")
            else:
                log.error(f"   Twilio error {resp.status}: {result}")


# ── WhatsApp ───────────────────────────────────────────────────────────────────
async def send_whatsapp(message: str):
    if not WHATSAPP_ENABLED:
        return
    # Twilio WhatsApp doesn't support Markdown — strip asterisks
    plain = message.replace("*", "").replace("_", "")
    await _send_twilio(TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO, plain)
    log.info("   📱 WhatsApp notification sent ✅")


# ── SMS ────────────────────────────────────────────────────────────────────────
async def send_sms(message: str):
    if not SMS_ENABLED:
        return
    # Keep SMS short
    short = message[:160]
    await _send_twilio(TWILIO_SMS_FROM, TWILIO_SMS_TO, short)
    log.info("   💬 SMS notification sent ✅")


# ── Main dispatcher ────────────────────────────────────────────────────────────
async def send_notification(message: str):
    """Fire all enabled notification channels concurrently."""
    import asyncio

    tasks = []
    if TELEGRAM_ENABLED:
        tasks.append(send_telegram(message))
    if WHATSAPP_ENABLED:
        tasks.append(send_whatsapp(message))
    if SMS_ENABLED:
        tasks.append(send_sms(message))

    if not tasks:
        log.warning("⚠️  No notification channels enabled! Check config.py / .env")
        return

    await asyncio.gather(*tasks, return_exceptions=True)
