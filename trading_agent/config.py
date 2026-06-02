"""Central configuration for the trading agent.

Values are read from the environment (.env) with sensible, conservative
defaults. Everything that touches real money is intentionally cautious.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed yet — env vars still work, just no .env file.
    pass


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --- Account ---------------------------------------------------------------
TRADING_MODE = os.getenv("TRADING_MODE", "paper").lower()  # "paper" | "live"
STARTING_CAPITAL = _float("CAPITAL", 100_000.0)            # ₹1 lakh for month 1
MONTHLY_TARGET_PCT = _float("MONTHLY_TARGET_PCT", 0.10)    # aspirational ceiling

# --- Risk controls (the part that actually protects your money) ------------
# Risk no more than this fraction of equity on a single trade. Position size
# is derived from this and the distance to the stop-loss.
MAX_RISK_PER_TRADE_PCT = 0.02      # 2% of equity at risk per trade
# Stop trading for the day once cumulative loss hits this fraction of capital.
MAX_DAILY_LOSS_PCT = 0.03          # 3% daily circuit breaker
# Never deploy more than this fraction of equity into a single position.
MAX_POSITION_WEIGHT = 0.25         # 25% of equity max per name
MAX_OPEN_POSITIONS = 5

# Hard exits applied regardless of the analyst's opinion.
HARD_STOP_LOSS_PCT = 0.05          # -5% from entry -> force exit
HARD_TAKE_PROFIT_PCT = 0.10        # +10% from entry -> book profit

# Minimum analyst confidence (0-1) required to open a new position.
MIN_CONFIDENCE_TO_TRADE = 0.60

# --- Costs (paper broker simulation) ---------------------------------------
SLIPPAGE_PCT = 0.0005              # 0.05% slippage per fill
COMMISSION_PER_ORDER = 20.0        # flat ₹20/order (Zerodha-like)

# --- Universe --------------------------------------------------------------
# NSE tickers use the ".NS" suffix on Yahoo Finance.
WATCHLIST = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
]

# --- Claude (the analyst) --------------------------------------------------
# Pick the brain from .env: claude-opus-4-8 (default, sharpest),
# claude-sonnet-4-6 (~40% cheaper), or claude-haiku-4-5 (~80% cheaper).
MODEL = os.getenv("MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# USD price per 1M tokens, used to estimate per-run cost.
PRICING = {
    "claude-opus-4-8":   {"in": 5.0,  "out": 25.0},
    "claude-opus-4-7":   {"in": 5.0,  "out": 25.0},
    "claude-opus-4-6":   {"in": 5.0,  "out": 25.0},
    "claude-sonnet-4-6": {"in": 3.0,  "out": 15.0},
    "claude-haiku-4-5":  {"in": 1.0,  "out": 5.0},
}
USD_INR = _float("USD_INR", 83.0)  # rough FX, only for displaying ₹ estimate

# --- Persistence -----------------------------------------------------------
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
