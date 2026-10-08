# Visa Slot Monitor

## The Problem

In 2026, getting an H1B visa stamping appointment in India is extremely competitive. Slots open up and disappear within minutes. Manually refreshing visa availability websites throughout the day is impractical — by the time you notice a slot, it's gone.

I also couldn't monitor the official US visa appointment website directly. If it flagged my activity as automated, it could block my account — which would mean losing the ability to book at all, with serious consequences for my visa status.

So I needed a way to monitor third-party websites that track and publish visa slot availability, and get an instant alert the moment something opens up.

## How It Works

The monitor runs 24/7 on GitHub's free cloud infrastructure (GitHub Actions) —
no laptop needed. GitHub's scheduler can't tick faster than every 5 minutes, so
instead of one run per check, each run launches a **persistent looper**: a single
job that wakes every 60 seconds internally for ~6 hours, then cron restarts it
(4×/day). Net effect: **60-second checks, 24/7, on public repos' unlimited
Actions minutes**.

Each URL has its own interval (`config.py`):
- **visagrader** (10 consulate pages) → every **60s** (lightweight, no rate limit)
- **checkvisaslots** → every **5 min** (bot mitigation + 20 sessions/day fair
  use — hitting it every 60s *will* get the runner blocked)

Each loop:

1. **Visit due pages** — a headless Chromium opens each site whose interval has
   elapsed, configured to look like a normal browser.

2. **Extract the content** — strips ads, navbars and noise, leaving meaningful
   page text.

3. **Compare to last time** — SHA-256 fingerprint vs the hash saved from the
   previous check. Match = nothing changed; mismatch = something is new.

4. **Alert instantly** — Telegram message with what changed and a page link.

State (`state.json`) is committed back to the repo every 30 minutes inside the
loop plus on shutdown, so a crash or timeout never loses baselines.

**Sites monitored:** All 5 US consulate locations in India (New Delhi, Mumbai, Chennai, Hyderabad, Kolkata) for both H1B Biometrics and Interview slots — 10 URLs in total, plus a general H1B availability tracker.

## Tech Stack
**Built using Claude Code**
- **Python + Playwright** — browser automation
- **GitHub Actions** — free cloud scheduler (runs every 5 min)
- **Telegram Bot API** — instant notifications
 
