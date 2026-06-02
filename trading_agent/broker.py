"""Broker abstraction.

PaperBroker simulates fills (default, safe). LiveBroker is a deliberate stub —
wiring real orders is a conscious, authenticated step you must implement and
review yourself before any real money moves.
"""
from __future__ import annotations

from dataclasses import dataclass

import config


@dataclass
class Fill:
    ticker: str
    side: str          # "BUY" | "SELL"
    qty: int
    price: float       # fill price incl. slippage
    commission: float

    @property
    def cash_delta(self) -> float:
        """Signed cash impact: negative for buys, positive for sells."""
        gross = self.qty * self.price
        if self.side == "BUY":
            return -(gross + self.commission)
        return gross - self.commission


class PaperBroker:
    """Fills at the current market price plus slippage and a flat commission."""

    mode = "paper"

    def execute(self, ticker: str, side: str, qty: int, market_price: float) -> Fill:
        slip = config.SLIPPAGE_PCT
        # Slippage works against you: pay up on buys, receive less on sells.
        price = market_price * (1 + slip) if side == "BUY" else market_price * (1 - slip)
        return Fill(
            ticker=ticker, side=side, qty=qty,
            price=round(price, 2), commission=config.COMMISSION_PER_ORDER,
        )


class LiveBroker:
    """Placeholder for real-money order routing (e.g. Zerodha Kite Connect).

    Intentionally not implemented. To go live you would:
      1. pip install kiteconnect and add API key/secret/access token to .env
      2. implement execute() using kite.place_order(...)
      3. map NSE tickers (RELIANCE.NS -> tradingsymbol RELIANCE on exchange NSE)
      4. test with tiny size first
    """

    mode = "live"

    def execute(self, ticker: str, side: str, qty: int, market_price: float) -> Fill:
        raise NotImplementedError(
            "Live trading is not wired up. Implement LiveBroker.execute() with "
            "your broker's API, or run with TRADING_MODE=paper."
        )


def get_broker():
    if config.TRADING_MODE == "live":
        return LiveBroker()
    return PaperBroker()
