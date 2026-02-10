#!/usr/bin/env python3
"""
Techy Pete's Live Trader - Runs continuously during market hours.
Scans for signals, executes trades, and refreshes the dashboard on a loop.

Usage:
    python live_trader.py                # Run with default 15-min intervals
    python live_trader.py --interval 10  # Scan every 10 minutes
    python live_trader.py --scan-only    # Scan but don't execute trades
    python live_trader.py --extended     # Include pre-market (8AM) and after-hours (6PM)
    python live_trader.py --crypto-247   # Also trade crypto outside market hours

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
from bot import OpenClawBot, load_config
from generate_dashboard import generate_dashboard

# ─── Constants ───────────────────────────────────────────────
EASTERN_OFFSET = -5  # EST (adjust to -4 for EDT / daylight saving)

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MIN = 0

EXTENDED_OPEN_HOUR = 8
EXTENDED_OPEN_MIN = 0
EXTENDED_CLOSE_HOUR = 18
EXTENDED_CLOSE_MIN = 0

# ─── Globals ─────────────────────────────────────────────────
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n  [!] Shutdown signal received. Finishing current cycle...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_eastern_now():
    """Get current time in US Eastern."""
    utc_now = datetime.datetime.utcnow()
    # Simple offset — for production you'd use pytz or zoneinfo
    eastern = utc_now + datetime.timedelta(hours=EASTERN_OFFSET)
    return eastern


def is_weekday(dt=None):
    """Check if it's a weekday (Mon-Fri)."""
    if dt is None:
        dt = get_eastern_now()
    return dt.weekday() < 5  # 0=Mon, 4=Fri


def is_market_hours(extended=False):
    """Check if we're within market trading hours (Eastern time)."""
    now = get_eastern_now()

    if not is_weekday(now):
        return False

    if extended:
        open_time = now.replace(hour=EXTENDED_OPEN_HOUR, minute=EXTENDED_OPEN_MIN, second=0)
        close_time = now.replace(hour=EXTENDED_CLOSE_HOUR, minute=EXTENDED_CLOSE_MIN, second=0)
    else:
        open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0)
        close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0)

    return open_time <= now <= close_time


def time_until_market_open(extended=False):
    """Calculate seconds until next market open."""
    now = get_eastern_now()
    open_hour = EXTENDED_OPEN_HOUR if extended else MARKET_OPEN_HOUR
    open_min = EXTENDED_OPEN_MIN if extended else MARKET_OPEN_MIN

    # Today's open
    today_open = now.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)

    if now < today_open and is_weekday(now):
        # Market opens later today
        return (today_open - now).total_seconds(), today_open

    # Find next weekday
    next_day = now + datetime.timedelta(days=1)
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += datetime.timedelta(days=1)

    next_open = next_day.replace(hour=open_hour, minute=open_min, second=0, microsecond=0)
    return (next_open - now).total_seconds(), next_open


def format_duration(seconds):
    """Format seconds into a readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def print_live_banner():
    """Print the live trading banner."""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║     ████████╗███████╗ ██████╗██╗  ██╗██╗   ██╗       ║
    ║     ╚══██╔══╝██╔════╝██╔════╝██║  ██║╚██╗ ██╔╝       ║
    ║        ██║   █████╗  ██║     ███████║ ╚████╔╝        ║
    ║        ██║   ██╔══╝  ██║     ██╔══██║  ╚██╔╝         ║
    ║        ██║   ███████╗╚██████╗██║  ██║   ██║          ║
    ║        ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝   ╚═╝          ║
    ║     ██████╗ ███████╗████████╗███████╗ ███████╗        ║
    ║     ██╔══██╗██╔════╝╚══██╔══╝██╔════╝ ██╔════╝        ║
    ║     ██████╔╝█████╗     ██║   █████╗   ███████╗        ║
    ║     ██╔═══╝ ██╔══╝     ██║   ██╔══╝   ╚════██║        ║
    ║     ██║     ███████╗   ██║   ███████╗ ███████║        ║
    ║     ╚═╝     ╚══════╝   ╚═╝   ╚══════╝ ╚══════╝        ║
    ║                                                       ║
    ║       Techy Pete's Investment App  v1.0               ║
    ║               >>> LIVE TRADING MODE <<<               ║
    ╚═══════════════════════════════════════════════════════╝
    """)


