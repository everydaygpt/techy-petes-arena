#!/usr/bin/env python3
"""
Techy Pete's Investment App - Main entry point for the paper trading platform.
Orchestrates the bot scan, trade execution, price updates, and dashboard generation.

Usage:
    python run.py              # Full run: scan, trade, update dashboard
    python run.py --scan-only  # Scan for signals but don't execute trades
    python run.py --update     # Just update prices and dashboard (no trading)
    python run.py --reset      # Reset portfolio to starting cash
    python run.py --status     # Show current portfolio status
"""

import sys
import json
import datetime
import os
from pathlib import Path

# Ensure we can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from engine import Portfolio, DataFetcher
from bot import OpenClawBot, load_config
from generate_dashboard import generate_dashboard


def print_banner():
    banner = """
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
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)


def print_portfolio_status(portfolio):
    """Print a clean portfolio summary."""
    summary = portfolio.get_summary()
    
    pnl_indicator = "+" if summary["total_pnl"] >= 0 else ""
    
    print(f"\n{'─'*50}")
    print(f"  PORTFOLIO STATUS")
    print(f"{'─'*50}")
    print(f"  Total Value:    ${summary['total_value']:>12,.2f}")
    print(f"  Cash:           ${summary['cash']:>12,.2f}")
    print(f"  Invested:       ${summary['positions_value']:>12,.2f}")
    print(f"  Total P&L:      {pnl_indicator}${summary['total_pnl']:>11,.2f} ({summary['total_return_pct']:+.2f}%)")
    print(f"  Realized P&L:   ${summary['realized_pnl']:>12,.2f}")
    print(f"  Unrealized P&L: ${summary['unrealized_pnl']:>12,.2f}")
    print(f"  Open Positions: {summary['num_positions']:>13}")
    print(f"  Total Trades:   {summary['num_trades']:>13}")
    print(f"  Win Rate:       {summary['win_rate']:>12.1f}%")
    print(f"{'─'*50}")
    
    if summary["positions"]:
        print(f"\n  OPEN POSITIONS:")
        print(f"  {'Symbol':<8} {'Type':<6} {'Qty':>8} {'Entry':>10} {'Current':>10} {'P&L':>12}")
        print(f"  {'─'*54}")
        for p in sorted(summary["positions"], key=lambda x: x["unrealized_pnl"], reverse=True):
            pnl_str = f"${p['unrealized_pnl']:+.2f}"
            print(f"  {p['symbol']:<8} {p['asset_type']:<6} {p['quantity']:>8.2f} ${p['entry_price']:>9.2f} ${p['current_price']:>9.2f} {pnl_str:>12}")


def run_full(config, scan_only=False):
    """Run a full bot cycle: scan, (optionally) trade, update, dashboard."""
    portfolio = Portfolio.load(starting_cash=config["starting_cash"])
    bot = OpenClawBot(config)
    
    print_portfolio_status(portfolio)
    
    # Update existing position prices first
    if portfolio.positions:
        print("\n[*] Updating current prices for existing positions...")
        symbols = list(portfolio.positions.keys())
        prices = DataFetcher.get_current_prices(symbols)
        portfolio.update_prices(prices)
        portfolio.save()
        valid = {k: v for k, v in prices.items() if v is not None}
        print(f"    Updated {len(valid)}/{len(symbols)} positions")
    
    # Run the bot scan
    buy_signals, sell_signals, all_signals = bot.run_scan(portfolio)
    
    # Execute trades (unless scan-only)
    if not scan_only and (buy_signals or sell_signals):
        print(f"\n[4] Executing trades...")
        executed = bot.execute_signals(portfolio, buy_signals, sell_signals)
        print(f"    Executed {len(executed)} trades")
    elif scan_only:
        print(f"\n[*] Scan-only mode - no trades executed")
    
    # Final status
    print_portfolio_status(portfolio)
    
    # Generate dashboard
    print(f"\n[*] Generating dashboard...")
    signals_data = bot.get_signals_summary()
    dashboard_path = generate_dashboard(signals_data=signals_data)
    print(f"    Dashboard saved to: {dashboard_path}")
    
    return portfolio


def run_update(config):
    """Update prices and regenerate dashboard without trading."""
    portfolio = Portfolio.load(starting_cash=config["starting_cash"])
    
    if portfolio.positions:
        print("[*] Updating current prices...")
        symbols = list(portfolio.positions.keys())
        prices = DataFetcher.get_current_prices(symbols)
        portfolio.update_prices(prices)
        portfolio.save()
    
    print_portfolio_status(portfolio)
    
    print("[*] Regenerating dashboard...")
    generate_dashboard()
    print("    Done!")


def run_reset(config):
    """Reset portfolio to starting cash."""
    portfolio_file = Path(__file__).parent / "portfolio.json"
    history_file = Path(__file__).parent / "value_history.json"
    
    if portfolio_file.exists():
        os.remove(portfolio_file)
    if history_file.exists():
        os.remove(history_file)
    
    portfolio = Portfolio(starting_cash=config["starting_cash"])
    portfolio.save()
    
    print(f"Portfolio reset to ${config['starting_cash']:,.2f}")
    generate_dashboard()
    print("Dashboard regenerated.")


def main():
    print_banner()
    
    config = load_config()
    
    args = sys.argv[1:]
    
    if "--reset" in args:
        confirm = input("Are you sure you want to reset the portfolio? (yes/no): ")
        if confirm.lower() == "yes":
            run_reset(config)
        else:
            print("Reset cancelled.")
    elif "--status" in args:
        portfolio = Portfolio.load(starting_cash=config["starting_cash"])
        print_portfolio_status(portfolio)
    elif "--update" in args:
        run_update(config)
    elif "--scan-only" in args:
        run_full(config, scan_only=True)
    else:
        run_full(config, scan_only=False)


if __name__ == "__main__":
    main()
