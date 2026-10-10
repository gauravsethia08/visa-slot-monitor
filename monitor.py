"""
Visa Slot Monitor — Playwright-based change detector
Supports: Telegram, WhatsApp (Twilio), SMS (Twilio)
Modes:
  - Continuous:       CHECK_INTERVAL > 0  → loops forever, each URL fetched
                      only when its own "interval" has elapsed
  - Single-shot (CI): CHECK_INTERVAL = 0  → checks every URL once and exits
"""

import asyncio
import hashlib
import json
import logging
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from config import (
    URLS, CHECK_INTERVAL_SECONDS, STATE_FILE, LOG_FILE,
    STATE_COMMIT_EVERY_N_LOOPS, DETECTION_LOG,
)
from notifier import send_notification

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Graceful shutdown (GitHub sends SIGTERM before the job timeout kill) ──────
_SHUTDOWN = False

def _on_sigterm(signum, frame):
    global _SHUTDOWN
    log.info("🛑 SIGTERM received — finishing current loop, then exiting.")
    _SHUTDOWN = True

signal.signal(signal.SIGTERM, _on_sigterm)


# ── State persistence ──────────────────────────────────────────────────────────
def load_state() -> dict:
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def commit_files(reason: str, files: list):
    """Commit given files to the repo (crash safety / detection propagation)."""
    try:
        subprocess.run(["git", "add"] + files,
                       check=True, capture_output=True, timeout=30)
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"],
                              capture_output=True, timeout=30)
        if diff.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m",
                 f"chore: monitor state [{reason}] [skip ci]"],
                check=True, capture_output=True, timeout=60)
            subprocess.run(["git", "push"],
                           check=True, capture_output=True, timeout=120)
            log.info(f"   💾 Committed {files} [{reason}]")
    except Exception as e:
        log.warning(f"   ⚠️ Git commit failed (non-fatal): {e}")


def commit_state(reason: str):
    """Push state.json to the repo so a crash/timeout doesn't lose baselines."""
    commit_files(reason, [STATE_FILE])


