"""Risk management — the guardrails between the analyst and your capital.

The analyst proposes; risk.py disposes. Every new position is sized so that
hitting its stop-loss costs at most MAX_RISK_PER_TRADE_PCT of equity, and the
daily circuit breaker halts trading after a bad day.
"""
from __future__ import annotations

import math
from typing import Dict

import config
from portfolio import Portfolio


def position_size(equity: float, entry: float, stop: float) -> int:
    """Quantity such that (entry-stop)*qty <= risk budget, and notional is
    capped at MAX_POSITION_WEIGHT of equity. Returns whole shares (>=0)."""
    if entry <= 0 or stop <= 0 or stop >= entry:
        return 0
    risk_budget = equity * config.MAX_RISK_PER_TRADE_PCT
    per_share_risk = entry - stop
    qty_by_risk = risk_budget / per_share_risk

    notional_cap = equity * config.MAX_POSITION_WEIGHT
    qty_by_weight = notional_cap / entry

    return max(0, int(math.floor(min(qty_by_risk, qty_by_weight))))


def daily_loss_breached(portfolio: Portfolio) -> bool:
    """True if today's realized loss has hit the daily circuit breaker."""
    limit = -abs(config.STARTING_CAPITAL * config.MAX_DAILY_LOSS_PCT)
    return portfolio.realized_today <= limit


def monthly_target_reached(portfolio: Portfolio, prices: Dict[str, float]) -> bool:
    """True once equity is up by the aspirational monthly target. When reached,
    the agent stops opening NEW risk (it still manages exits)."""
    target_equity = portfolio.starting_capital * (1 + config.MONTHLY_TARGET_PCT)
    return portfolio.equity(prices) >= target_equity


def can_open_new(portfolio: Portfolio, prices: Dict[str, float]) -> tuple[bool, str]:
    if len(portfolio.positions) >= config.MAX_OPEN_POSITIONS:
        return False, "max open positions reached"
    if daily_loss_breached(portfolio):
        return False, "daily loss limit hit — trading halted for the day"
    if monthly_target_reached(portfolio, prices):
        return False, "monthly target reached — no new risk this month"
    return True, "ok"