def run_cycle(config, portfolio, bot, scan_only=False, crypto_only=False):
    """
    Run one complete trading cycle:
    1. Update prices for existing positions
    2. Scan for signals
    3. Execute trades (unless scan-only)
    4. Regenerate dashboard
    """
    now = datetime.datetime.now()
    cycle_start = time.time()

    print(f"\n{'━'*60}")
    print(f"  CYCLE @ {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━'*60}")

    # 1. Update existing position prices
    if portfolio.positions:
        symbols = list(portfolio.positions.keys())
        if crypto_only:
            # Only update crypto positions outside market hours
            symbols = [s for s in symbols if portfolio.positions[s].asset_type == "crypto"]

        if symbols:
            print(f"  [1/4] Updating prices for {len(symbols)} positions...")
            prices = DataFetcher.get_current_prices(symbols)
            valid = {k: v for k, v in prices.items() if v is not None}
            portfolio.update_prices(prices)
            portfolio.save()
            print(f"        Updated {len(valid)}/{len(symbols)} prices")
        else:
            print(f"  [1/4] No positions to update in current mode")
    else:
        print(f"  [1/4] No open positions")

    # 2. Scan for signals
    if crypto_only:
        # Only scan crypto watchlist outside market hours
        original_watchlist = bot.watchlist
        bot.watchlist = [w for w in bot.watchlist if w["type"] == "crypto"]
        buy_signals, sell_signals, all_signals = bot.run_scan(portfolio)
        bot.watchlist = original_watchlist
    else:
        buy_signals, sell_signals, all_signals = bot.run_scan(portfolio)

    # 3. Execute trades
    executed = []
    if not scan_only and (buy_signals or sell_signals):
        print(f"\n  [3/4] Executing trades...")
        executed = bot.execute_signals(portfolio, buy_signals, sell_signals)
        print(f"        Executed {len(executed)} trades")
    elif scan_only:
        print(f"\n  [3/4] Scan-only mode — no trades executed")
    else:
        print(f"\n  [3/4] No actionable signals")

    # 4. Regenerate dashboard
    print(f"  [4/4] Refreshing dashboard...")
    signals_data = bot.get_signals_summary()
    generate_dashboard(signals_data=signals_data)

    # Cycle summary
    elapsed = time.time() - cycle_start
    summary = portfolio.get_summary()
    pnl_sign = "+" if summary["total_pnl"] >= 0 else ""

    print(f"\n  ┌─────────────────────────────────────────┐")
    print(f"  │  Portfolio: ${summary['total_value']:>10,.2f}  ({pnl_sign}{summary['total_return_pct']:.2f}%)")
    print(f"  │  Cash:      ${summary['cash']:>10,.2f}  │  Positions: {summary['num_positions']}")
    print(f"  │  Trades this cycle: {len(executed):>3}   │  Cycle time: {elapsed:.1f}s")
    print(f"  └─────────────────────────────────────────┘")

    return len(executed)


