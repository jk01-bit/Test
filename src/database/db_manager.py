"""
Database Manager
Handles all database operations
"""
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, date
from typing import List, Optional, Dict
import os

from src.database.models import Base, Trade, DailyPerformance, MarketData, Signal, SystemLog
from config.settings import DB_PATH


class DatabaseManager:
    """Manage database connections and operations"""

    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection"""
        if db_url is None:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            db_url = f"sqlite:///{DB_PATH}"

        self.engine = create_engine(db_url, echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # Create all tables
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    # ========================================================================
    # TRADE OPERATIONS
    # ========================================================================

    def create_trade(self, trade_data: Dict) -> Trade:
        """Create a new trade record"""
        session = self.get_session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            session.refresh(trade)
            return trade
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_trade(self, trade_id: str, update_data: Dict) -> Trade:
        """Update an existing trade"""
        session = self.get_session()
        try:
            trade = session.query(Trade).filter(Trade.trade_id == trade_id).first()
            if trade:
                for key, value in update_data.items():
                    setattr(trade, key, value)
                trade.updated_at = datetime.now()
                session.commit()
                session.refresh(trade)
            return trade
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a trade by ID"""
        session = self.get_session()
        try:
            return session.query(Trade).filter(Trade.trade_id == trade_id).first()
        finally:
            session.close()

    def get_open_trades(self) -> List[Trade]:
        """Get all open trades"""
        session = self.get_session()
        try:
            return session.query(Trade).filter(Trade.status == "OPEN").all()
        finally:
            session.close()

    def get_trades_by_date(self, trade_date: date) -> List[Trade]:
        """Get all trades for a specific date"""
        session = self.get_session()
        try:
            start = datetime.combine(trade_date, datetime.min.time())
            end = datetime.combine(trade_date, datetime.max.time())
            return (
                session.query(Trade)
                .filter(Trade.entry_time >= start, Trade.entry_time <= end)
                .all()
            )
        finally:
            session.close()

    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """Get most recent trades"""
        session = self.get_session()
        try:
            return (
                session.query(Trade)
                .order_by(desc(Trade.entry_time))
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    # ========================================================================
    # DAILY PERFORMANCE OPERATIONS
    # ========================================================================

    def create_or_update_daily_performance(
        self, performance_date: date, performance_data: Dict
    ) -> DailyPerformance:
        """Create or update daily performance record"""
        session = self.get_session()
        try:
            perf = (
                session.query(DailyPerformance)
                .filter(
                    func.date(DailyPerformance.date) == performance_date
                )
                .first()
            )

            if perf:
                for key, value in performance_data.items():
                    setattr(perf, key, value)
                perf.updated_at = datetime.now()
            else:
                performance_data["date"] = datetime.combine(
                    performance_date, datetime.min.time()
                )
                perf = DailyPerformance(**performance_data)
                session.add(perf)

            session.commit()
            session.refresh(perf)
            return perf
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_daily_performance(self, performance_date: date) -> Optional[DailyPerformance]:
        """Get daily performance for a specific date"""
        session = self.get_session()
        try:
            return (
                session.query(DailyPerformance)
                .filter(func.date(DailyPerformance.date) == performance_date)
                .first()
            )
        finally:
            session.close()

    def calculate_daily_pnl(self, trade_date: date) -> float:
        """Calculate total P&L for a specific date"""
        session = self.get_session()
        try:
            start = datetime.combine(trade_date, datetime.min.time())
            end = datetime.combine(trade_date, datetime.max.time())

            result = (
                session.query(func.sum(Trade.net_pnl))
                .filter(
                    Trade.entry_time >= start,
                    Trade.entry_time <= end,
                    Trade.status == "CLOSED",
                )
                .scalar()
            )
            return result or 0.0
        finally:
            session.close()

    # ========================================================================
    # MARKET DATA OPERATIONS
    # ========================================================================

    def save_market_data(self, data: Dict) -> MarketData:
        """Save market data"""
        session = self.get_session()
        try:
            market_data = MarketData(**data)
            session.add(market_data)
            session.commit()
            session.refresh(market_data)
            return market_data
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_latest_market_data(self, instrument: str) -> Optional[MarketData]:
        """Get latest market data for an instrument"""
        session = self.get_session()
        try:
            return (
                session.query(MarketData)
                .filter(MarketData.instrument == instrument)
                .order_by(desc(MarketData.timestamp))
                .first()
            )
        finally:
            session.close()

    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================

    def create_signal(self, signal_data: Dict) -> Signal:
        """Create a new signal record"""
        session = self.get_session()
        try:
            signal = Signal(**signal_data)
            session.add(signal)
            session.commit()
            session.refresh(signal)
            return signal
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_signal(self, signal_id: str, update_data: Dict) -> Signal:
        """Update a signal"""
        session = self.get_session()
        try:
            signal = session.query(Signal).filter(Signal.signal_id == signal_id).first()
            if signal:
                for key, value in update_data.items():
                    setattr(signal, key, value)
                session.commit()
                session.refresh(signal)
            return signal
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ========================================================================
    # SYSTEM LOG OPERATIONS
    # ========================================================================

    def log(self, level: str, module: str, message: str, details: Optional[str] = None):
        """Create a system log entry"""
        session = self.get_session()
        try:
            log = SystemLog(
                timestamp=datetime.now(),
                log_level=level,
                module=module,
                message=message,
                details=details,
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Failed to create log entry: {e}")
        finally:
            session.close()

    # ========================================================================
    # STATISTICS & REPORTING
    # ========================================================================

    def get_performance_stats(self, start_date: date, end_date: date) -> Dict:
        """Get performance statistics for a date range"""
        session = self.get_session()
        try:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())

            trades = (
                session.query(Trade)
                .filter(
                    Trade.entry_time >= start_dt,
                    Trade.entry_time <= end_dt,
                    Trade.status == "CLOSED",
                )
                .all()
            )

            if not trades:
                return {}

            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.is_winning_trade])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = sum(t.net_pnl for t in trades)
            avg_win = (
                sum(t.net_pnl for t in trades if t.is_winning_trade) / winning_trades
                if winning_trades > 0
                else 0
            )
            avg_loss = (
                sum(t.net_pnl for t in trades if not t.is_winning_trade) / losing_trades
                if losing_trades > 0
                else 0
            )

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "largest_win": max((t.net_pnl for t in trades), default=0),
                "largest_loss": min((t.net_pnl for t in trades), default=0),
            }
        finally:
            session.close()

    def close(self):
        """Close database connection"""
        self.Session.remove()
        self.engine.dispose()
