#!/usr/bin/env python3
"""
OpenClaw Trading Engine - Core portfolio management and data fetching.
Handles simulated trade execution, position tracking, and real market data.
"""

import json
import os
import datetime
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).parent
PORTFOLIO_FILE = DEFAULT_DATA_DIR / "portfolio.json"
HISTORY_FILE = DEFAULT_DATA_DIR / "value_history.json"


class Position:
    """Represents a single position in the portfolio."""
    
    def __init__(self, symbol, quantity, entry_price, entry_date, asset_type="stock"):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.asset_type = asset_type
        self.current_price = entry_price
        self.high_since_entry = entry_price
    
    @property
    def market_value(self):
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self):
        return self.quantity * self.entry_price
    
    @property
    def unrealized_pnl(self):
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self):
        if self.cost_basis == 0:
            return 0
        return (self.unrealized_pnl / self.cost_basis) * 100
    
    def to_dict(self):
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_date": self.entry_date,
            "asset_type": self.asset_type,
            "current_price": self.current_price,
            "high_since_entry": self.high_since_entry,
        }
    
    @classmethod
    def from_dict(cls, d):
        pos = cls(
            symbol=d["symbol"],
            quantity=d["quantity"],
            entry_price=d["entry_price"],
            entry_date=d["entry_date"],
            asset_type=d.get("asset_type", "stock"),
        )
        pos.current_price = d.get("current_price", d["entry_price"])
        pos.high_since_entry = d.get("high_since_entry", d["entry_price"])
        return pos


