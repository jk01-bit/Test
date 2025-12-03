"""
Market Constants and Reference Data
"""

# ============================================================================
# LOT SIZES (Update these periodically as they change)
# ============================================================================
LOT_SIZES = {
    "NIFTY": 75,        # Current Nifty lot size
    "BANKNIFTY": 35,    # Current BankNifty lot size
    "FINNIFTY": 25,     # FinNifty lot size (for future use)
    "MIDCPNIFTY": 50,   # MidCap Nifty lot size (for future use)
}

# ============================================================================
# STRIKE INTERVALS
# ============================================================================
STRIKE_INTERVALS = {
    "NIFTY": 50,       # Nifty strikes are in multiples of 50
    "BANKNIFTY": 100,  # BankNifty strikes are in multiples of 100
    "FINNIFTY": 50,
    "MIDCPNIFTY": 25,
}

# ============================================================================
# MARKET TIMINGS (IST)
# ============================================================================
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
PRE_MARKET_OPEN = "09:00"
POST_MARKET_CLOSE = "15:40"

# ============================================================================
# OPTION TYPES
# ============================================================================
OPTION_TYPE_CE = "CE"  # Call Option
OPTION_TYPE_PE = "PE"  # Put Option

# ============================================================================
# EXPIRY DAYS
# ============================================================================
EXPIRY_DAY = {
    "NIFTY": 3,        # Thursday (0=Monday, 3=Thursday)
    "BANKNIFTY": 2,    # Wednesday
    "FINNIFTY": 1,     # Tuesday
}

# ============================================================================
# INDICES
# ============================================================================
INDEX_SYMBOLS = {
    "NIFTY": "NIFTY 50",
    "BANKNIFTY": "NIFTY BANK",
    "INDIA_VIX": "INDIA VIX",
}

# ============================================================================
# ORDER STATUS
# ============================================================================
ORDER_STATUS_COMPLETE = "COMPLETE"
ORDER_STATUS_PENDING = "PENDING"
ORDER_STATUS_REJECTED = "REJECTED"
ORDER_STATUS_CANCELLED = "CANCELLED"

# ============================================================================
# TRANSACTION TYPES
# ============================================================================
TRANSACTION_TYPE_BUY = "BUY"
TRANSACTION_TYPE_SELL = "SELL"

# ============================================================================
# SPREAD TYPES
# ============================================================================
SPREAD_TYPE_BULL_PUT = "BULL_PUT_SPREAD"  # Uptrend - Sell Put Spread
SPREAD_TYPE_BEAR_CALL = "BEAR_CALL_SPREAD"  # Downtrend - Sell Call Spread

# ============================================================================
# TREND TYPES
# ============================================================================
TREND_UPTREND = "UPTREND"
TREND_DOWNTREND = "DOWNTREND"
TREND_SIDEWAYS = "SIDEWAYS"
TREND_UNKNOWN = "UNKNOWN"

# ============================================================================
# TRADE STATES
# ============================================================================
TRADE_STATE_SIGNAL_GENERATED = "SIGNAL_GENERATED"
TRADE_STATE_ENTRY_PENDING = "ENTRY_PENDING"
TRADE_STATE_POSITION_OPEN = "POSITION_OPEN"
TRADE_STATE_EXIT_PENDING = "EXIT_PENDING"
TRADE_STATE_CLOSED = "CLOSED"
TRADE_STATE_FAILED = "FAILED"

# ============================================================================
# EXIT REASONS
# ============================================================================
EXIT_REASON_PROFIT_TARGET = "PROFIT_TARGET"
EXIT_REASON_STOP_LOSS = "STOP_LOSS"
EXIT_REASON_TIME_EXIT = "TIME_EXIT"
EXIT_REASON_DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
EXIT_REASON_MANUAL = "MANUAL"
EXIT_REASON_ERROR = "ERROR"
EXIT_REASON_EXPIRED = "EXPIRED"  # Options expired worthless

# ============================================================================
# NOTIFICATION TYPES
# ============================================================================
NOTIF_TRADE_ENTRY = "TRADE_ENTRY"
NOTIF_TRADE_EXIT = "TRADE_EXIT"
NOTIF_STOP_LOSS_HIT = "STOP_LOSS_HIT"
NOTIF_DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
NOTIF_ERROR = "ERROR"
NOTIF_DAILY_REPORT = "DAILY_REPORT"

# ============================================================================
# FILTER REASONS (Why trade was not taken)
# ============================================================================
FILTER_VIX_HIGH = "VIX_TOO_HIGH"
FILTER_GAP_LARGE = "GAP_TOO_LARGE"
FILTER_OUTSIDE_TIME = "OUTSIDE_ENTRY_WINDOW"
FILTER_EXPIRY_LATE = "EXPIRY_DAY_TOO_LATE"
FILTER_NO_TREND = "NO_CLEAR_TREND"
FILTER_POSITION_EXISTS = "POSITION_ALREADY_EXISTS"
FILTER_CAPITAL_INSUFFICIENT = "INSUFFICIENT_CAPITAL"
FILTER_DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT_REACHED"