def save_session_log(log_entries):
    """Save session log to a JSON file for review."""
    log_file = Path(__file__).parent / "session_log.json"
    try:
        existing = []
        if log_file.exists():
            with open(log_file) as f:
                existing = json.load(f)
        existing.extend(log_entries)
        # Keep last 500 entries
        existing = existing[-500:]
        with open(log_file, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def main():
    global running

    print_live_banner()

    # Parse args
    args = sys.argv[1:]
    interval_min = 15  # Default: scan every 15 minutes
    scan_only = "--scan-only" in args
    extended = "--extended" in args
    crypto_247 = "--crypto-247" in args

    for i, arg in enumerate(args):
        if arg == "--interval" and i + 1 < len(args):
            try:
                interval_min = int(args[i + 1])
            except ValueError:
                print("  [!] Invalid interval, using default 15 minutes")

    interval_sec = interval_min * 60

    # Load config and initialize
    config = load_config()
    portfolio = Portfolio.load(starting_cash=config["starting_cash"])
    bot = OpenClawBot(config)

    # Print session info
    eastern_now = get_eastern_now()
    mode_str = "SCAN ONLY" if scan_only else "LIVE TRADING"
    hours_str = "EXTENDED (8AM-6PM ET)" if extended else "REGULAR (9:30AM-4PM ET)"
    crypto_str = " + CRYPTO 24/7" if crypto_247 else ""

    print(f"  Mode:      {mode_str}")
    print(f"  Hours:     {hours_str}{crypto_str}")
    print(f"  Interval:  Every {interval_min} minutes")
    print(f"  Time (ET): {eastern_now.strftime('%A %Y-%m-%d %H:%M')}")
    print(f"  Portfolio: ${portfolio.total_value:,.2f} ({portfolio.num_positions} positions)")
    print(f"\n  Press Ctrl+C to stop.\n")

    session_log = []
    total_trades = 0
    cycles = 0

    while running:
        in_market = is_market_hours(extended=extended)
        is_wkday = is_weekday()

        if in_market:
            # === MARKET HOURS: Full scan + trade ===
            trades = run_cycle(config, portfolio, bot, scan_only=scan_only)
            total_trades += trades
            cycles += 1

            session_log.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "mode": "market",
                "trades_executed": trades,
                "portfolio_value": portfolio.total_value,
            })

            # Wait for next cycle
            if running:
                next_time = datetime.datetime.now() + datetime.timedelta(seconds=interval_sec)
                print(f"\n  Next scan at {next_time.strftime('%H:%M:%S')} "
                      f"({interval_min}m)  |  Session: {cycles} cycles, {total_trades} trades")

                # Sleep in small increments so Ctrl+C is responsive
                wait_until = time.time() + interval_sec
                while running and time.time() < wait_until:
                    time.sleep(min(5, wait_until - time.time()))

        elif crypto_247 and is_wkday:
            # === AFTER HOURS: Crypto only ===
            print(f"\n  Market closed — running crypto-only cycle...")
            trades = run_cycle(config, portfolio, bot, scan_only=scan_only, crypto_only=True)
            total_trades += trades
            cycles += 1

            session_log.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "mode": "crypto_only",
                "trades_executed": trades,
                "portfolio_value": portfolio.total_value,
            })

            if running:
                # Longer interval for after-hours crypto
                crypto_wait = interval_sec * 2
                next_time = datetime.datetime.now() + datetime.timedelta(seconds=crypto_wait)
                print(f"\n  Next crypto scan at {next_time.strftime('%H:%M:%S')} "
                      f"({interval_min * 2}m)")

                wait_until = time.time() + crypto_wait
                while running and time.time() < wait_until:
                    time.sleep(min(5, wait_until - time.time()))

        else:
            # === MARKET CLOSED: Wait ===
            secs, next_open = time_until_market_open(extended=extended)
            dur = format_duration(secs)

            if not is_wkday:
                print(f"\n  Weekend — market opens {next_open.strftime('%A at %I:%M %p ET')} ({dur})")
            else:
                print(f"\n  Market closed — opens at {next_open.strftime('%I:%M %p ET')} ({dur})")

            if crypto_247:
                print(f"  Crypto trading continues in the background.")

            # Check every 60 seconds if we should wake up
            check_interval = 60
            while running and not is_market_hours(extended=extended):
                time.sleep(min(check_interval, 60))

                # If crypto 24/7 mode, do occasional crypto cycles even on weekends
                if crypto_247 and running:
                    elapsed_wait = 0
                    while running and elapsed_wait < interval_sec * 4 and not is_market_hours(extended=extended):
                        time.sleep(min(30, interval_sec * 4 - elapsed_wait))
                        elapsed_wait += 30

                    if running and not is_market_hours(extended=extended):
                        print(f"\n  Running weekend crypto cycle...")
                        trades = run_cycle(config, portfolio, bot, scan_only=scan_only, crypto_only=True)
                        total_trades += trades
                        cycles += 1

    # === SHUTDOWN ===
    print(f"\n{'═'*60}")
    print(f"  SESSION COMPLETE")
    print(f"{'═'*60}")
    print(f"  Total Cycles:  {cycles}")
    print(f"  Total Trades:  {total_trades}")

    summary = portfolio.get_summary()
    pnl_sign = "+" if summary["total_pnl"] >= 0 else ""
    print(f"  Final Value:   ${summary['total_value']:,.2f}")
    print(f"  Session P&L:   {pnl_sign}${summary['total_pnl']:,.2f} ({pnl_sign}{summary['total_return_pct']:.2f}%)")
    print(f"  Win Rate:      {summary['win_rate']:.1f}%")
    print(f"{'═'*60}")

    # Save session log
    save_session_log(session_log)
    print(f"  Session log saved to session_log.json")

    # Final dashboard update
    print(f"  Generating final dashboard...")
    generate_dashboard()
    print(f"  Done. Goodbye!\n")


if __name__ == "__main__":
    main()
