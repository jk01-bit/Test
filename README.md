# 📈 Options Trading Automation System

**Automated Options Selling + Trend Following Strategy**

A fully automated options trading system that implements Bull Put Spreads in uptrends and Bear Call Spreads in downtrends, with comprehensive risk management and monitoring.

---

## 🎯 Strategy Overview

### **Core Strategy**
- **Trend Identification**: Uses 20 EMA and 50 EMA on 15-minute charts
- **Uptrend**: Sell Put Spread (Bull Put Spread)
- **Downtrend**: Sell Call Spread (Bear Call Spread)
- **Capital**: ₹5,00,000 with 40% margin utilization

### **Key Features**
- ✅ Automated signal generation based on technical indicators
- ✅ Real-time position monitoring
- ✅ Automatic stop-loss and profit target management
- ✅ Daily loss limit protection
- ✅ Telegram and email notifications
- ✅ Comprehensive trade logging and reporting
- ✅ Zerodha integration (extensible to other brokers)

---

## 📋 Prerequisites

- **Python 3.10+**
- **Zerodha Trading Account** with API access
- **Capital**: Minimum ₹5,00,000 recommended
- **VPS/Server** (optional but recommended for 24/7 operation)

---

## 🚀 Quick Start

### **1. Clone the Repository**

```bash
git clone <repository-url>
cd options-trading-bot
```

### **2. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **3. Configure Environment**

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your details:

```env
# Zerodha API Credentials
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_USER_ID=your_user_id

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Mode
TRADING_MODE=paper  # Use 'paper' for testing, 'live' for real trading
```

### **4. Run the Bot**

```bash
python main.py
```

The bot will:
1. Ask you to login to Zerodha
2. Provide a login URL
3. Request the authentication token
4. Start monitoring markets and trading

---

## 📖 Detailed Setup

### **Getting Zerodha API Credentials**

