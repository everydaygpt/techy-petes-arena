#!/usr/bin/env python3
"""
Techy Pete's Multi-Bot Live Trader
Runs 5 bots simultaneously during market hours, each with a different strategy.
Generates a head-to-head comparison dashboard after each cycle.

Usage:
    python multi_trader.py                # Run all 5 bots live during market hours
    python multi_trader.py --interval 10  # Scan every 10 minutes
    python multi_trader.py --scan-only    # See signals without executing trades
    python multi_trader.py --once         # Run one cycle and exit
    python multi_trader.py --reset        # Reset ALL bots to $10K fresh start
    python multi_trader.py --status       # Show all bot standings

Press Ctrl+C to stop cleanly at any time.
"""

import sys
import time
import signal
import datetime
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import Portfolio, DataFetcher
from bot import OpenClawBot
from compare_dashboard import generate_comparison_dashboard

# ─── Bot Definitions ─────────────────────────────────────────
PLATFORM_DIR = Path(__file__).parent
BOTS_DIR = PLATFORM_DIR / "bots"

BOT_ROSTER = [
    {"id": "momentum_pete",       "name": "Momentum Pete",       "emoji": "🚀", "color": "#58a6ff"},
    {"id": "cautious_carl",       "name": "Cautious Carl",       "emoji": "🛡️", "color": "#3fb950"},
    {"id": "mean_reversion_mary", "name": "Mean Reversion Mary", "emoji": "🔄", "color": "#bc8cff"},
    {"id": "volume_victor",       "name": "Volume Victor",       "emoji": "📊", "color": "#f0883e"},
    {"id": "yolo_yolanda",        "name": "YOLO Yolanda",        "emoji": "🎲", "color": "#f85149"},
]

# ─── Market Hours ────────────────────────────────────────────
EASTERN_OFFSET = -5
MARKET_OPEN_HOUR, MARKET_OPEN_MIN = 9, 30
MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN = 16, 0

running = True


def signal_handler(sig, frame):
    global running
    print("\n\n  [!] Shutdown signal received. Finishing current cycle...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_eastern_now():
    utc_now = datetime.datetime.utcnow()
    return utc_now + datetime.timedelta(hours=EASTERN_OFFSET)


def is_market_hours():
    now = get_eastern_now()
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0)
    close_t = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0)
    return open_t <= now <= close_t


def time_until_market_open():
    now = get_eastern_now()
    today_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0, microsecond=0)
    if now < today_open and now.weekday() < 5:
        return (today_open - now).total_seconds(), today_open
    next_day = now + datetime.timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    next_open = next_day.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0, microsecond=0)
    return (next_open - now).total_seconds(), next_open


def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"


def load_bot_config(bot_id):
    """Load a bot's config.json."""
    config_path = BOTS_DIR / bot_id / "config.json"
    with open(config_path) as f:
        return json.load(f)


def get_bot_data_dir(bot_id):
    """Get the data directory for a bot."""
    return BOTS_DIR / bot_id


# ─── Core Logic ──────────────────────────────────────────────

def run_single_bot(bot_info, scan_only=False):
    """Run one trading cycle for a single bot. Returns summary dict."""
    bot_id = bot_info["id"]
    bot_name = bot_info["name"]
    emoji = bot_info["emoji"]

    try:
        config = load_bot_config(bot_id)
        data_dir = get_bot_data_dir(bot_id)
        portfolio = Portfolio.load(starting_cash=config["starting_cash"], data_dir=str(data_dir))
        bot = OpenClawBot(config)

        # Update prices for existing positions
        if portfolio.positions:
            symbols = list(portfolio.positions.keys())
            prices = DataFetcher.get_current_prices(symbols)
            portfolio.update_prices(prices)
            portfolio.save()

        # Scan
        buy_signals, sell_signals, all_signals = bot.run_scan(portfolio)

        # Execute
        executed = []
        if not scan_only and (buy_signals or sell_signals):
            executed = bot.execute_signals(portfolio, buy_signals, sell_signals)

        summary = portfolio.get_summary()
        pnl_sign = "+" if summary["total_pnl"] >= 0 else ""

        print(f"  {emoji} {bot_name:<22} │ ${summary['total_value']:>10,.2f} │ "
              f"{pnl_sign}{summary['total_return_pct']:.2f}% │ "
              f"{summary['num_positions']} pos │ {len(executed)} trades")

        return {
            "bot_id": bot_id,
            "bot_name": bot_name,
            "emoji": emoji,
            "color": bot_info["color"],
            "summary": summary,
            "trades_this_cycle": len(executed),
            "signals": bot.get_signals_summary(),
            "description": config.get("bot_description", ""),
        }

    except Exception as e:
        print(f"  {emoji} {bot_name:<22} │ ERROR: {str(e)[:50]}")
        return {
            "bot_id": bot_id,
            "bot_name": bot_name,
            "emoji": emoji,
            "color": bot_info["color"],
            "summary": {"total_value": 10000, "total_pnl": 0, "total_return_pct": 0,
                        "num_positions": 0, "num_trades": 0, "win_rate": 0,
                        "cash": 10000, "positions_value": 0, "realized_pnl": 0,
                        "unrealized_pnl": 0, "positions": [], "starting_cash": 10000},
            "trades_this_cycle": 0,
            "signals": [],
            "description": "",
        }


