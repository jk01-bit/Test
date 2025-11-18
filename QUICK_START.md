# 🚀 Quick Start Guide

Get your options trading bot running in 5 minutes!

---

## Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] Zerodha trading account
- [ ] Zerodha API subscription (₹2000/month)
- [ ] API Key and Secret
- [ ] ₹5,00,000 capital (recommended)

---

## 3-Step Setup

### **Step 1: Install** (2 minutes)

```bash
# Clone repository
git clone <repo-url>
cd options-trading-bot

# Run setup
python setup.py
```

### **Step 2: Configure** (2 minutes)

Edit `.env` file:

```bash
nano .env
```

Add your credentials:
```env
ZERODHA_API_KEY=your_actual_key
ZERODHA_API_SECRET=your_actual_secret
ZERODHA_USER_ID=your_user_id
TRADING_MODE=paper  # Start with paper trading
```

### **Step 3: Run** (1 minute)

```bash
python main.py
```

---

## First Time Login

1. Bot will show a login URL
2. Open URL in browser
3. Login to Zerodha
4. Copy the `request_token` from redirect URL
5. Paste it in the bot terminal

Example redirect URL:
```
http://127.0.0.1/?request_token=ABC123&action=login&status=success
```
Copy: `ABC123`

---

## Understanding the Output

```
✓ Database initialized
✓ Broker initialized
✓ Market data handler initialized
...
🚀 TRADING BOT STARTED
```

The bot will:
1. Check market status
2. Wait for entry window (9:35-10:30 AM)
3. Generate signals if conditions are met
4. Monitor positions
5. Execute exits based on rules

---

## Quick Commands

```bash
# View live logs
tail -f logs/trading_bot.log

# View trades only
tail -f logs/trades.log

# Check database
sqlite3 data/trading.db "SELECT COUNT(*) FROM trades;"

# Stop bot
Ctrl + C
```

---

## Safety First! ⚠️

### **Before Going Live:**

1. ✅ **Paper Trade First**
   - Set `TRADING_MODE=paper` in `.env`
   - Run for 2-4 weeks
   - Verify strategy performance

2. ✅ **Start Small**
   - Begin with 1 lot (not 2-4)
   - Reduce capital exposure
   - Monitor closely

3. ✅ **Daily Monitoring**
   - Check logs every day
   - Verify trades are correct
   - Watch for errors

4. ✅ **Set Alerts**
   - Configure Telegram notifications
   - Get instant trade alerts
   - Monitor remotely

---

## Common First-Time Issues

### **1. "Failed to connect to broker"**
- ✅ Check API credentials in `.env`
- ✅ Ensure API subscription is active
- ✅ Request token expires in 5 minutes - be quick!

### **2. "No signals generated"**
- ✅ Market must be open (9:15 AM - 3:30 PM IST)
- ✅ Time must be in entry window (9:35-10:30 AM)
- ✅ Check if VIX < 17
- ✅ Check if gap < 1.5%

### **3. "Module not found"**
```bash
pip install -r requirements.txt
```

### **4. "Permission denied"**
```bash
chmod +x main.py
chmod -R 755 logs data
```

---

## What Happens Next?

### **During Market Hours (9:15 AM - 3:30 PM):**

1. **9:00-9:35 AM**: Bot starts, waits for entry window
2. **9:35-10:30 AM**: Checks for entry signals every minute
3. **10:30 AM-3:10 PM**: Monitors open positions
4. **3:10 PM**: Exits all positions (time exit)
5. **3:15 PM**: Generates daily report
6. **3:20 PM**: Shuts down

### **Outside Market Hours:**

Bot waits and checks every 5 minutes.

---

## Your First Trade

When the bot finds a valid signal, you'll see:

```
═══════════════════════════════════════════
VALID SIGNAL GENERATED
═══════════════════════════════════════════
Instrument: NIFTY
Trend: UPTREND
Strategy: Bull Put Spread
Sell Strike: 23,150 PE @ ₹32
Buy Strike: 22,950 PE @ ₹18
Net Credit: ₹14
Stop Loss: ₹48
Target: ₹7-8
═══════════════════════════════════════════
```

If all checks pass, the trade will be executed automatically!

You'll get a Telegram notification (if configured):

```
🎯 TRADE ENTERED

ID: NIFTY_20241118_093542
Type: BULL_PUT_SPREAD
Premium: ₹14.00
Quantity: 100
Stop Loss: ₹48.00
```

---

## Monitoring Your Trades

### **Live Status:**
```bash
# View current positions
python -c "from src.database.db_manager import DatabaseManager; db = DatabaseManager(); print(len(db.get_open_trades()), 'open positions')"
```

### **Today's P&L:**
```bash
# Check today's performance
python -c "from src.database.db_manager import DatabaseManager; from datetime import date; db = DatabaseManager(); print('Today PnL:', db.calculate_daily_pnl(date.today()))"
```

---

## When to Stop

The bot will automatically stop if:
- Daily loss limit (₹7,500) is reached
- Circuit breaker is triggered
- Market closes
- You press Ctrl+C

All positions will be force-exited on shutdown.

---

## Next Steps

### **After First Day:**
1. Review logs
2. Check all trades in database
3. Verify P&L calculations
4. Adjust parameters if needed

### **After First Week:**
1. Analyze win rate
2. Check average profit/loss
3. Review exit reasons
4. Fine-tune stop loss/targets

### **After First Month:**
1. Calculate actual vs expected returns
2. Decide to continue or adjust
3. Scale up if consistent results
4. Consider live trading (if in paper mode)

---

## Getting Help

1. **Check Logs:**
   ```bash
   tail -n 100 logs/trading_bot.log
   ```

2. **Enable Debug Mode:**
   In `.env`:
   ```env
   LOG_LEVEL=DEBUG
   ```

3. **Test Individual Components:**
   ```bash
   python -c "from src.data.market_data import MarketDataHandler; print('Test OK')"
   ```

---

## Backup & Safety

### **Daily Backup:**
```bash
cp data/trading.db data/backup_$(date +%Y%m%d).db
```

### **Emergency Stop:**
```bash
pkill -f "python main.py"
```

### **View Trade History:**
```bash
sqlite3 data/trading.db
> SELECT * FROM trades ORDER BY entry_time DESC LIMIT 5;
> .exit
```

---

## Ready to Go Live?

### **Checklist Before Live Trading:**

- [ ] Paper traded for minimum 2-4 weeks
- [ ] Win rate is 65%+
- [ ] Average profit meets expectations
- [ ] Understand all entry/exit logic
- [ ] Know how to monitor and intervene
- [ ] Have backup internet connection
- [ ] Set proper position sizes
- [ ] Configure all notifications
- [ ] Have tested emergency stops

### **Switch to Live:**

In `.env`:
```env
TRADING_MODE=live  # Change from paper to live
```

**⚠️ WARNING:** Live mode places real trades with real money!

---

## Summary

```bash
# Setup
python setup.py
nano .env  # Add credentials

# Run
python main.py

# Monitor
tail -f logs/trading_bot.log

# Stop
Ctrl + C
```

**That's it! You're ready to automate your options trading.** 🎉

---

**Remember:** Start small, monitor closely, and scale gradually. The best trade is sometimes no trade!

Good luck! 🚀