1. Go to [https://kite.trade/](https://kite.trade/)
2. Sign up for KiteConnect API
3. Create an app and get your API Key and Secret
4. Note: API costs ₹2000/month

### **Setting Up Telegram Notifications** (Optional)

1. Create a bot using [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
4. Add credentials to `.env`

### **Directory Structure**

```
options-trading-bot/
├── config/                 # Configuration files
│   ├── settings.py        # Strategy parameters
│   ├── constants.py       # Market constants
│   └── credentials.py     # Credential management
├── src/
│   ├── brokers/           # Broker integrations
│   ├── data/              # Market data & indicators
│   ├── strategy/          # Signal generation & filters
│   ├── execution/         # Order & exit management
│   ├── risk/              # Risk management
│   ├── utils/             # Logging & notifications
│   └── database/          # Database models
├── logs/                  # Log files
├── data/                  # Database files
├── backtesting/          # Backtesting engine
├── main.py               # Main trading bot
└── requirements.txt      # Dependencies
```

---

## ⚙️ Configuration

### **Strategy Parameters** (`config/settings.py`)

Key parameters you can adjust:

```python
# Capital & Risk
TOTAL_CAPITAL = 500000
MARGIN_UTILIZATION = 0.40  # 40%
MAX_DAILY_LOSS = 7500

# Position Sizing
POSITION_SIZE = {
    "BANKNIFTY": 2,  # 2 lots
    "NIFTY": 4,      # 4 lots
}

# Entry/Exit
ENTRY_START_TIME = time(9, 35)
ENTRY_END_TIME = time(10, 30)
EXIT_TIME = time(15, 10)

# Filters
MAX_VIX = 17
MAX_GAP_PERCENT = 1.5
```

---

## 🎮 Usage

### **Normal Operation**

```bash
python main.py
```

### **Dry Run Mode** (No Real Trades)

Set in `.env`:
```env
TRADING_MODE=paper
```

Or in `config/settings.py`:
```python
DRY_RUN_MODE = True
```

### **View Logs**

```bash
tail -f logs/trading_bot.log
tail -f logs/trades.log
```

---

## 📊 Strategy Rules

### **Entry Conditions**

1. **Trend Identification**
   - Uptrend: 20 EMA > 50 EMA AND price > 20 EMA
   - Downtrend: 20 EMA < 50 EMA AND price < 20 EMA

2. **Entry Filters**
   - Time: 9:35 AM - 10:30 AM
   - India VIX < 17
   - Gap < 1.5%
   - No expiry trading after 2 PM
   - Max 1 position at a time

3. **Strike Selection**
   - **Uptrend (Bull Put Spread)**:
     - Sell: ATM - 150 (or -200) PE
     - Buy: Sell Strike - 200 PE

   - **Downtrend (Bear Call Spread)**:
     - Sell: ATM + 150 (or +200) CE
     - Buy: Sell Strike + 200 CE

### **Exit Conditions**

1. **Profit Target**: 40-50% premium decay
2. **Stop Loss**: 1.5× premium of sold leg
3. **Time Exit**: 3:10 PM (close all positions)
4. **Daily Loss Limit**: ₹7,500

### **Risk Management**

- Position Sizing: 40% of capital
- Max 1 active spread at a time
- Daily loss limit: ₹7,500
- Circuit breaker for extreme losses

---

## 📈 Expected Performance

- **Monthly Return**: 3-5%
- **Monthly Profit**: ₹15,000 - ₹25,000
- **Win Rate**: 65-75%
- **Risk-Reward**: ~1:1.5

*Past performance is not indicative of future results*

---

## 🔍 Monitoring

### **Database**

All trades are stored in SQLite database at `data/trading.db`

Query trades:
```python
from src.database.db_manager import DatabaseManager

db = DatabaseManager()
trades = db.get_recent_trades(limit=10)
```

### **Logs**

- `logs/trading_bot.log` - Detailed system logs
- `logs/trades.log` - Trade-specific logs

### **Notifications**

Real-time notifications for:
- Trade entries
- Trade exits
- Stop losses hit
- Daily loss limit reached
- Errors and warnings
- Daily performance reports

---

## 🛡️ Safety Features

1. **Daily Loss Limit**: Auto-stop trading at ₹7,500 loss
2. **Circuit Breaker**: Emergency stop for extreme conditions
3. **Position Limits**: Max 1 position to limit exposure
4. **VIX Filter**: Avoid trading in high volatility
5. **Gap Filter**: Skip days with large gaps
6. **Time Exit**: Force close all positions by 3:10 PM
7. **Dry Run Mode**: Test without real money

---

## 🧪 Backtesting

Run backtests to validate strategy:

```bash
python -m backtesting.backtest_engine
```

Customize backtest parameters in `backtesting/` folder.

---

## 🔧 Troubleshooting

### **Bot Not Connecting to Zerodha**

1. Check API credentials in `.env`
2. Ensure API subscription is active
3. Verify request token is fresh (valid for 5 minutes)

### **No Signals Generated**

1. Check if market is open
2. Verify time is within entry window (9:35-10:30 AM)
3. Check if filters are too restrictive (VIX, gap, etc.)
4. Review logs for filter failures

### **Orders Not Executing**

1. Check available margin in your account
2. Verify strike prices exist in option chain
3. Check broker API status
4. Review order logs for errors

### **Database Issues**

Delete and recreate:
```bash
rm data/trading.db
python main.py  # Will create new database
```

---

## 📝 Important Notes

### **Disclaimer**

⚠️ **Trading involves significant risk of loss. This system is provided for educational purposes only. Always:**
- Test thoroughly in paper trading mode
- Start with small position sizes
- Monitor the system regularly
- Understand the risks involved
- Consult a financial advisor

### **Best Practices**

1. **Start Small**: Begin with 1 lot regardless of capital
2. **Paper Trade First**: Run in simulation for 2-4 weeks
3. **Monitor Daily**: Check logs and positions regularly
4. **Backup Internet**: Have backup connectivity
5. **Review Weekly**: Analyze performance and adjust
6. **Keep Learning**: Markets evolve, so should your strategy

---

## 🤝 Support & Contribution

### **For Issues**

1. Check logs in `logs/` directory
2. Enable DEBUG logging in `.env`
3. Review error messages carefully
4. Check Zerodha API status

### **Extending to Other Brokers**

The system is designed to be broker-agnostic:

1. Create new broker class in `src/brokers/`
2. Implement same interface as `ZerodhaBroker`
3. Update `config/settings.py` to use new broker
4. Test thoroughly

Example brokers to add:
- Angel One (SmartAPI)
- Upstox
- Fyers
- AliceBlue

---

## 📚 Additional Resources

- [Zerodha KiteConnect Documentation](https://kite.trade/docs/connect/v3/)
- [Options Trading Basics](https://zerodha.com/varsity/module/option-strategies/)
- [Technical Analysis](https://zerodha.com/varsity/module/technical-analysis/)

---

## 📄 License

This project is provided as-is for educational purposes. Use at your own risk.

---

## ✨ Features Roadmap

- [ ] Multi-broker support (Angel One, Upstox)
- [ ] Web dashboard for monitoring
- [ ] Advanced backtesting with optimization
- [ ] Machine learning for entry timing
- [ ] Multiple strategy support
- [ ] Portfolio mode (multiple instruments simultaneously)
- [ ] Options Greeks tracking
- [ ] Market regime detection

---

## 🎯 Quick Command Reference

```bash
# Start bot
python main.py

# View live logs
tail -f logs/trading_bot.log

# Check trades
sqlite3 data/trading.db "SELECT * FROM trades ORDER BY entry_time DESC LIMIT 5;"

# Test notifications
python -c "from src.utils.notifications import NotificationManager; n = NotificationManager(); n.notify_system_start()"

# Backup database
cp data/trading.db data/trading_backup_$(date +%Y%m%d).db
```

---

**Happy Trading! 🚀**

*Remember: The best trade is sometimes no trade. Let the system work for you.*
