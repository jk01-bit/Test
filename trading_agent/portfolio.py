"""Portfolio: cash, open positions, realized P&L, and persistence.

This is the bookkeeping core. It does NOT decide trades (the analyst does) and
does NOT enforce risk (risk.py does) — it just tracks state faithfully.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass
class Position:
    ticker: str
    qty: int
    avg_price: float
    stop_loss: float
    target: float
    opened_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def market_value(self, price: float) -> float:
        return self.qty * price

    def unrealized(self, price: float) -> float:
        return (price - self.avg_price) * self.qty


class Portfolio:
    def __init__(self, starting_capital: float):
        self.starting_capital = starting_capital
        self.cash = starting_capital
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = 0.0
        self.trades: List[dict] = []
        # Realized P&L booked today — drives the daily circuit breaker.
        self.day = date.today().isoformat()
        self.realized_today = 0.0

    # --- valuation ---------------------------------------------------------
    def equity(self, prices: Dict[str, float]) -> float:
        holdings = sum(
            pos.market_value(prices.get(t, pos.avg_price))
            for t, pos in self.positions.items()
        )
        return self.cash + holdings

    def unrealized(self, prices: Dict[str, float]) -> float:
        return sum(
            pos.unrealized(prices.get(t, pos.avg_price))
            for t, pos in self.positions.items()
        )

    # --- day rollover ------------------------------------------------------
    def _roll_day(self) -> None:
        today = date.today().isoformat()
        if today != self.day:
            self.day = today
            self.realized_today = 0.0

    # --- mutations ---------------------------------------------------------
    def open_position(self, ticker: str, qty: int, fill_price: float,
                      cost: float, stop_loss: float, target: float) -> None:
        self.cash -= cost
        self.positions[ticker] = Position(
            ticker=ticker, qty=qty, avg_price=fill_price,
            stop_loss=stop_loss, target=target,
        )
        self._log("BUY", ticker, qty, fill_price, pnl=0.0)

    def close_position(self, ticker: str, fill_price: float,
                       proceeds: float) -> float:
        self._roll_day()
        pos = self.positions.pop(ticker)
        pnl = (fill_price - pos.avg_price) * pos.qty
        self.cash += proceeds
        self.realized_pnl += pnl
        self.realized_today += pnl
        self._log("SELL", ticker, pos.qty, fill_price, pnl=pnl)
        return pnl

    def _log(self, side: str, ticker: str, qty: int, price: float,
             pnl: float) -> None:
        self.trades.append({
            "time": datetime.now().isoformat(timespec="seconds"),
            "side": side, "ticker": ticker, "qty": qty,
            "price": round(price, 2), "pnl": round(pnl, 2),
        })

    # --- persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "starting_capital": self.starting_capital,
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "day": self.day,
            "realized_today": self.realized_today,
            "positions": {t: asdict(p) for t, p in self.positions.items()},
            "trades": self.trades,
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str, starting_capital: float) -> "Portfolio":
        if not os.path.exists(path):
            return cls(starting_capital)
        with open(path) as f:
            data = json.load(f)
        p = cls(data.get("starting_capital", starting_capital))
        p.cash = data.get("cash", starting_capital)
        p.realized_pnl = data.get("realized_pnl", 0.0)
        p.day = data.get("day", date.today().isoformat())
        p.realized_today = data.get("realized_today", 0.0)
        p.trades = data.get("trades", [])
        for t, pd_ in data.get("positions", {}).items():
            p.positions[t] = Position(**pd_)
        p._roll_day()
        return p
