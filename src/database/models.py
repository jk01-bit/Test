"""
Database Models for Trade Tracking
"""
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    """Trade model to store all trade information"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Trade Identification
    trade_id = Column(String(50), unique=True, nullable=False)
    instrument = Column(String(20), nullable=False)  # NIFTY or BANKNIFTY
    spread_type = Column(String(20), nullable=False)  # BULL_PUT_SPREAD or BEAR_CALL_SPREAD

    # Entry Details
    entry_time = Column(DateTime, nullable=False)
    expiry = Column(DateTime, nullable=False)  # Option expiry date
    entry_spot_price = Column(Float, nullable=False)
    trend = Column(String(20), nullable=False)  # UPTREND or DOWNTREND

    # Strike Details
    sell_strike = Column(Float, nullable=False)
    buy_strike = Column(Float, nullable=False)
    option_type = Column(String(5), nullable=False)  # CE or PE

    # Premium Details
    sell_premium = Column(Float, nullable=False)
    buy_premium = Column(Float, nullable=False)
    net_premium = Column(Float, nullable=False)  # Credit received

    # Position Details
    lot_size = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    margin_used = Column(Float)

    # Order IDs
    sell_order_id = Column(String(50))
    buy_order_id = Column(String(50))

    # Exit Details
    exit_time = Column(DateTime)
    exit_sell_premium = Column(Float)
    exit_buy_premium = Column(Float)
    exit_net_premium = Column(Float)
    exit_reason = Column(String(50))  # PROFIT_TARGET, STOP_LOSS, TIME_EXIT, etc.

    # P&L
    gross_pnl = Column(Float)
    net_pnl = Column(Float)  # After commissions
    commission = Column(Float, default=0.0)
    pnl_percent = Column(Float)

    # Risk Management
    stop_loss_value = Column(Float)  # 1.5x premium of sold leg
    target_value = Column(Float)

    # Status
    status = Column(String(20), nullable=False)  # OPEN, CLOSED, FAILED
    is_winning_trade = Column(Boolean)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Trade {self.trade_id}: {self.instrument} {self.spread_type} @ {self.entry_time}>"


class DailyPerformance(Base):
    """Daily performance tracking"""

    __tablename__ = "daily_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, unique=True, nullable=False)

    # Trade Stats
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # P&L
    gross_pnl = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    commissions = Column(Float, default=0.0)

    # Capital
    starting_capital = Column(Float)
    ending_capital = Column(Float)
    return_percent = Column(Float)

    # Risk
    max_drawdown = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<DailyPerformance {self.date.date()}: PnL={self.net_pnl}>"


class MarketData(Base):
    """Store market data for backtesting and analysis"""

    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # OHLC
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)

    # Indicators
    ema_20 = Column(Float)
    ema_50 = Column(Float)

    # Market Info
    india_vix = Column(Float)
    gap_percent = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<MarketData {self.instrument} @ {self.timestamp}>"


class Signal(Base):
    """Store generated signals for tracking"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Signal Details
    instrument = Column(String(20), nullable=False)
    trend = Column(String(20), nullable=False)
    signal_type = Column(String(20), nullable=False)  # ENTRY, EXIT

    # Market Conditions
    spot_price = Column(Float, nullable=False)
    ema_20 = Column(Float)
    ema_50 = Column(Float)
    india_vix = Column(Float)
    gap_percent = Column(Float)

    # Signal Status
    is_valid = Column(Boolean, default=True)
    filter_passed = Column(Boolean, default=True)
    filter_reason = Column(String(100))  # Why signal was filtered out

    # Action Taken
    was_executed = Column(Boolean, default=False)
    trade_id = Column(String(50))  # Link to trade if executed

    # Metadata
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Signal {self.signal_id}: {self.instrument} {self.trend} @ {self.timestamp}>"


class SystemLog(Base):
    """System logs for debugging and monitoring"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    log_level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    module = Column(String(50))
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON or additional details

    def __repr__(self):
        return f"<SystemLog {self.log_level}: {self.message[:50]}>"
