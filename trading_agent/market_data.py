"""Market data + technical indicators for NSE equities.

Uses yfinance. Each `snapshot()` returns a compact dict the analyst can read:
current price, recent trend (SMA), momentum (RSI), and a short price history.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
    _YF = True
except Exception:  # pragma: no cover - optional at runtime
    _YF = False


def _rsi(close: pd.Series, period: int = 14) -> float:
    """Classic Wilder RSI. Returns the latest value (0-100)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else 50.0


def get_history(ticker: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    if not _YF:
        raise RuntimeError(
            "yfinance is not installed. Run: pip install -r requirements.txt"
        )
    df = yf.download(ticker, period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return None
    # yfinance can return a MultiIndex on the columns for a single ticker.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def snapshot(ticker: str) -> Optional[dict]:
    """Return a compact technical snapshot, or None if data is unavailable."""
    df = get_history(ticker)
    if df is None or len(df) < 50:
        return None

    close = df["Close"].astype(float)
    price = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    rsi14 = _rsi(close)

    prev = float(close.iloc[-2])
    change_pct = (price - prev) / prev * 100 if prev else 0.0

    # 10-session closing history, rounded, for the analyst to eyeball the trend.
    recent = [round(float(x), 2) for x in close.iloc[-10:].tolist()]

    return {
        "ticker": ticker,
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "rsi14": round(rsi14, 1),
        "trend": "up" if sma20 > sma50 else "down",
        "recent_closes": recent,
    }


def get_price(ticker: str) -> Optional[float]:
    snap = snapshot(ticker)
    return snap["price"] if snap else None