def run_all_bots(scan_only=False):
    """Run one cycle for all bots, return list of results."""
    now = datetime.datetime.now()

    print(f"\n{'━'*70}")
    print(f"  TECHY PETE'S MULTI-BOT ARENA  │  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━'*70}")
    print(f"  {'Bot':<25} │ {'Value':>12} │ {'Return':>7} │ {'Pos':>5} │ Trades")
    print(f"  {'─'*25}─┼─{'─'*12}─┼─{'─'*7}─┼─{'─'*5}─┼─{'─'*6}")

    results = []
    for bot_info in BOT_ROSTER:
        result = run_single_bot(bot_info, scan_only=scan_only)
        results.append(result)

    # Leaderboard
    ranked = sorted(results, key=lambda r: r["summary"]["total_return_pct"], reverse=True)

    print(f"\n  {'━'*50}")
    print(f"  LEADERBOARD")
    print(f"  {'━'*50}")
    for i, r in enumerate(ranked):
        medal = ["🥇", "🥈", "🥉", "  4.", "  5."][i]
        pnl = r["summary"]["total_pnl"]
        pnl_sign = "+" if pnl >= 0 else ""
        print(f"  {medal} {r['emoji']} {r['bot_name']:<22} {pnl_sign}${pnl:>8,.2f}  ({pnl_sign}{r['summary']['total_return_pct']:.2f}%)")

    print(f"  {'━'*50}")

    return results


def reset_all_bots():
    """Reset all 5 bots to $10K fresh start."""
    print("\n  Resetting all bots to $10,000...")
    for bot_info in BOT_ROSTER:
        bot_id = bot_info["id"]
        data_dir = get_bot_data_dir(bot_id)

        for fname in ["portfolio.json", "value_history.json"]:
            fpath = data_dir / fname
            if fpath.exists():
                os.remove(fpath)

        config = load_bot_config(bot_id)
        portfolio = Portfolio(starting_cash=config["starting_cash"], data_dir=str(data_dir))
        portfolio.save()
        print(f"  {bot_info['emoji']} {bot_info['name']}: reset to ${config['starting_cash']:,.2f}")

    print("\n  All bots reset. Ready to compete!\n")


def show_status():
    """Show current standings for all bots."""
    print(f"\n{'━'*70}")
    print(f"  TECHY PETE'S MULTI-BOT STANDINGS")
    print(f"{'━'*70}")
    print(f"  {'Bot':<25} │ {'Value':>12} │ {'P&L':>10} │ {'Return':>8} │ {'Pos':>3} │ {'Trades':>6} │ {'Win%':>5}")
    print(f"  {'─'*25}─┼─{'─'*12}─┼─{'─'*10}─┼─{'─'*8}─┼─{'─'*3}─┼─{'─'*6}─┼─{'─'*5}")

    results = []
    for bot_info in BOT_ROSTER:
        bot_id = bot_info["id"]
        try:
            config = load_bot_config(bot_id)
            data_dir = get_bot_data_dir(bot_id)
            portfolio = Portfolio.load(starting_cash=config["starting_cash"], data_dir=str(data_dir))
            s = portfolio.get_summary()
            pnl_sign = "+" if s["total_pnl"] >= 0 else ""
            print(f"  {bot_info['emoji']} {bot_info['name']:<22} │ ${s['total_value']:>10,.2f} │ "
                  f"{pnl_sign}${s['total_pnl']:>8,.2f} │ {pnl_sign}{s['total_return_pct']:>6.2f}% │ "
                  f"{s['num_positions']:>3} │ {s['num_trades']:>6} │ {s['win_rate']:>4.1f}%")
            results.append((bot_info, s))
        except Exception as e:
            print(f"  {bot_info['emoji']} {bot_info['name']:<22} │ {'ERROR':>12} │ {str(e)[:30]}")

    if results:
        ranked = sorted(results, key=lambda r: r[1]["total_return_pct"], reverse=True)
        best = ranked[0]
        print(f"\n  👑 Leader: {best[0]['emoji']} {best[0]['name']} at {best[1]['total_return_pct']:+.2f}%")

    print(f"{'━'*70}\n")


