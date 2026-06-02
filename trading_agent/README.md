# 📈 Claude Stock Market Analyst Agent

A self-contained trading agent for NSE equities. **Claude acts as the analyst** —
it reviews each stock and decides BUY / HOLD / EXIT — while the agent handles
risk sizing, order execution, profit booking, and bookkeeping around it.

It starts from **₹1,00,000 (1 lakh)** of capital and runs in **paper mode** by
default (simulated fills, no real money, no broker account needed).

---

## ⚠️ Read this first — about the "10% per month" goal

You asked for **10% per month**. Be clear-eyed about what that means:

- 10%/month compounds to **~214% per year**. That is far beyond what
  professional funds sustain. **No honest system can promise it.**
- The only way to *aim* that high is to take large risk per trade, which
  sharply raises the odds of a drawdown that eats a big chunk of your ₹1 lakh.
- This agent is built the opposite way: **capital preservation first.** It
  targets a realistic **~2–4%/month**, caps risk per trade, and has a daily
  loss circuit breaker. It treats your 10% as a *ceiling* — once equity is up
  10%, it stops opening new risk for the month rather than pushing its luck.

Trading involves real risk of loss. Paper-trade for several weeks and read
every trade the agent makes before you even consider real money.

---

## How it works

```
 market_data ──► analyst (Claude) ──► risk sizing ──► broker ──► portfolio
   indicators      BUY/HOLD/EXIT      stop-based qty    fills      P&L + state
```

1. **`market_data.py`** — pulls price history (yfinance) and computes SMA20/50
   and RSI14 for each watchlist stock.
2. **`analyst.py`** — Claude reviews the snapshot + your current position and
   returns a structured decision (action, confidence, entry, stop, target,
   rationale). Uses prompt caching + adaptive thinking + JSON-schema output.
3. **`risk.py`** — sizes every position so hitting its stop costs ≤ 2% of
   equity, caps position weight, and enforces the daily loss breaker.
4. **`broker.py`** — `PaperBroker` simulates fills with slippage + commission.
   `LiveBroker` is a documented stub you implement to go real.
5. **`portfolio.py`** — tracks cash, positions, realized P&L; persists to
   `state.json` so it survives restarts.
6. **`runner.py` / `main.py`** — the loop: manage exits, scan for entries,
   book profits, print a summary.

---

## Setup

```bash
cd trading_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
```

## Run

```bash
python main.py            # one analyse + trade pass (paper mode)
python main.py --loop 15  # repeat every 15 minutes during market hours
python main.py --reset    # wipe saved state and start fresh
```

---

## Configuration (`config.py` / `.env`)

| Setting | Default | Meaning |
|---|---|---|
| `CAPITAL` | 100000 | Starting capital (₹) |
| `MONTHLY_TARGET_PCT` | 0.10 | Aspirational ceiling; stops new risk once hit |
| `MAX_RISK_PER_TRADE_PCT` | 0.02 | Max equity risked per trade (drives sizing) |
| `MAX_DAILY_LOSS_PCT` | 0.03 | Daily loss circuit breaker |
| `HARD_STOP_LOSS_PCT` | 0.05 | Force-exit a losing position |
| `HARD_TAKE_PROFIT_PCT` | 0.10 | Force-book a winning position |
| `MIN_CONFIDENCE_TO_TRADE` | 0.60 | Min analyst confidence to open a trade |
| `WATCHLIST` | 5 large caps | Stocks to analyse |

---

## Going live (only after thorough paper testing)

`LiveBroker` in `broker.py` is intentionally a stub. To route real orders:

1. `pip install kiteconnect`, add Zerodha API key/secret/access token to `.env`.
2. Implement `LiveBroker.execute()` using `kite.place_order(...)`.
3. Map tickers (`RELIANCE.NS` → tradingsymbol `RELIANCE`, exchange `NSE`).
4. Start with **1 share** and watch every fill before scaling.

The agent never routes a live order while `TRADING_MODE=paper`.

---

## Disclaimer

This software is for educational purposes. It is not financial advice. Past or
simulated performance does not predict future results. You are responsible for
any trades you place with it.