def log_detection(label: str, url: str, summary: str):
    """
    Append a detection event to detections.jsonl and commit it IMMEDIATELY,
    so the tailing agent (Muse) sees it within ~1 minute instead of waiting
    for the next periodic state commit.
    """
    entry = {
        "id": hashlib.sha256(
            f"{time.time()}|{label}|{url}".encode()).hexdigest()[:16],
        "ts": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "url": url,
        "summary": summary[:2000],
    }
    try:
        with open(DETECTION_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        # bound file size — keep the most recent 500 detections
        with open(DETECTION_LOG) as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(DETECTION_LOG, "w") as f:
                f.writelines(lines[-500:])
        commit_files("detection", [DETECTION_LOG])
    except Exception as e:
        log.warning(f"   ⚠️ Detection log failed (non-fatal): {e}")


# ── Per-URL scheduling ─────────────────────────────────────────────────────────
def is_due(entry: dict, state: dict, now_ts: float) -> bool:
    """True when this URL's own interval has elapsed since its last check."""
    interval = entry.get("interval", CHECK_INTERVAL_SECONDS)
    last = state.get(entry["url"], {}).get("last_checked_ts", 0)
    return (now_ts - last) >= interval


# ── Dynamic-content normalization ──────────────────────────────────────────────
# Strip lines that change on every page load (ad countdowns, relative
# timestamps) BEFORE hashing, so the fingerprint only reflects real content.
# Without this, every loop "detects" a change and spams detections.
import re as _re
DYNAMIC_LINE_PATTERNS = [
    r"^ad ends in \d+$",              # visagrader video-ad countdown
    r"you can skip to video in \d+",  # visagrader video-ad skip overlay
    r"\d+\s+(second|minute|hour)s?\s+ago",  # relative timestamps
    r"^video (paused|muted|playing)$",     # visagrader video-ad player state
    r"^(sponsored|advertisement)$",   # ad-block disclosure labels
]
# Tokens that rotate on every load but sit inline within a line.
INLINE_PATTERNS = [
    r"[a-z]{2,4}\d*::[A-Za-z0-9_.\-]+",  # Vercel ad-impression tokens (iad1::, sfo1::, …)
    r"\(updated within last [^)]*\)",   # visagrader tracker relative timestamps
]

def normalize_text(text: str) -> str:
    for p in INLINE_PATTERNS:
        text = _re.sub(p, "", text, flags=_re.IGNORECASE)
    out = []
    for line in text.splitlines():
        s = line.strip()
        if any(_re.search(p, s, _re.IGNORECASE) for p in DYNAMIC_LINE_PATTERNS):
            continue
        out.append(line)
    return "\n".join(out).strip()


# ── Page scraping ──────────────────────────────────────────────────────────────
CLOUDFLARE_KEYWORDS = ["security service", "verifying you are not a bot", "Ray ID", "Cloudflare"]

async def get_page_content(browser, url: str) -> tuple[str, str]:
    """
    Returns (visible_text, sha256_hash).
    Uses a real Chromium browser so JS-rendered pages and #hash fragments work.
    """
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        timezone_id="America/New_York",
        viewport={"width": 1280, "height": 800},
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(5_000)

        if "#" in url:
            fragment = url.split("#")[-1]
            try:
                await page.evaluate(
                    f"document.getElementById('{fragment}')?.scrollIntoView()"
                )
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

        text = normalize_text(await page.evaluate("""() => {
            ['nav','footer','header','script','style','noscript',
             '.cookie-banner','#cookie-notice','.ads','.advertisement']
              .forEach(sel => document.querySelectorAll(sel)
                .forEach(el => el.remove()));
            return document.body?.innerText?.trim() ?? '';
        }"""))

        if any(kw in text for kw in CLOUDFLARE_KEYWORDS):
            raise RuntimeError("Cloudflare challenge page detected — bot blocked")

        return text, hashlib.sha256(text.encode()).hexdigest()
    finally:
        await page.close()
        await context.close()


# ── Diff summary ───────────────────────────────────────────────────────────────
def summarize_change(old_text: str, new_text: str) -> str:
    old_lines = set(old_text.splitlines())
    new_lines = set(new_text.splitlines())
    added   = [l for l in (new_lines - old_lines) if l.strip()]
    removed = [l for l in (old_lines - new_lines) if l.strip()]
    parts = []
    if added:
        parts.append("➕ *New content:*\n```\n" + "\n".join(added[:6]) + "\n```")
    if removed:
        parts.append("➖ *Removed:*\n```\n" + "\n".join(removed[:6]) + "\n```")
    return "\n\n".join(parts) if parts else "Page content changed."


# ── Core check logic ───────────────────────────────────────────────────────────
async def check_all_urls(browser, state: dict, texts: dict) -> bool:
    changed = False
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_ts = time.time()

    for entry in URLS:
        url   = entry["url"]
        label = entry["label"]

        if not is_due(entry, state, now_ts):
            continue

        try:
            new_text, new_hash = await get_page_content(browser, url)
            old_hash = state.get(url, {}).get("hash", "")

            if url not in state:
                state[url] = {}
            state[url]["label"]           = label
            state[url]["last_checked"]    = now
            state[url]["last_checked_ts"] = now_ts

            if old_hash == "":
                log.info(f"   📸 Baseline recorded: {label}")
                state[url]["hash"] = new_hash
                texts[url] = new_text
            elif new_hash != old_hash:
                log.info(f"   🔔 CHANGE DETECTED: {label}")
                diff = summarize_change(texts.get(url, ""), new_text)
                message = (
                    f"🚨 *Visa Slot Change Detected!*\n\n"
                    f"📍 *Site:* {label}\n"
                    f"🔗 {url}\n\n"
                    f"{diff}\n\n"
                    f"🕐 {now}"
                )
                await send_notification(message)
                log_detection(label, url, diff)
                state[url]["hash"] = new_hash
                texts[url] = new_text
                changed = True
            else:
                log.info(f"   — No change: {label}")

        except Exception as e:
            log.error(f"   ❌ Error checking {label}: {e}")

    save_state(state)
    return changed


# ── Entry point ────────────────────────────────────────────────────────────────
async def run_monitor():
    state = load_state()
    texts: dict[str, str] = {}

    log.info("🚀 Visa slot monitor starting")
    log.info(f"   URLs     : {len(URLS)}")
    log.info(f"   Mode     : {'single-shot (CI)' if CHECK_INTERVAL_SECONDS == 0 else 'continuous (' + str(CHECK_INTERVAL_SECONDS) + 's tick)'}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        if CHECK_INTERVAL_SECONDS == 0:
            # Single-shot mode — check every URL once and exit
            log.info("⚡ Running single check...")
            # force all URLs due in single-shot mode
            for entry in URLS:
                state.setdefault(entry["url"], {})["last_checked_ts"] = 0
            await check_all_urls(browser, state, texts)
            log.info("✅ Done. Exiting.")
        else:
            # Continuous mode — persistent looper (for GitHub Actions 6h jobs)
            log.info("👁️  Continuous mode started\n")
            loop_n = 0
            while not _SHUTDOWN:
                loop_n += 1
                await check_all_urls(browser, state, texts)
                if loop_n % STATE_COMMIT_EVERY_N_LOOPS == 0:
                    commit_files(f"periodic loop {loop_n}",
                                 [STATE_FILE, DETECTION_LOG])
                if _SHUTDOWN:
                    break
                log.info(f"   💤 Sleeping {CHECK_INTERVAL_SECONDS}s...\n")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

            log.info("🛑 Shutting down — final state save.")
            save_state(state)
            commit_state("shutdown")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_monitor())