def print_banner():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║       TECHY PETE'S INVESTMENT APP  v1.0               ║
    ║                                                       ║
    ║       🚀  Momentum Pete                               ║
    ║       🛡️  Cautious Carl                                ║
    ║       🔄  Mean Reversion Mary                         ║
    ║       📊  Volume Victor                               ║
    ║       🎲  YOLO Yolanda                                ║
    ║                                                       ║
    ║            >>> 5-BOT ARENA MODE <<<                   ║
    ╚═══════════════════════════════════════════════════════╝
    """)


# ─── Main Loop ───────────────────────────────────────────────

def main():
    global running

    print_banner()

    args = sys.argv[1:]

    if "--reset" in args:
        confirm = input("  Reset ALL 5 bots to $10K? This erases all history. (yes/no): ")
        if confirm.lower() == "yes":
            reset_all_bots()
        return

    if "--status" in args:
        show_status()
        return

    if "--test" in args:
        print("  [TEST MODE] Testing the full pipeline...\n")

        # 1. Regenerate dashboard from current bot data
        print("  [1/3] Regenerating dashboard from current data...")
        try:
            dashboard_path = generate_comparison_dashboard()
            print(f"        Dashboard saved: {dashboard_path}")
        except Exception as e:
            print(f"        Dashboard FAILED: {e}")
            import traceback; traceback.print_exc()
            return

        # 2. Deploy to GitHub
        print("  [2/3] Pushing to GitHub Pages...")
        try:
            from deploy import deploy_verbose
            success, msg = deploy_verbose()
            print(f"        {'[OK]' if success else '[FAIL]'} {msg}")
        except ImportError:
            # Fallback to regular deploy with manual output
            from deploy import deploy
            success, msg = deploy()
            print(f"        {'[OK]' if success else '[FAIL]'} {msg}")
        except Exception as e:
            print(f"        Deploy FAILED: {e}")
            import traceback; traceback.print_exc()
            return

        # 3. Confirm
        if success:
            print("  [3/3] Deployed! Check your dashboard in ~30 seconds:")
            print("        https://everydaygpt.github.io/techy-petes-arena/arena_dashboard.html")
            print("\n        (Dashboard now auto-refreshes every 2 minutes)")
        else:
            print("  [3/3] Deploy failed. Try manually:")
            print("        git add -A && git commit -m 'update' && git push")
        return

    interval_min = 15
    scan_only = "--scan-only" in args
    run_once = "--once" in args
    auto_deploy = "--deploy" in args

    for i, arg in enumerate(args):
        if arg == "--interval" and i + 1 < len(args):
            try:
                interval_min = int(args[i + 1])
            except ValueError:
                pass

    interval_sec = interval_min * 60
    mode_str = "SCAN ONLY" if scan_only else "LIVE TRADING"
    eastern = get_eastern_now()

    deploy_str = "ON (GitHub Pages)" if auto_deploy else "OFF"
    print(f"  Mode:      {mode_str}")
    print(f"  Interval:  Every {interval_min} minutes")
    print(f"  Deploy:    {deploy_str}")
    print(f"  Time (ET): {eastern.strftime('%A %Y-%m-%d %H:%M')}")
    print(f"  Bots:      {len(BOT_ROSTER)} competing")
    if not run_once:
        print(f"\n  Press Ctrl+C to stop.\n")

    cycles = 0

    while running:
        if run_once or is_market_hours():
            # Run all bots
            results = run_all_bots(scan_only=scan_only)
            cycles += 1

            # Generate comparison dashboard
            print(f"\n  [*] Generating comparison dashboard...")
            try:
                dashboard_path = generate_comparison_dashboard(results, BOT_ROSTER)
                print(f"      Saved to: {dashboard_path}")
            except Exception as e:
                print(f"      Dashboard error: {e}")

            # Auto-deploy to GitHub Pages
            if auto_deploy:
                print(f"  [*] Deploying to GitHub Pages...")
                try:
                    from deploy import deploy
                    success, msg = deploy()
                    print(f"      {'[OK]' if success else '[FAIL]'} {msg}")
                except Exception as e:
                    print(f"      Deploy error: {e}")

            if run_once:
                print(f"\n  Single cycle complete. Exiting.")
                break

            # Wait for next cycle
            if running:
                next_time = datetime.datetime.now() + datetime.timedelta(seconds=interval_sec)
                print(f"\n  Next cycle at {next_time.strftime('%H:%M:%S')} ({interval_min}m)")
                wait_until = time.time() + interval_sec
                while running and time.time() < wait_until:
                    time.sleep(min(5, wait_until - time.time()))

        else:
            secs, next_open = time_until_market_open()
            dur = format_duration(secs)
            eastern = get_eastern_now()
            if eastern.weekday() >= 5:
                print(f"\n  Weekend — market opens {next_open.strftime('%A at %I:%M %p ET')} ({dur})")
            else:
                print(f"\n  Market closed — opens at {next_open.strftime('%I:%M %p ET')} ({dur})")

            while running and not is_market_hours():
                time.sleep(30)

    # Shutdown
    if cycles > 0:
        print(f"\n{'═'*70}")
        print(f"  SESSION COMPLETE  │  {cycles} cycles")
        print(f"{'═'*70}")
        show_status()


if __name__ == "__main__":
    main()
