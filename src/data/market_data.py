"""
Market Data Handler
Fetches and processes market data
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd
import pytz

from src.brokers.zerodha_broker import ZerodhaBroker
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class MarketDataHandler:
    """Handle market data fetching and storage"""

    def __init__(self, broker: ZerodhaBroker, db: DatabaseManager):
        """
        Initialize market data handler

        Args:
            broker: Broker instance
            db: Database manager
        """
        self.broker = broker
        self.db = db

        # Cache instrument tokens
        self.instrument_tokens = {}
        self._load_instrument_tokens()

    def _load_instrument_tokens(self):
        """Load and cache instrument tokens"""
        try:
            # Check if broker is connected
            if not hasattr(self.broker, 'is_connected') or not self.broker.is_connected:
                logger.warning("Broker not connected yet. Instrument tokens will be loaded after connection.")
                return

            instruments = self.broker.get_instruments("NSE")

            if instruments.empty:
                logger.error("No instruments returned from broker")
                return

            # Store tokens for indices
            for symbol in ["NIFTY 50", "NIFTY BANK", "INDIA VIX"]:
                data = instruments[instruments["tradingsymbol"] == symbol]
                if not data.empty:
                    self.instrument_tokens[symbol] = data.iloc[0]["instrument_token"]
                    logger.debug(f"Loaded token for {symbol}: {data.iloc[0]['instrument_token']}")
                else:
                    logger.warning(f"Symbol '{symbol}' not found in NSE instruments")

            logger.info(f"Loaded {len(self.instrument_tokens)} instrument tokens")

        except Exception as e:
            logger.error(f"Error loading instrument tokens: {e}")

    def reload_instruments(self):
        """Reload instrument tokens (call after broker connection)"""
        logger.info("Reloading instrument tokens...")
        self.instrument_tokens.clear()
        self._load_instrument_tokens()

    def get_spot_price(self, symbol: str) -> Optional[float]:
        """
        Get current spot price for an index

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Current spot price
        """
        try:
            if symbol == "NIFTY":
                symbol_name = "NIFTY 50"
            elif symbol == "BANKNIFTY":
                symbol_name = "NIFTY BANK"
            else:
                symbol_name = symbol

            trading_symbol = f"NSE:{symbol_name}"
            price = self.broker.get_ltp(trading_symbol)

            if price:
                logger.debug(f"{symbol} spot price: {price}")
                return price

            return None

        except Exception as e:
            logger.error(f"Error fetching spot price for {symbol}: {e}")
            return None

    def get_india_vix(self) -> Optional[float]:
        """Get current India VIX value"""
        try:
            vix = self.broker.get_ltp("NSE:INDIA VIX")
            if vix:
                logger.debug(f"India VIX: {vix}")
            return vix
        except Exception as e:
            logger.error(f"Error fetching India VIX: {e}")
            return None

    def get_historical_candles(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = "15minute",
    ) -> pd.DataFrame:
        """
        Fetch historical candle data

        Args:
            symbol: NIFTY or BANKNIFTY
            from_date: Start date
            to_date: End date
            interval: Candle interval

        Returns:
            DataFrame with OHLC data
        """
        try:
            if symbol == "NIFTY":
                symbol_name = "NIFTY 50"
            elif symbol == "BANKNIFTY":
                symbol_name = "NIFTY BANK"
            else:
                symbol_name = symbol

            token = self.instrument_tokens.get(symbol_name)
            if not token:
                logger.error(f"Instrument identifier not found for {symbol}")
                return pd.DataFrame()

            df = self.broker.get_historical_data(
                instrument_token=token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
            )

            if not df.empty:
                logger.info(
                    f"Fetched {len(df)} candles for {symbol} "
                    f"from {from_date} to {to_date}"
                )

            return df

        except Exception as e:
            logger.error(f"Error fetching historical candles: {e}")
            return pd.DataFrame()

    def get_latest_candles(
        self, symbol: str, num_candles: int = 100, interval: str = "15minute"
    ) -> pd.DataFrame:
        """
        Get latest N candles

        Args:
            symbol: NIFTY or BANKNIFTY
            num_candles: Number of candles to fetch
            interval: Candle interval

        Returns:
            DataFrame with OHLC data
        """
        try:
            # Calculate from_date based on number of candles needed
            # 15-minute candles: ~26 candles per trading day
            days_needed = (num_candles // 26) + 5  # Add buffer for holidays

            to_date = datetime.now(IST)
            from_date = to_date - timedelta(days=days_needed)

            df = self.get_historical_candles(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
            )

            # Return only the last N candles
            if not df.empty:
                return df.tail(num_candles)

            return df

        except Exception as e:
            logger.error(f"Error fetching latest candles: {e}")
            return pd.DataFrame()

    def detect_gap(self, symbol: str) -> Dict:
        """
        Detect gap up/down at market open

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Dict with gap_percent and is_large_gap
        """
        try:
            # Get today's data
            today = datetime.now(IST).date()
            to_date = datetime.combine(today, datetime.now(IST).time())
            from_date = to_date - timedelta(days=2)

            df = self.get_historical_candles(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval="day",
            )

            if len(df) >= 2:
                prev_close = df.iloc[-2]["close"]
                today_open = df.iloc[-1]["open"]

                gap_percent = ((today_open - prev_close) / prev_close) * 100

                result = {
                    "prev_close": prev_close,
                    "today_open": today_open,
                    "gap_percent": abs(gap_percent),
                    "gap_direction": "up" if gap_percent > 0 else "down",
                }

                logger.info(
                    f"{symbol} Gap: {gap_percent:.2f}% "
                    f"({prev_close} -> {today_open})"
                )

                return result

            return {"gap_percent": 0, "gap_direction": "none"}

        except Exception as e:
            logger.error(f"Error detecting gap: {e}")
            return {"gap_percent": 0, "gap_direction": "none"}

    def save_to_database(self, symbol: str, candle_data: pd.Series):
        """
        Save market data to database

        Args:
            symbol: Instrument symbol
            candle_data: Candle data as Series
        """
        try:
            data = {
                "instrument": symbol,
                "timestamp": candle_data["date"],
                "open": candle_data["open"],
                "high": candle_data["high"],
                "low": candle_data["low"],
                "close": candle_data["close"],
                "volume": candle_data.get("volume", 0),
            }

            self.db.save_market_data(data)
            logger.debug(f"Saved market data for {symbol}")

        except Exception as e:
            logger.error(f"Error saving market data to database: {e}")

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now(IST)
        current_time = now.time()

        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = now.replace(hour=9, minute=15, second=0)
        market_close = now.replace(hour=15, minute=30, second=0)

        # Check if it's a weekday (Monday=0 to Friday=4)
        is_weekday = now.weekday() < 5

        is_open = (
            is_weekday and market_open.time() <= current_time <= market_close.time()
        )

        return is_open

    def get_next_expiry(self, symbol: str) -> Optional[datetime]:
        """
        Get next expiry date for an instrument

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Next expiry datetime
        """
        try:
            instruments = self.broker.get_instruments("NFO")

            # Filter for the symbol
            symbol_instruments = instruments[instruments["name"] == symbol]

            if not symbol_instruments.empty:
                # Get unique expiry dates and sort
                expiries = pd.to_datetime(symbol_instruments["expiry"]).unique()
                expiries = sorted(expiries)

                # Find next expiry (today or future)
                today = datetime.now(IST).date()
                for expiry in expiries:
                    if expiry.date() >= today:
                        logger.info(f"Next expiry for {symbol}: {expiry.date()}")
                        return expiry

            return None

        except Exception as e:
            logger.error(f"Error getting next expiry: {e}")
            return None
