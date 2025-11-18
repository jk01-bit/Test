"""
Strategy Configuration Settings
"""
from datetime import time

# ============================================================================
# CAPITAL & RISK MANAGEMENT
# ============================================================================
TOTAL_CAPITAL = 500000  # Total trading capital
MARGIN_UTILIZATION = 0.40  # Use 40% of capital
MAX_DAILY_LOSS = 7500  # Maximum daily loss allowed
MAX_POSITIONS = 1  # Only 1 active spread at a time

# ============================================================================
# POSITION SIZING
# ============================================================================
POSITION_SIZE = {
    "BANKNIFTY": 2,  # 2 lots for BankNifty
    "NIFTY": 4,      # 4-5 lots for Nifty (configurable)
}

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================
FAST_EMA = 20
SLOW_EMA = 50
TIMEFRAME = "15minute"  # 15-minute candles
EMA_FLAT_THRESHOLD = 0.001  # If EMA difference < 0.1%, consider flat

# ============================================================================
# STRIKE SELECTION
# ============================================================================
ATM_OFFSET_MIN = 150  # Minimum offset from ATM
ATM_OFFSET_MAX = 200  # Maximum offset from ATM
SPREAD_WIDTH = 200    # Width between sell and buy strikes

# For Bull Put Spread (Uptrend):
# - Sell: ATM + 150 or ATM + 200 PE
# - Buy: (Sell Strike - 200) PE

# For Bear Call Spread (Downtrend):
# - Sell: ATM + 150 or ATM + 200 CE
# - Buy: (Sell Strike + 200) CE

# ============================================================================
# ENTRY RULES
# ============================================================================
ENTRY_START_TIME = time(9, 35)   # 9:35 AM
ENTRY_END_TIME = time(10, 30)    # 10:30 AM
ENTRY_ALLOWED_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday

# ============================================================================
# EXIT RULES
# ============================================================================
PROFIT_TARGET_MIN = 0.40  # 40% premium decay
PROFIT_TARGET_MAX = 0.50  # 50% premium decay
EXIT_TIME = time(15, 10)  # Exit all positions by 3:10 PM
STOP_LOSS_MULTIPLIER = 1.5  # SL = 1.5x premium of sold leg

# ============================================================================
# FILTERS & RISK CONTROLS
# ============================================================================
MAX_VIX = 17  # Don't trade if India VIX > 17
MAX_GAP_PERCENT = 1.5  # Avoid trading on gaps > 1.5%
EXPIRY_CUTOFF_TIME = time(14, 0)  # Don't trade expiry after 2 PM

# ============================================================================
# INSTRUMENTS
# ============================================================================
TRADING_INSTRUMENTS = ["NIFTY", "BANKNIFTY"]

# ============================================================================
# MONITORING & ALERTS
# ============================================================================
POSITION_CHECK_INTERVAL = 60  # Check positions every 60 seconds
ENABLE_TELEGRAM = True
ENABLE_EMAIL = False

# ============================================================================
# EXPECTED PERFORMANCE (For Tracking)
# ============================================================================
EXPECTED_MONTHLY_RETURN = 0.04  # 3-5% per month (using 4% avg)
EXPECTED_WIN_RATE = 0.70  # 65-75% win rate (using 70% avg)
EXPECTED_MONTHLY_PROFIT_MIN = 15000
EXPECTED_MONTHLY_PROFIT_MAX = 25000

# ============================================================================
# BACKTESTING PARAMETERS
# ============================================================================
BACKTEST_START_DATE = "2023-01-01"
BACKTEST_CAPITAL = 500000
BACKTEST_SLIPPAGE = 0.5  # ₹0.5 per lot slippage
BACKTEST_COMMISSION = 20  # ₹20 per order

# ============================================================================
# BROKER SETTINGS
# ============================================================================
BROKER = "ZERODHA"  # Currently using Zerodha, can extend to others

# Order types
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_MARKET = "MARKET"
PRODUCT_TYPE = "NRML"  # NRML for positional, MIS for intraday
EXCHANGE = "NFO"  # NSE Futures & Options

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "logs/trading_bot.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# ============================================================================
# DATABASE
# ============================================================================
DB_PATH = "data/trading.db"

# ============================================================================
# SAFETY CHECKS
# ============================================================================
REQUIRE_MANUAL_APPROVAL = False  # Set to True for manual approval before each trade
DRY_RUN_MODE = False  # Set to True to test without placing real orders