class Portfolio:
    """Manages the complete paper trading portfolio."""

    def __init__(self, starting_cash=10000.0, data_dir=None):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.positions = {}  # symbol -> Position
        self.trade_history = []
        self.created_at = datetime.datetime.now().isoformat()
        self.last_updated = self.created_at
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.history_file = self.data_dir / "value_history.json"
    
    @property
    def total_positions_value(self):
        return sum(p.market_value for p in self.positions.values())
    
    @property
    def total_value(self):
        return self.cash + self.total_positions_value
    
    @property
    def total_pnl(self):
        return self.total_value - self.starting_cash
    
    @property
    def total_return_pct(self):
        if self.starting_cash == 0:
            return 0
        return (self.total_pnl / self.starting_cash) * 100
    
    @property
    def num_positions(self):
        return len(self.positions)
    
    def buy(self, symbol, quantity, price, asset_type="stock", reason=""):
        """Execute a simulated buy order."""
        cost = quantity * price
        if cost > self.cash:
            return False, f"Insufficient cash. Need ${cost:.2f}, have ${self.cash:.2f}"
        
        self.cash -= cost
        
        if symbol in self.positions:
            # Average into existing position
            existing = self.positions[symbol]
            total_qty = existing.quantity + quantity
            avg_price = ((existing.quantity * existing.entry_price) + (quantity * price)) / total_qty
            existing.quantity = total_qty
            existing.entry_price = avg_price
            existing.current_price = price
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_date=datetime.datetime.now().isoformat(),
                asset_type=asset_type,
            )
        
        trade = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "total": cost,
            "asset_type": asset_type,
            "reason": reason,
            "cash_after": self.cash,
        }
        self.trade_history.append(trade)
        self.last_updated = datetime.datetime.now().isoformat()
        self.save()
        return True, f"Bought {quantity} {symbol} @ ${price:.2f} (${cost:.2f})"
    
    def sell(self, symbol, quantity=None, price=None, reason=""):
        """Execute a simulated sell order. Sells all if quantity is None."""
        if symbol not in self.positions:
            return False, f"No position in {symbol}"
        
        pos = self.positions[symbol]
        if quantity is None:
            quantity = pos.quantity
        
        if quantity > pos.quantity:
            return False, f"Only have {pos.quantity} shares of {symbol}"
        
        if price is None:
            price = pos.current_price
        
        proceeds = quantity * price
        pnl = (price - pos.entry_price) * quantity
        
        self.cash += proceeds
        
        trade = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": "SELL",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "total": proceeds,
            "pnl": pnl,
            "pnl_pct": ((price - pos.entry_price) / pos.entry_price) * 100,
            "asset_type": pos.asset_type,
            "reason": reason,
            "cash_after": self.cash,
        }
        self.trade_history.append(trade)
        
        if quantity >= pos.quantity:
            del self.positions[symbol]
        else:
            pos.quantity -= quantity
        
        self.last_updated = datetime.datetime.now().isoformat()
        self.save()
        return True, f"Sold {quantity} {symbol} @ ${price:.2f} (${proceeds:.2f}, PnL: ${pnl:.2f})"
    
    def update_prices(self, price_map):
        """Update current prices for all positions."""
        for symbol, pos in self.positions.items():
            if symbol in price_map and price_map[symbol] is not None:
                pos.current_price = price_map[symbol]
                if pos.current_price > pos.high_since_entry:
                    pos.high_since_entry = pos.current_price
        self.last_updated = datetime.datetime.now().isoformat()
    
    def get_summary(self):
        """Get portfolio summary as a dict."""
        positions_list = []
        for sym, pos in sorted(self.positions.items()):
            positions_list.append({
                "symbol": sym,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "cost_basis": pos.cost_basis,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "asset_type": pos.asset_type,
                "entry_date": pos.entry_date,
            })
        
        realized_pnl = sum(t.get("pnl", 0) for t in self.trade_history if t["action"] == "SELL")
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        wins = [t for t in self.trade_history if t["action"] == "SELL" and t.get("pnl", 0) > 0]
        losses = [t for t in self.trade_history if t["action"] == "SELL" and t.get("pnl", 0) <= 0]
        total_closed = len(wins) + len(losses)
        
        return {
            "total_value": self.total_value,
            "cash": self.cash,
            "positions_value": self.total_positions_value,
            "total_pnl": self.total_pnl,
            "total_return_pct": self.total_return_pct,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "num_positions": self.num_positions,
            "num_trades": len(self.trade_history),
            "win_rate": (len(wins) / total_closed * 100) if total_closed > 0 else 0,
            "positions": positions_list,
            "starting_cash": self.starting_cash,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }
    
    def save(self):
        """Save portfolio state to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "starting_cash": self.starting_cash,
            "cash": self.cash,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "positions": {sym: pos.to_dict() for sym, pos in self.positions.items()},
            "trade_history": self.trade_history,
        }
        with open(self.portfolio_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

        # Also save value snapshot for equity curve
        self._save_value_snapshot()

    def _save_value_snapshot(self):
        """Append current value to history for equity curve tracking."""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        snapshot = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_value": self.total_value,
            "cash": self.cash,
            "positions_value": self.total_positions_value,
            "num_positions": self.num_positions,
        }

        # Only add if it's been at least 1 hour since last snapshot or value changed significantly
        if history:
            last = history[-1]
            last_time = datetime.datetime.fromisoformat(last["timestamp"])
            now = datetime.datetime.now()
            value_change = abs(self.total_value - last["total_value"])
            if (now - last_time).total_seconds() < 3600 and value_change < 1:
                return

        history.append(snapshot)
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    @classmethod
    def load(cls, starting_cash=10000.0, data_dir=None):
        """Load portfolio from disk, or create new one."""
        portfolio = cls(starting_cash=starting_cash, data_dir=data_dir)

        if not portfolio.portfolio_file.exists():
            portfolio.save()
            return portfolio

        try:
            with open(portfolio.portfolio_file) as f:
                state = json.load(f)

            portfolio.starting_cash = state.get("starting_cash", starting_cash)
            portfolio.cash = state["cash"]
            portfolio.created_at = state.get("created_at", datetime.datetime.now().isoformat())
            portfolio.last_updated = state.get("last_updated", datetime.datetime.now().isoformat())
            portfolio.trade_history = state.get("trade_history", [])

            for sym, pos_data in state.get("positions", {}).items():
                portfolio.positions[sym] = Position.from_dict(pos_data)

            return portfolio
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"Error loading portfolio, creating new one: {e}")
            portfolio = cls(starting_cash=starting_cash, data_dir=data_dir)
            portfolio.save()
            return portfolio


class DataFetcher:
    """Fetches real market data using yfinance."""
    
    @staticmethod
    def get_current_prices(symbols):
        """Get current/latest prices for a list of symbols."""
        prices = {}
        if not symbols:
            return prices
        
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        price = getattr(info, 'last_price', None)
                        if price is None or price == 0:
                            # Fallback: try history
                            hist = ticker.history(period="1d")
                            if not hist.empty:
                                price = hist["Close"].iloc[-1]
                        prices[symbol] = float(price) if price else None
                    else:
                        prices[symbol] = None
                except Exception:
                    prices[symbol] = None
        except Exception as e:
            print(f"Error fetching prices: {e}")
            # Try one by one as fallback
            for symbol in symbols:
                try:
                    t = yf.Ticker(symbol)
                    hist = t.history(period="2d")
                    if not hist.empty:
                        prices[symbol] = float(hist["Close"].iloc[-1])
                    else:
                        prices[symbol] = None
                except Exception:
                    prices[symbol] = None
        
        return prices
    
    @staticmethod
    def get_historical_data(symbol, period="60d", interval="1d"):
        """Get historical OHLCV data for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return None
            return df
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return None
    
    @staticmethod
    def get_technical_data(symbol, period="60d"):
        """Get historical data with calculated technical indicators."""
        df = DataFetcher.get_historical_data(symbol, period=period)
        if df is None or len(df) < 26:
            return None
        
        # RSI
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.inf)
        df["RSI"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
        
        # Bollinger Bands
        df["BB_Mid"] = df["Close"].rolling(window=20).mean()
        bb_std = df["Close"].rolling(window=20).std()
        df["BB_Upper"] = df["BB_Mid"] + (bb_std * 2)
        df["BB_Lower"] = df["BB_Mid"] - (bb_std * 2)
        df["BB_Pct"] = (df["Close"] - df["BB_Lower"]) / (df["BB_Upper"] - df["BB_Lower"])
        
        # Volume analysis
        df["Vol_SMA"] = df["Volume"].rolling(window=20).mean()
        df["Vol_Ratio"] = df["Volume"] / df["Vol_SMA"].replace(0, 1)
        
        # Moving averages
        df["SMA_10"] = df["Close"].rolling(window=10).mean()
        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
        
        # Price momentum
        df["ROC_5"] = df["Close"].pct_change(periods=5) * 100
        df["ROC_10"] = df["Close"].pct_change(periods=10) * 100
        
        return df
    
    @staticmethod
    def classify_asset(symbol):
        """Classify a symbol as stock, etf, or crypto."""
        if "-USD" in symbol or "-usd" in symbol:
            return "crypto"
        # Common ETFs
        etfs = {"SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "XLF", "XLE", "XLK", 
                "XLV", "ARKK", "ARKG", "GLD", "SLV", "TLT", "HYG", "VNQ", "EEM"}
        if symbol.upper() in etfs:
            return "etf"
        return "stock"
