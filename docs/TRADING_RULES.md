# Trading Rules Document

## Strategy Overview

**Strategy Type**: Credit Spread Strategy (Bull Put Spread / Bear Call Spread)
**Instruments**: NIFTY, BANKNIFTY
**Timeframe**: 15-minute candles
**Trend Indicator**: EMA 20 & EMA 50 crossover

---

## Order Execution Sequence

### Entry Order Sequence
| Step | Action | Description |
|------|--------|-------------|
| 1 | **BUY** option of X strike | Place hedge order first (protection) |
| 2 | Wait for BUY execution | Max wait: 30 seconds |
| 3 | **SELL** option of Y strike | Place risk order after hedge is confirmed |

**Rationale**: BUY order first ensures hedge protection is in place before taking on risk with the SELL order.

### Exit Order Sequence
| Step | Action | Description |
|------|--------|-------------|
| 1 | **Square off SELL** (BUY back Y strike) | Cover short position first (reduce risk) |
| 2 | Wait for BUY-back execution | Max wait: 30 seconds |
| 3 | **Square off BUY** (SELL X strike) | Close long position after short is covered |

**Rationale**: Covering the short position first reduces risk exposure before closing the hedge.

---

## Instrument Specifications

| Parameter | NIFTY | BANKNIFTY |
|-----------|-------|-----------|
| Lot Size | 75 | 35 |
| Strike Interval | 50 | 100 |
| Expiry Day | Thursday | Wednesday |
| Position Size | 4 lots | 2 lots |

---

## Entry Rules

### Time Window
- **Entry Start**: 9:35 AM IST
- **Entry End**: 10:30 AM IST
- **Trading Days**: Monday to Friday

### Trend Identification
| Trend | Condition | Spread Type | Option Type |
|-------|-----------|-------------|-------------|
| UPTREND | EMA 20 > EMA 50 | Bull Put Spread | SELL PE, BUY PE |
| DOWNTREND | EMA 20 < EMA 50 | Bear Call Spread | SELL CE, BUY CE |
| SIDEWAYS | EMA difference < 0.1% | No Trade | - |

### Strike Selection
- **Sell Strike**: ATM + 150 points (minimum offset)
- **Buy Strike**: Sell Strike ± 200 points (spread width)

**Bull Put Spread (Uptrend)**:
- Sell: ATM + 150 PE
- Buy: Sell Strike - 200 PE

**Bear Call Spread (Downtrend)**:
- Sell: ATM + 150 CE
- Buy: Sell Strike + 200 CE

---

## Exit Rules

### Exit Triggers
| Trigger | Condition | Priority |
|---------|-----------|----------|
| Profit Target | Rs.600 per lot | 1 |
| Stop Loss | 1.5x premium of sold leg | 2 |
| Time Exit | 3:10 PM IST | 3 |
| Daily Loss Limit | Rs.7,500 reached | 4 |
| Expiry | Options expired worthless | 5 |

### Exit Time
- **Mandatory Exit**: 3:10 PM IST (all open positions must be closed)

---

## Risk Management

### Capital Allocation
| Parameter | Value |
|-----------|-------|
| Total Capital | Rs.5,00,000 |
| Margin Utilization | 40% (Rs.2,00,000) |
| Max Daily Loss | Rs.7,500 |
| Max Open Positions | 1 spread at a time |

### Filters (Trade Rejection)
| Filter | Condition | Action |
|--------|-----------|--------|
| VIX Filter | India VIX > 17 | Skip trade |
| Gap Filter | Opening gap > 1.5% | Skip trade |
| Expiry Cutoff | After 2:00 PM on expiry day | Skip trade |
| No Trend | EMA flat (< 0.1% difference) | Skip trade |
| Capital Check | Insufficient margin | Skip trade |

---

## Order Configuration

| Setting | Value |
|---------|-------|
| Order Type | LIMIT |
| Product Type | NRML (positional) |
| Exchange | NFO |
| Order Validity | DAY |

### Order Timeout
- **Max Wait Time**: 30 seconds per order
- **Action on Timeout**: Cancel pending order and abort spread

---

## Expected Performance

| Metric | Target |
|--------|--------|
| Monthly Return | 3-5% |
| Win Rate | 65-75% |
| Monthly Profit | Rs.15,000 - Rs.25,000 |

---

## Monitoring

| Parameter | Value |
|-----------|-------|
| Position Check Interval | 60 seconds |
| Telegram Alerts | Enabled |
| Email Alerts | Disabled |

---

## Safety Controls

| Control | Setting |
|---------|---------|
| Manual Approval | Disabled |
| Dry Run Mode | Disabled |

---

## Order Logging Format

Each order is logged with the following details:
```
ORDER PLACED [YYYY-MM-DD HH:MM:SS] | Symbol: XXX | Type: BUY/SELL | Qty: XX | Price: Rs.XX | Product: NRML | Order ID: XXXXX
```

Spread entry logs include:
```
============================================================
SPREAD ORDER ENTRY - YYYY-MM-DD HH:MM:SS
============================================================
SELL Leg: NIFTY24DECXXPE @ Rs.XX x XXX
BUY Leg:  NIFTY24DECXXPE @ Rs.XX x XXX
Net Credit: Rs.XX.XX
============================================================
[STEP 1] Placing BUY order first: NIFTY24DECXXPE @ Rs.XX
[OK] BUY order placed - Order ID: XXXXX
[STEP 2] Waiting for BUY order XXXXX to execute...
[OK] BUY order XXXXX executed @ Rs.XX
[STEP 3] Placing SELL order: NIFTY24DECXXPE @ Rs.XX
[OK] SELL order placed - Order ID: XXXXX
============================================================
SPREAD ORDER SUMMARY
============================================================
BUY Order ID:  XXXXX - NIFTY24DECXXPE
SELL Order ID: XXXXX - NIFTY24DECXXPE
Quantity: XXX
============================================================
```

---

## Document Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-03 | Initial trading rules document |

---

*Last Updated: 2025-12-03*
