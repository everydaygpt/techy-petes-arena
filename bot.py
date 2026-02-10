#!/usr/bin/env python3
"""
OpenClaw Bot - Automated trading strategy for short-term gains.
Uses technical indicators (RSI, MACD, Bollinger Bands, Volume) to generate
buy/sell signals and manage positions.
"""

import json
import datetime
import numpy as np
from pathlib import Path

# Import from engine
from engine import Portfolio, DataFetcher


class Signal:
    """Represents a trading signal."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

    def __init__(self, action, symbol, strength, reasons, price=None, asset_type="stock"):
        self.action = action
        self.symbol = symbol
        self.strength = strength  # 0-5 scale
        self.reasons = reasons    # list of strings
        self.price = price
        self.asset_type = asset_type
        self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self):
        return {
            "action": self.action,
            "symbol": self.symbol,
            "strength": self.strength,
            "reasons": self.reasons,
            "price": self.price,
            "asset_type": self.asset_type,
            "timestamp": self.timestamp,
        }


class OpenClawBot:
    """
    The OpenClaw trading bot. Analyzes technical indicators and generates
    buy/sell signals focused on short-term momentum and mean reversion.
    """

    def __init__(self, config):
        self.config = config
        self.strategy = config.get("strategy", {})
        self.watchlist = self._build_watchlist(config.get("watchlist", {}))
        self.max_position_pct = config.get("max_position_pct", 0.15)
        self.max_positions = config.get("max_positions", 12)
        self.stop_loss_pct = config.get("stop_loss_pct", 0.05)
        self.take_profit_pct = config.get("take_profit_pct", 0.10)
        self.trailing_stop_pct = config.get("trailing_stop_pct", 0.03)
        self.min_signal_strength = self.strategy.get("min_signal_strength", 2)
        self.signals_log = []

    def _build_watchlist(self, watchlist_config):
        """Build flat watchlist with asset type tags."""
        items = []
        for symbol in watchlist_config.get("stocks", []):
            items.append({"symbol": symbol, "type": "stock"})
        for symbol in watchlist_config.get("etfs", []):
            items.append({"symbol": symbol, "type": "etf"})
        for symbol in watchlist_config.get("crypto", []):
            items.append({"symbol": symbol, "type": "crypto"})
        return items

    def analyze_symbol(self, symbol, asset_type="stock"):
        """
        Analyze a single symbol and return a Signal.
        Uses multiple technical indicators for confluence.
        """
        df = DataFetcher.get_technical_data(symbol)
        if df is None or len(df) < 30:
            return Signal(Signal.HOLD, symbol, 0, ["Insufficient data"], asset_type=asset_type)

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(latest["Close"])

        buy_reasons = []
        sell_reasons = []
        buy_strength = 0
        sell_strength = 0

        # === RSI Analysis ===
        rsi = latest.get("RSI")
        if rsi is not None and not np.isnan(rsi):
            if rsi < self.strategy.get("rsi_oversold", 30):
                buy_reasons.append(f"RSI oversold ({rsi:.1f})")
                buy_strength += 1.5
            elif rsi < 40:
                buy_reasons.append(f"RSI approaching oversold ({rsi:.1f})")
                buy_strength += 0.5
            elif rsi > self.strategy.get("rsi_overbought", 70):
                sell_reasons.append(f"RSI overbought ({rsi:.1f})")
                sell_strength += 1.5
            elif rsi > 65:
                sell_reasons.append(f"RSI approaching overbought ({rsi:.1f})")
                sell_strength += 0.5

        # === MACD Analysis ===
        macd = latest.get("MACD")
        macd_signal = latest.get("MACD_Signal")
        macd_hist = latest.get("MACD_Hist")
        prev_macd_hist = prev.get("MACD_Hist")

        if all(v is not None and not np.isnan(v) for v in [macd, macd_signal, macd_hist, prev_macd_hist]):
            # Bullish crossover
            if macd_hist > 0 and prev_macd_hist <= 0:
                buy_reasons.append("MACD bullish crossover")
                buy_strength += 1.5
            elif macd_hist > 0 and macd_hist > prev_macd_hist:
                buy_reasons.append("MACD momentum increasing")
                buy_strength += 0.5

            # Bearish crossover
            if macd_hist < 0 and prev_macd_hist >= 0:
                sell_reasons.append("MACD bearish crossover")
                sell_strength += 1.5
            elif macd_hist < 0 and macd_hist < prev_macd_hist:
                sell_reasons.append("MACD momentum decreasing")
                sell_strength += 0.5

        # === Bollinger Band Analysis ===
        bb_pct = latest.get("BB_Pct")
        bb_lower = latest.get("BB_Lower")
        bb_upper = latest.get("BB_Upper")

        if bb_pct is not None and not np.isnan(bb_pct):
            if bb_pct < 0.05:
                buy_reasons.append(f"Price at lower Bollinger Band ({bb_pct:.2f})")
                buy_strength += 1.0
            elif bb_pct < 0.2:
                buy_reasons.append(f"Price near lower Bollinger Band ({bb_pct:.2f})")
                buy_strength += 0.5
            elif bb_pct > 0.95:
                sell_reasons.append(f"Price at upper Bollinger Band ({bb_pct:.2f})")
                sell_strength += 1.0
            elif bb_pct > 0.8:
                sell_reasons.append(f"Price near upper Bollinger Band ({bb_pct:.2f})")
                sell_strength += 0.5

        # === Volume Analysis ===
        vol_ratio = latest.get("Vol_Ratio")
        if vol_ratio is not None and not np.isnan(vol_ratio):
            spike_mult = self.strategy.get("volume_spike_multiplier", 1.5)
            if vol_ratio > spike_mult:
                # High volume confirms the direction
                daily_return = (price - float(prev["Close"])) / float(prev["Close"])
                if daily_return > 0:
                    buy_reasons.append(f"Volume spike ({vol_ratio:.1f}x avg) on up move")
                    buy_strength += 0.75
                else:
                    sell_reasons.append(f"Volume spike ({vol_ratio:.1f}x avg) on down move")
                    sell_strength += 0.75

        # === Moving Average Analysis ===
        sma10 = latest.get("SMA_10")
        sma20 = latest.get("SMA_20")
        ema9 = latest.get("EMA_9")

        if all(v is not None and not np.isnan(v) for v in [sma10, sma20, ema9]):
            if price > sma10 > sma20:
                buy_reasons.append("Price above rising MAs (bullish trend)")
                buy_strength += 0.5
            elif price < sma10 < sma20:
                sell_reasons.append("Price below falling MAs (bearish trend)")
                sell_strength += 0.5

            # EMA9 crossover for short-term momentum
            prev_ema9 = prev.get("EMA_9")
            prev_sma20 = prev.get("SMA_20")
            if prev_ema9 is not None and prev_sma20 is not None:
                if not np.isnan(prev_ema9) and not np.isnan(prev_sma20):
                    if ema9 > sma20 and prev_ema9 <= prev_sma20:
                        buy_reasons.append("EMA9 crossed above SMA20")
                        buy_strength += 0.75
                    elif ema9 < sma20 and prev_ema9 >= prev_sma20:
                        sell_reasons.append("EMA9 crossed below SMA20")
                        sell_strength += 0.75

        # === Momentum (Rate of Change) ===
        roc5 = latest.get("ROC_5")
        roc10 = latest.get("ROC_10")

        if roc5 is not None and not np.isnan(roc5):
            if roc5 > 3 and (roc10 is not None and not np.isnan(roc10) and roc10 > 0):
                buy_reasons.append(f"Strong short-term momentum (+{roc5:.1f}% in 5d)")
                buy_strength += 0.5
            elif roc5 < -3 and (roc10 is not None and not np.isnan(roc10) and roc10 < 0):
                sell_reasons.append(f"Negative momentum ({roc5:.1f}% in 5d)")
                sell_strength += 0.5

        # === Generate final signal ===
        net_strength = buy_strength - sell_strength

        if net_strength >= self.min_signal_strength:
            return Signal(Signal.BUY, symbol, buy_strength, buy_reasons, price=price, asset_type=asset_type)
        elif net_strength <= -self.min_signal_strength:
            return Signal(Signal.SELL, symbol, sell_strength, sell_reasons, price=price, asset_type=asset_type)
        else:
            all_reasons = []
            if buy_reasons:
                all_reasons.append(f"Bullish: {', '.join(buy_reasons)}")
            if sell_reasons:
                all_reasons.append(f"Bearish: {', '.join(sell_reasons)}")
            if not all_reasons:
                all_reasons = ["No significant signals"]
            return Signal(Signal.HOLD, symbol, abs(net_strength), all_reasons, price=price, asset_type=asset_type)

    def check_exit_conditions(self, portfolio):
        """Check if any existing positions should be exited."""
        exit_signals = []

        for symbol, pos in portfolio.positions.items():
            reasons = []
            should_exit = False

            pnl_pct = pos.unrealized_pnl_pct / 100

            # Stop loss
            if pnl_pct <= -self.stop_loss_pct:
                reasons.append(f"Stop loss triggered ({pnl_pct*100:.1f}% loss)")
                should_exit = True

            # Take profit
            if pnl_pct >= self.take_profit_pct:
                reasons.append(f"Take profit triggered ({pnl_pct*100:.1f}% gain)")
                should_exit = True

            # Trailing stop
            if pos.high_since_entry > 0:
                drawdown_from_high = (pos.current_price - pos.high_since_entry) / pos.high_since_entry
                if drawdown_from_high <= -self.trailing_stop_pct and pnl_pct > 0:
                    reasons.append(f"Trailing stop ({drawdown_from_high*100:.1f}% from high)")
                    should_exit = True

            # Also check technical signals for existing positions
            if not should_exit:
                signal = self.analyze_symbol(symbol, pos.asset_type)
                if signal.action == Signal.SELL and signal.strength >= self.min_signal_strength:
                    reasons.extend(signal.reasons)
                    should_exit = True

            if should_exit:
                exit_signals.append(Signal(
                    Signal.SELL, symbol, 5, reasons,
                    price=pos.current_price, asset_type=pos.asset_type
                ))

        return exit_signals

    def calculate_position_size(self, portfolio, price):
        """Calculate how many shares/units to buy based on position sizing rules."""
        max_position_value = portfolio.total_value * self.max_position_pct
        max_spend = min(max_position_value, portfolio.cash * 0.9)  # Keep 10% cash buffer

        if max_spend < price:
            return 0

        # For crypto, allow fractional units
        quantity = max_spend / price

        # For stocks/ETFs, round down to whole shares
        # (For simplicity, we allow fractional for all in this sim)
        quantity = round(quantity, 4)

        return quantity if quantity * price >= 10 else 0  # Min $10 order

    def run_scan(self, portfolio):
        """
        Run a full market scan and return actionable signals.
        Returns (buy_signals, sell_signals, all_signals)
        """
        print(f"\n{'='*60}")
        print(f"  TECHY PETE'S BOT - Market Scan")
        print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        all_signals = []
        buy_signals = []
        sell_signals = []

        # First, check exits for existing positions
        print(f"\n[1] Checking exit conditions for {portfolio.num_positions} positions...")
        exit_signals = self.check_exit_conditions(portfolio)
        for sig in exit_signals:
            print(f"  EXIT {sig.symbol}: {', '.join(sig.reasons)}")
            sell_signals.append(sig)
            all_signals.append(sig)

        # Then scan watchlist for new entries
        print(f"\n[2] Scanning {len(self.watchlist)} symbols for entry signals...")
        for item in self.watchlist:
            symbol = item["symbol"]
            asset_type = item["type"]

            # Skip if we already have a position (exits handled above)
            if symbol in portfolio.positions:
                continue

            # Skip if at max positions
            if portfolio.num_positions >= self.max_positions:
                break

            try:
                signal = self.analyze_symbol(symbol, asset_type)
                all_signals.append(signal)

                if signal.action == Signal.BUY and signal.strength >= self.min_signal_strength:
                    buy_signals.append(signal)
                    print(f"  BUY  {symbol:8s} | Strength: {signal.strength:.1f} | {', '.join(signal.reasons[:2])}")
                elif signal.action == Signal.SELL:
                    print(f"  SELL {symbol:8s} | Strength: {signal.strength:.1f} | {', '.join(signal.reasons[:2])}")
                else:
                    print(f"  HOLD {symbol:8s} | Net: {signal.strength:.1f}")
            except Exception as e:
                print(f"  ERR  {symbol:8s} | {str(e)[:50]}")

        # Sort buy signals by strength (strongest first)
        buy_signals.sort(key=lambda s: s.strength, reverse=True)

        print(f"\n[3] Summary: {len(buy_signals)} buy signals, {len(sell_signals)} sell signals")

        self.signals_log = all_signals
        return buy_signals, sell_signals, all_signals

    def execute_signals(self, portfolio, buy_signals, sell_signals, auto_execute=True):
        """Execute the generated signals against the portfolio."""
        executed = []

        if not auto_execute:
            return executed

        # Execute sells first (free up cash)
        for signal in sell_signals:
            if signal.symbol in portfolio.positions:
                success, msg = portfolio.sell(
                    signal.symbol,
                    price=signal.price,
                    reason=" | ".join(signal.reasons[:3])
                )
                if success:
                    executed.append({"action": "SELL", "symbol": signal.symbol, "message": msg})
                    print(f"  EXECUTED: {msg}")

        # Execute buys (strongest signals first, respect limits)
        for signal in buy_signals:
            if portfolio.num_positions >= self.max_positions:
                print(f"  SKIPPED: {signal.symbol} - max positions reached")
                break

            quantity = self.calculate_position_size(portfolio, signal.price)
            if quantity <= 0:
                print(f"  SKIPPED: {signal.symbol} - insufficient funds or position too small")
                continue

            success, msg = portfolio.buy(
                signal.symbol,
                quantity=quantity,
                price=signal.price,
                asset_type=signal.asset_type,
                reason=" | ".join(signal.reasons[:3])
            )
            if success:
                executed.append({"action": "BUY", "symbol": signal.symbol, "message": msg})
                print(f"  EXECUTED: {msg}")

        return executed

    def get_signals_summary(self):
        """Get all signals as a list of dicts for the dashboard."""
        return [s.to_dict() for s in self.signals_log]


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


if __name__ == "__main__":
    # Quick test run
    config = load_config()
    portfolio = Portfolio.load(starting_cash=config["starting_cash"])
    bot = OpenClawBot(config)

    print(f"Portfolio Value: ${portfolio.total_value:,.2f}")
    print(f"Cash: ${portfolio.cash:,.2f}")
    print(f"Positions: {portfolio.num_positions}")

    buy_signals, sell_signals, all_signals = bot.run_scan(portfolio)

    if buy_signals or sell_signals:
        print("\n[4] Executing trades...")
        executed = bot.execute_signals(portfolio, buy_signals, sell_signals)
        print(f"\nExecuted {len(executed)} trades")

    # Update prices for existing positions
    if portfolio.positions:
        symbols = list(portfolio.positions.keys())
        prices = DataFetcher.get_current_prices(symbols)
        portfolio.update_prices(prices)
        portfolio.save()

    print(f"\nFinal Portfolio Value: ${portfolio.total_value:,.2f}")
    print(f"Total P&L: ${portfolio.total_pnl:,.2f} ({portfolio.total_return_pct:+.2f}%)")
