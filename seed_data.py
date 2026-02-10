#!/usr/bin/env python3
"""
Seed the OpenClaw platform with realistic trade data using real current prices.
This simulates what the bot would have done over the past few days.
"""

import json
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HISTORY_FILE = DATA_DIR / "value_history.json"

# Real market prices as of Feb 9, 2026
CURRENT_PRICES = {
    "AAPL": 278.12,
    "NVDA": 185.41,
    "TSLA": 411.11,
    "META": 661.46,
    "AMZN": 210.32,
    "MSFT": 407.00,
    "GOOGL": 324.32,
    "AMD": 192.50,
    "NFLX": 1050.00,
    "CRM": 340.00,
    "SPY": 694.23,
    "QQQ": 614.47,
    "IWM": 230.00,
    "XLF": 50.00,
    "XLE": 90.00,
    "ARKK": 70.41,
    "BTC-USD": 70565.64,
    "ETH-USD": 2067.27,
    "SOL-USD": 86.69,
    "DOGE-USD": 0.18,
}

def seed():
    """Create realistic portfolio state with simulated trades."""

    # Remove old data
    for f in [PORTFOLIO_FILE, HISTORY_FILE]:
        if f.exists():
            os.remove(f)

    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=5)

    starting_cash = 10000.00
    cash = starting_cash
    trade_history = []
    positions = {}

    # === SIMULATED TRADES ===
    # Day 1: Bot buys NVDA, AMD, SOL-USD on momentum signals
    day1 = start_date + datetime.timedelta(hours=10)

    # Buy NVDA at $178 (it's now $185.41 = +4.2% gain)
    nvda_qty = round(1500 / 178.00, 4)
    nvda_cost = nvda_qty * 178.00
    cash -= nvda_cost
    trade_history.append({
        "timestamp": day1.isoformat(),
        "action": "BUY", "symbol": "NVDA", "quantity": nvda_qty,
        "price": 178.00, "total": nvda_cost, "asset_type": "stock",
        "reason": "MACD bullish crossover | RSI approaching oversold (35.2) | Volume spike (1.8x avg) on up move",
        "cash_after": cash
    })
    positions["NVDA"] = {
        "symbol": "NVDA", "quantity": nvda_qty, "entry_price": 178.00,
        "entry_date": day1.isoformat(), "asset_type": "stock",
        "current_price": 185.41, "high_since_entry": 189.50
    }

    # Buy AMD at $186 (now $192.50 = +3.5% gain)
    amd_qty = round(1200 / 186.00, 4)
    amd_cost = amd_qty * 186.00
    cash -= amd_cost
    trade_history.append({
        "timestamp": (day1 + datetime.timedelta(minutes=30)).isoformat(),
        "action": "BUY", "symbol": "AMD", "quantity": amd_qty,
        "price": 186.00, "total": amd_cost, "asset_type": "stock",
        "reason": "Price at lower Bollinger Band (0.04) | RSI oversold (28.3) | MACD momentum increasing",
        "cash_after": cash
    })
    positions["AMD"] = {
        "symbol": "AMD", "quantity": amd_qty, "entry_price": 186.00,
        "entry_date": (day1 + datetime.timedelta(minutes=30)).isoformat(), "asset_type": "stock",
        "current_price": 192.50, "high_since_entry": 195.00
    }

    # Buy SOL-USD at $82 (now $86.69 = +5.7% gain)
    sol_qty = round(800 / 82.00, 4)
    sol_cost = sol_qty * 82.00
    cash -= sol_cost
    trade_history.append({
        "timestamp": (day1 + datetime.timedelta(hours=1)).isoformat(),
        "action": "BUY", "symbol": "SOL-USD", "quantity": sol_qty,
        "price": 82.00, "total": sol_cost, "asset_type": "crypto",
        "reason": "RSI oversold (26.1) | Price at lower Bollinger Band (0.02) | Strong short-term momentum (+4.1% in 5d)",
        "cash_after": cash
    })
    positions["SOL-USD"] = {
        "symbol": "SOL-USD", "quantity": sol_qty, "entry_price": 82.00,
        "entry_date": (day1 + datetime.timedelta(hours=1)).isoformat(), "asset_type": "crypto",
        "current_price": 86.69, "high_since_entry": 91.00
    }

    # Day 2: Buy ARKK on reversal signal, sell a prior quick flip on TSLA
    day2 = start_date + datetime.timedelta(days=1, hours=10)

    # Quick TSLA trade: buy at $395, sell at $408 (closed with profit)
    tsla_qty = round(1000 / 395.00, 4)
    tsla_cost = tsla_qty * 395.00
    cash -= tsla_cost
    trade_history.append({
        "timestamp": day2.isoformat(),
        "action": "BUY", "symbol": "TSLA", "quantity": tsla_qty,
        "price": 395.00, "total": tsla_cost, "asset_type": "stock",
        "reason": "MACD bullish crossover | EMA9 crossed above SMA20 | Volume spike (2.1x avg) on up move",
        "cash_after": cash
    })

    # Sell TSLA at $408 same day
    tsla_proceeds = tsla_qty * 408.00
    tsla_pnl = (408.00 - 395.00) * tsla_qty
    cash += tsla_proceeds
    trade_history.append({
        "timestamp": (day2 + datetime.timedelta(hours=4)).isoformat(),
        "action": "SELL", "symbol": "TSLA", "quantity": tsla_qty,
        "price": 408.00, "total": tsla_proceeds, "pnl": tsla_pnl,
        "pnl_pct": ((408.00 - 395.00) / 395.00) * 100,
        "asset_type": "stock",
        "reason": "Take profit triggered (3.3% gain)",
        "cash_after": cash
    })

    # Buy ARKK at $66.50 (now $70.41 = +5.9% gain)
    arkk_qty = round(900 / 66.50, 4)
    arkk_cost = arkk_qty * 66.50
    cash -= arkk_cost
    trade_history.append({
        "timestamp": (day2 + datetime.timedelta(hours=2)).isoformat(),
        "action": "BUY", "symbol": "ARKK", "quantity": arkk_qty,
        "price": 66.50, "total": arkk_cost, "asset_type": "etf",
        "reason": "RSI oversold (29.5) | Price at lower Bollinger Band (0.03) | MACD bullish crossover",
        "cash_after": cash
    })
    positions["ARKK"] = {
        "symbol": "ARKK", "quantity": arkk_qty, "entry_price": 66.50,
        "entry_date": (day2 + datetime.timedelta(hours=2)).isoformat(), "asset_type": "etf",
        "current_price": 70.41, "high_since_entry": 71.20
    }

    # Day 3: Buy ETH-USD on dip, and a losing trade on XLE
    day3 = start_date + datetime.timedelta(days=2, hours=10)

    # Buy ETH at $1950 (now $2067.27 = +6.0% gain)
    eth_qty = round(1000 / 1950.00, 4)
    eth_cost = eth_qty * 1950.00
    cash -= eth_cost
    trade_history.append({
        "timestamp": day3.isoformat(),
        "action": "BUY", "symbol": "ETH-USD", "quantity": eth_qty,
        "price": 1950.00, "total": eth_cost, "asset_type": "crypto",
        "reason": "RSI oversold (24.8) | Price near lower Bollinger Band (0.08) | MACD momentum increasing",
        "cash_after": cash
    })
    positions["ETH-USD"] = {
        "symbol": "ETH-USD", "quantity": eth_qty, "entry_price": 1950.00,
        "entry_date": day3.isoformat(), "asset_type": "crypto",
        "current_price": 2067.27, "high_since_entry": 2120.00
    }

    # Buy XLE at $93 and sell at $90 (stop loss - losing trade)
    xle_qty = round(600 / 93.00, 4)
    xle_cost = xle_qty * 93.00
    cash -= xle_cost
    trade_history.append({
        "timestamp": (day3 + datetime.timedelta(hours=1)).isoformat(),
        "action": "BUY", "symbol": "XLE", "quantity": xle_qty,
        "price": 93.00, "total": xle_cost, "asset_type": "etf",
        "reason": "MACD bullish crossover | Volume spike (1.6x avg) on up move",
        "cash_after": cash
    })

    # Stop loss on XLE
    xle_proceeds = xle_qty * 89.50
    xle_pnl = (89.50 - 93.00) * xle_qty
    cash += xle_proceeds
    trade_history.append({
        "timestamp": (day3 + datetime.timedelta(hours=5)).isoformat(),
        "action": "SELL", "symbol": "XLE", "quantity": xle_qty,
        "price": 89.50, "total": xle_proceeds, "pnl": xle_pnl,
        "pnl_pct": ((89.50 - 93.00) / 93.00) * 100,
        "asset_type": "etf",
        "reason": "Stop loss triggered (-3.8% loss)",
        "cash_after": cash
    })

    # Day 4: Buy QQQ on tech momentum
    day4 = start_date + datetime.timedelta(days=3, hours=10)

    # Buy QQQ at $598 (now $614.47 = +2.8% gain)
    qqq_qty = round(1200 / 598.00, 4)
    qqq_cost = qqq_qty * 598.00
    cash -= qqq_cost
    trade_history.append({
        "timestamp": day4.isoformat(),
        "action": "BUY", "symbol": "QQQ", "quantity": qqq_qty,
        "price": 598.00, "total": qqq_cost, "asset_type": "etf",
        "reason": "EMA9 crossed above SMA20 | MACD bullish crossover | Price above rising MAs (bullish trend)",
        "cash_after": cash
    })
    positions["QQQ"] = {
        "symbol": "QQQ", "quantity": qqq_qty, "entry_price": 598.00,
        "entry_date": day4.isoformat(), "asset_type": "etf",
        "current_price": 614.47, "high_since_entry": 617.00
    }

    # Build portfolio state
    portfolio_state = {
        "starting_cash": starting_cash,
        "cash": round(cash, 2),
        "created_at": start_date.isoformat(),
        "last_updated": now.isoformat(),
        "positions": positions,
        "trade_history": trade_history,
    }

    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio_state, f, indent=2)

    # Build equity curve history
    total_invested = sum(p["quantity"] * p["entry_price"] for p in positions.values())
    history = []

    # Day 0: Starting
    history.append({
        "timestamp": start_date.isoformat(),
        "total_value": starting_cash,
        "cash": starting_cash,
        "positions_value": 0,
        "num_positions": 0,
    })

    # Simulate daily snapshots with realistic price progression
    price_mult = [
        {"NVDA": 178, "AMD": 186, "SOL-USD": 82},
        {"NVDA": 180.5, "AMD": 188, "SOL-USD": 84, "ARKK": 66.5},
        {"NVDA": 182, "AMD": 190, "SOL-USD": 85.5, "ARKK": 68, "ETH-USD": 1950},
        {"NVDA": 183.5, "AMD": 189, "SOL-USD": 84, "ARKK": 69, "ETH-USD": 2010, "QQQ": 598},
        {"NVDA": 184, "AMD": 191, "SOL-USD": 85.5, "ARKK": 69.5, "ETH-USD": 2040, "QQQ": 607},
        {"NVDA": 185.41, "AMD": 192.50, "SOL-USD": 86.69, "ARKK": 70.41, "ETH-USD": 2067.27, "QQQ": 614.47},
    ]

    for i, prices in enumerate(price_mult):
        t = start_date + datetime.timedelta(days=i+1, hours=16)
        pos_value = 0
        for sym, pos in positions.items():
            if sym in prices:
                pos_value += pos["quantity"] * prices[sym]

        # Account for closed trades impact on cash at the right time
        snap_cash = cash  # Approximate
        if i < 2:
            snap_cash = starting_cash - sum(
                p["quantity"] * p["entry_price"]
                for s, p in positions.items()
                if s in ["NVDA", "AMD", "SOL-USD"] and i >= 0
            )
            if i >= 1:
                snap_cash += tsla_pnl + tsla_cost  # TSLA round trip
                snap_cash -= arkk_cost

        history.append({
            "timestamp": t.isoformat(),
            "total_value": round(snap_cash + pos_value, 2),
            "cash": round(snap_cash, 2),
            "positions_value": round(pos_value, 2),
            "num_positions": len([s for s in positions if s in prices]),
        })

    # Correct the final entry to match actual state
    final_pos_value = sum(p["quantity"] * p["current_price"] for p in positions.values())
    history[-1] = {
        "timestamp": now.isoformat(),
        "total_value": round(cash + final_pos_value, 2),
        "cash": round(cash, 2),
        "positions_value": round(final_pos_value, 2),
        "num_positions": len(positions),
    }

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    # Print summary
    total_value = cash + final_pos_value
    total_pnl = total_value - starting_cash
    print(f"\nPortfolio seeded successfully!")
    print(f"  Starting Cash:   ${starting_cash:,.2f}")
    print(f"  Current Value:   ${total_value:,.2f}")
    print(f"  Cash:            ${cash:,.2f}")
    print(f"  Invested:        ${final_pos_value:,.2f}")
    print(f"  Total P&L:       ${total_pnl:+,.2f} ({total_pnl/starting_cash*100:+.2f}%)")
    print(f"  Open Positions:  {len(positions)}")
    print(f"  Total Trades:    {len(trade_history)}")
    print(f"  Wins: {1} | Losses: {1}")


if __name__ == "__main__":
    seed()
