# 📦 Installation Guide

## System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.10 or higher
- **RAM**: Minimum 2GB
- **Storage**: 1GB free space
- **Internet**: Stable connection required

---

## Installation Steps

### **Option 1: Automated Setup**

```bash
# 1. Clone the repository
git clone <repository-url>
cd options-trading-bot

# 2. Run setup script
python setup.py

# 3. Edit .env file with your credentials
nano .env

# 4. Run the bot
python main.py
```

### **Option 2: Manual Setup**

#### **Step 1: Install Python Dependencies**

```bash
pip install -r requirements.txt
```

#### **Step 2: Create Directories**

```bash
mkdir -p logs data config src backtesting tests
```

#### **Step 3: Configure Environment**

```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

#### **Step 4: Initialize Database**

```bash
python -c "from src.database.db_manager import DatabaseManager; DatabaseManager()"
```

#### **Step 5: Test Installation**

```bash
python -c "from src.utils.logger import setup_logger; setup_logger()"
```

---

## Configuration

### **1. Zerodha API Setup**

1. Go to [Zerodha KiteConnect](https://kite.trade/)
2. Create an app (costs ₹2000/month)
3. Note down API Key and API Secret
4. Add to `.env` file

```env
ZERODHA_API_KEY=your_key_here
ZERODHA_API_SECRET=your_secret_here
ZERODHA_USER_ID=your_user_id
```

### **2. Telegram Setup (Optional)**

1. Create bot with [@BotFather](https://t.me/botfather)
2. Get bot token
3. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
4. Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### **3. Strategy Configuration**

Edit `config/settings.py` to customize:

```python
TOTAL_CAPITAL = 500000
MARGIN_UTILIZATION = 0.40
MAX_DAILY_LOSS = 7500
POSITION_SIZE = {
    "BANKNIFTY": 2,
    "NIFTY": 4,
}
```

---

## Verification

### **Test the Installation**

```bash
# Test imports
python -c "from src.brokers.zerodha_broker import ZerodhaBroker; print('✓ Broker OK')"
python -c "from src.data.indicators import IndicatorEngine; print('✓ Indicators OK')"
python -c "from src.database.db_manager import DatabaseManager; print('✓ Database OK')"

# Test notifications
python -c "from src.utils.notifications import NotificationManager; n = NotificationManager(); print('✓ Notifications OK')"
```

### **Run in Dry Mode**

Set in `.env`:
```env
TRADING_MODE=paper
```

Then run:
```bash
python main.py
```

---

## Troubleshooting

### **Import Errors**

```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### **Database Errors**

```bash
rm data/trading.db
python setup.py
```

### **Permission Errors**

```bash
chmod +x main.py
chmod -R 755 logs data
```

---

## Deployment

### **Option 1: Local Machine**

Run during market hours:
```bash
python main.py
```

### **Option 2: AWS EC2**

```bash
# 1. Launch t2.micro instance (₹500-800/month)
# 2. SSH into instance
# 3. Install Python 3.10+
# 4. Clone repo and setup
# 5. Run with nohup or screen

screen -S trading-bot
python main.py
# Ctrl+A, D to detach
```

### **Option 3: Systemd Service (Linux)**

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Options Trading Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/options-trading-bot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

---

## Updates

### **Update the Bot**

```bash
git pull origin main
pip install -r requirements.txt --upgrade
python main.py
```

---

## Uninstallation

```bash
# Stop the bot
pkill -f "python main.py"

# Backup data
cp -r data/ data_backup/

# Remove files
rm -rf options-trading-bot/
```

---

## Next Steps

After installation:

1. ✅ Verify all tests pass
2. ✅ Configure strategy parameters
3. ✅ Run in paper trading mode for 2-4 weeks
4. ✅ Monitor and analyze results
5. ✅ Gradually move to live trading with small size
6. ✅ Scale up after consistent results

---

**Need Help?** Check logs in `logs/` directory for detailed error messages.
