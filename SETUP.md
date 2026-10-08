# Setup — 60-second Visa Slot Monitor (Muse alerts, no Telegram bot)

Takes ~10 minutes. You need: a GitHub account. That's it — alerts come from
your Muse agent in the H-1B side chat, not from a bot.

How alerting works: the monitor writes every detection to `detections.jsonl`
in the repo and commits it immediately. Your Muse agent tails that file every
60 seconds and pings you in chat the moment a new detection lands.

## 1. Create the GitHub repo

1. Go to github.com → New repository → name it `visa-slot-monitor` → **Public**
   (public repos get unlimited free Actions minutes; private repos get 2,000/month).
2. Don't initialize with README — you'll push the files below.

## 2. Push these files

In a terminal where you have git + your GitHub credentials:

```bash
cd /path/to/visa-slot-monitor-1min   # the folder containing these files
git init
git add .
git commit -m "60-second visa slot monitor"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/visa-slot-monitor.git
git push -u origin main
```

(Or upload the files via GitHub's web UI: repo → Add file → Upload files.
Make sure the `.github/workflows/` folder is included.)

## 3. Start it

Repo → **Actions** tab → enable workflows if prompted → select
"🛂 Visa Slot Monitor" → **Run workflow** → Run.

The first run records baselines (no alerts — that's expected). From then on:
visagrader pages checked every 60s, checkvisaslots every 5 min, every change
appended to `detections.jsonl` and committed instantly. The looper restarts
itself every 6 hours via cron, so it runs 24/7 unattended.

## 4. Point Muse at it

Send your Muse agent the repo URL (e.g.
`https://github.com/YOUR_USERNAME/visa-slot-monitor`). It will tail
`detections.jsonl` every 60 seconds and alert you in the H-1B side chat.

## Optional: also get Telegram alerts

If you ever want a Telegram bot too: message @BotFather → `/newbot`, then
@userinfobot for your chat ID, and add them as repo secrets
`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`. The notifier picks them up
automatically — no code changes needed.

## Tuning

- `config.py` → per-URL `"interval"` values (seconds). Don't drop checkvisaslots
  below 300 unless you enjoy getting blocked.
- Workflow cron `0 */6 * * *` controls looper restarts; `timeout-minutes: 355`
  must stay under GitHub's 6-hour job cap.

## Attribution

Forked from [shravyaamarnath/visa-slot-monitor](https://github.com/shravyaamarnath/visa-slot-monitor).
Changes here: persistent 60s looper job, per-URL intervals, detections log
committed immediately for agent tailing, periodic state commits, graceful
SIGTERM shutdown.
