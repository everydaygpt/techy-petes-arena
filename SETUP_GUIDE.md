# Techy Pete's Investment App — Hosting Setup Guide

## The Plan

You run the bots on your machine. After each cycle, the dashboard automatically pushes to a free website that you and your buddy both access from the same URL. No servers to manage, no cost.

**What you'll use:** GitHub Pages (free, auto-hosted from a repo)

---

## Step 1: Install Prerequisites (your machine)

Open a terminal and make sure you have these installed:

```bash
# Python packages (the bot needs these)
pip install yfinance pandas numpy

# Git (you probably already have this)
git --version

# GitHub CLI (makes setup easier)
# Mac:
brew install gh
# Windows:
winget install GitHub.cli
# Linux:
sudo apt install gh
```

---

## Step 2: Create the GitHub Repo

```bash
# Login to GitHub (one-time)
gh auth login

# Navigate to your project folder
cd openclaw_platform

# Initialize git and create the repo
git init
git add .
git commit -m "Initial commit - Techy Pete's Investment App"

# Create a public repo on GitHub (public is required for free GitHub Pages)
gh repo create techy-petes-arena --public --source=. --push
```

---

## Step 3: Enable GitHub Pages

```bash
# This tells GitHub to serve your HTML files as a website
gh api repos/{owner}/techy-petes-arena/pages -X POST -f source.branch=main -f source.path=/
```

**Or do it manually:**
1. Go to https://github.com/YOUR_USERNAME/techy-petes-arena
2. Click **Settings** → **Pages** (left sidebar)
3. Under "Source", select **main** branch, **/ (root)** folder
4. Click **Save**

Your dashboard will be live at:
```
https://YOUR_USERNAME.github.io/techy-petes-arena/arena_dashboard.html
```

Share that URL with your buddy. Done.

---

## Step 4: Run the Bots with Auto-Deploy

Use the included deploy script to run bots AND push updates automatically:

```bash
# Run all 5 bots with auto-deploy to GitHub Pages
python multi_trader.py --deploy

# Or run once and deploy
python multi_trader.py --once --deploy
```

Every cycle, the script will:
1. Run all 5 bots (scan → trade → update)
2. Regenerate the arena dashboard
3. Git commit and push the updated HTML to GitHub
4. Your buddy refreshes the page and sees the latest data

---

## Step 5: Keep it Running During Market Hours

**Option A: Just leave a terminal open**
```bash
python multi_trader.py --deploy
```
Leave this running during 9:30 AM – 4:00 PM ET. It auto-sleeps outside market hours.

**Option B: Run in the background (Mac/Linux)**
```bash
nohup python multi_trader.py --deploy > bot_output.log 2>&1 &
```
This keeps running even if you close the terminal. Check the log:
```bash
tail -f bot_output.log
```

**Option C: Schedule it with cron (Mac/Linux)**
```bash
# Edit crontab
crontab -e

# Add this line — runs every weekday at 9:25 AM ET, stops at 4:05 PM
25 9 * * 1-5 cd /path/to/openclaw_platform && python multi_trader.py --deploy >> bot_output.log 2>&1
```

**Option D: Task Scheduler (Windows)**
1. Open Task Scheduler
2. Create Basic Task → "Techy Pete Bot"
3. Trigger: Daily, 9:25 AM, weekdays only
4. Action: Start Program → `python`, Arguments: `multi_trader.py --deploy`
5. Set working directory to your openclaw_platform folder

---

## What Your Buddy Sees

Your buddy just bookmarks this URL and refreshes it whenever they want:

```
https://YOUR_USERNAME.github.io/techy-petes-arena/arena_dashboard.html
```

The page shows:
- Live leaderboard of all 5 bots
- Equity curves tracking each bot's performance
- Which symbols each bot is holding
- Recent trade history per bot
- Return % comparison chart

No login, no install, no setup on their end. Just a URL.

---

## Useful Commands Reference

| Command | What it does |
|---------|-------------|
| `python multi_trader.py` | Run all 5 bots during market hours |
| `python multi_trader.py --deploy` | Run + auto-push dashboard to GitHub |
| `python multi_trader.py --once` | Run one cycle and exit |
| `python multi_trader.py --status` | Quick standings check |
| `python multi_trader.py --reset` | Wipe all bots back to $10K |
| `python multi_trader.py --interval 10` | Scan every 10 minutes instead of 15 |
| `python multi_trader.py --scan-only` | See signals without executing trades |

---

## Troubleshooting

**"GitHub Pages not working"**
- Make sure the repo is public (free Pages requires public repos)
- Check Settings → Pages → it should say "Your site is live at..."
- It can take 1-2 minutes after a push for changes to appear

**"Bot can't fetch data"**
- Make sure you have internet access
- Run `pip install --upgrade yfinance` if data fetching fails
- Yahoo Finance occasionally rate-limits; the bot retries automatically

**"Dashboard isn't updating"**
- Check that the `--deploy` flag is set
- Run `git status` in the project folder to see if changes are staged
- Run `git push` manually if auto-push failed

**"I want to reset everything"**
```bash
python multi_trader.py --reset
```
Then run the bots again — they'll start fresh at $10K each.
