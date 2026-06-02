"""The agent loop: analyse -> risk-check -> execute -> book profits.

One `run_once()` does a full pass:
  1. Manage open positions first (hard stops/targets, then ask the analyst).
  2. Look for new entries across the watchlist (subject to risk limits).
  3. Persist state and print a summary.
"""
from __future__ import annotations

from typing import Dict, Optional

import config
import market_data
import risk
from analyst import get_analyst
from broker import get_broker
from portfolio import Portfolio, Position


class TradingAgent:
    def __init__(self):
        self.portfolio = Portfolio.load(config.STATE_FILE, config.STARTING_CAPITAL)
        self.broker = get_broker()
        self.analyst = get_analyst()

    # --- helpers -----------------------------------------------------------
    def _snapshots(self) -> Dict[str, dict]:
        tickers = set(config.WATCHLIST) | set(self.portfolio.positions)
        out = {}
        for t in tickers:
            snap = market_data.snapshot(t)
            if snap:
                out[t] = snap
        return out

    def _prices(self, snapshots: Dict[str, dict]) -> Dict[str, float]:
        return {t: s["price"] for t, s in snapshots.items()}

    def _execute(self, ticker: str, side: str, qty: int, price: float,
                 stop: float = 0.0, target: float = 0.0) -> None:
        fill = self.broker.execute(ticker, side, qty, price)
        if side == "BUY":
            self.portfolio.open_position(
                ticker, qty, fill.price, cost=-fill.cash_delta,
                stop_loss=stop, target=target,
            )
            print(f"  -> BOUGHT {qty} {ticker} @ {fill.price} "
                  f"(stop {stop}, target {target})")
        else:
            pnl = self.portfolio.close_position(ticker, fill.price,
                                                proceeds=fill.cash_delta)
            print(f"  -> SOLD {qty} {ticker} @ {fill.price}  P&L ₹{pnl:,.0f}")

    # --- position management ----------------------------------------------
    def _manage_positions(self, snapshots: Dict[str, dict]) -> None:
        for ticker, pos in list(self.portfolio.positions.items()):
            snap = snapshots.get(ticker)
            if not snap:
                continue
            price = snap["price"]

            # 1) Hard, non-negotiable exits first.
            hard_stop = pos.avg_price * (1 - config.HARD_STOP_LOSS_PCT)
            hard_tp = pos.avg_price * (1 + config.HARD_TAKE_PROFIT_PCT)
            if price <= max(pos.stop_loss, hard_stop):
                print(f"[{ticker}] stop-loss hit @ {price}")
                self._execute(ticker, "SELL", pos.qty, price)
                continue
            if pos.target and price >= pos.target or price >= hard_tp:
                print(f"[{ticker}] target/take-profit hit @ {price}")
                self._execute(ticker, "SELL", pos.qty, price)
                continue

            # 2) Otherwise let the analyst decide HOLD vs EXIT.
            decision = self.analyst.review(
                snap, position=_pos_view(pos),
                equity=self.portfolio.equity(self._prices(snapshots)),
            )
            if decision["action"] == "EXIT":
                print(f"[{ticker}] analyst EXIT: {decision['rationale']}")
                self._execute(ticker, "SELL", pos.qty, price)
            else:
                print(f"[{ticker}] hold (conf {decision['confidence']:.2f})")

    # --- new entries -------------------------------------------------------
    def _look_for_entries(self, snapshots: Dict[str, dict]) -> None:
        prices = self._prices(snapshots)
        for ticker in config.WATCHLIST:
            if ticker in self.portfolio.positions:
                continue
            ok, reason = risk.can_open_new(self.portfolio, prices)
            if not ok:
                print(f"(no new entries: {reason})")
                return

            snap = snapshots.get(ticker)
            if not snap:
                continue

            equity = self.portfolio.equity(prices)
            decision = self.analyst.review(snap, position=None, equity=equity)
            action = decision["action"]
            conf = decision["confidence"]

            if action != "BUY":
                print(f"[{ticker}] {action} (conf {conf:.2f})")
                continue
            if conf < config.MIN_CONFIDENCE_TO_TRADE:
                print(f"[{ticker}] BUY but low confidence {conf:.2f} — skipped")
                continue

            entry = decision.get("entry") or snap["price"]
            stop = decision.get("stop_loss")
            target = decision.get("target")
            if not stop or not target or stop >= entry:
                print(f"[{ticker}] BUY rejected — invalid stop/target")
                continue

            qty = risk.position_size(equity, entry, stop)
            if qty < 1:
                print(f"[{ticker}] BUY but position size < 1 share — skipped")
                continue
            cost = qty * snap["price"]
            if cost > self.portfolio.cash:
                print(f"[{ticker}] BUY but not enough cash — skipped")
                continue

            print(f"[{ticker}] BUY conf {conf:.2f}: {decision['rationale']}")
            self._execute(ticker, "BUY", qty, snap["price"],
                          stop=round(stop, 2), target=round(target, 2))

    # --- public ------------------------------------------------------------
    def run_once(self) -> None:
        snapshots = self._snapshots()
        if not snapshots:
            print("No market data available (market closed or offline?).")
            return

        print("\n=== Managing open positions ===")
        if self.portfolio.positions:
            self._manage_positions(snapshots)
        else:
            print("(none)")

        print("\n=== Scanning for new entries ===")
        self._look_for_entries(snapshots)

        self.portfolio.save(config.STATE_FILE)
        self._summary(snapshots)

    def _summary(self, snapshots: Dict[str, dict]) -> None:
        prices = self._prices(snapshots)
        equity = self.portfolio.equity(prices)
        ret = (equity / self.portfolio.starting_capital - 1) * 100
        print("\n=== Portfolio ===")
        print(f"Cash:        ₹{self.portfolio.cash:,.0f}")
        print(f"Equity:      ₹{equity:,.0f}  ({ret:+.2f}% vs start)")
        print(f"Realized P&L:₹{self.portfolio.realized_pnl:,.0f} "
              f"(today ₹{self.portfolio.realized_today:,.0f})")
        if self.portfolio.positions:
            print("Open positions:")
            for t, p in self.portfolio.positions.items():
                px = prices.get(t, p.avg_price)
                print(f"  {t}: {p.qty} @ {p.avg_price}  now {px}  "
                      f"uPnL ₹{p.unrealized(px):,.0f}")

        print()
        print(self.analyst.cost_summary())


def _pos_view(pos: Position) -> dict:
    return {
        "qty": pos.qty,
        "avg_price": pos.avg_price,
        "stop_loss": pos.stop_loss,
        "target": pos.target,
    }
