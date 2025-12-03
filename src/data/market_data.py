"""
Market Data Handler
Fetches and processes market data including CPR (Central Pivot Range)
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

        # Cache CPR levels (calculated once per day)
        self._cpr_cache = {}
        self._cpr_cache_date = None

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

    def get_previous_day_ohlc(self, symbol: str) -> Optional[Dict]:
        """
        Get previous trading day's OHLC data for CPR calculation

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Dict with high, low, close of previous day
        """
        try:
            # Get daily candles for last 5 days (to handle holidays/weekends)
            to_date = datetime.now(IST)
            from_date = to_date - timedelta(days=7)

            df = self.get_historical_candles(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval="day",
            )

            if df.empty or len(df) < 2:
                logger.error(f"Insufficient daily data for {symbol}")
                return None

            # Get previous day's data (second last row)
            prev_day = df.iloc[-2]

            ohlc = {
                "date": prev_day.get("date", None),
                "open": float(prev_day["open"]),
                "high": float(prev_day["high"]),
                "low": float(prev_day["low"]),
                "close": float(prev_day["close"]),
            }

            logger.info(
                f"Previous day OHLC for {symbol}: "
                f"O={ohlc['open']}, H={ohlc['high']}, "
                f"L={ohlc['low']}, C={ohlc['close']}"
            )

            return ohlc

        except Exception as e:
            logger.error(f"Error fetching previous day OHLC for {symbol}: {e}")
            return None

    def get_cpr_levels(self, symbol: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get CPR (Central Pivot Range) levels for a symbol

        CPR is calculated from previous day's High, Low, Close.
        Results are cached for the entire trading day.

        Args:
            symbol: NIFTY or BANKNIFTY
            force_refresh: Force recalculation even if cached

        Returns:
            Dict with CPR levels (pivot, tc, bc, r1, r2, s1, s2)
        """
        try:
            today = datetime.now(IST).date()

            # Check if we have cached CPR for today
            if (
                not force_refresh
                and self._cpr_cache_date == today
                and symbol in self._cpr_cache
            ):
                logger.debug(f"Using cached CPR levels for {symbol}")
                return self._cpr_cache[symbol]

            # Get previous day's OHLC
            prev_ohlc = self.get_previous_day_ohlc(symbol)

            if not prev_ohlc:
                logger.error(f"Cannot calculate CPR - no previous day data for {symbol}")
                return None

            # Calculate CPR using IndicatorEngine
            from src.data.indicators import IndicatorEngine

            indicator_engine = IndicatorEngine()
            cpr_levels = indicator_engine.calculate_cpr(
                prev_high=prev_ohlc["high"],
                prev_low=prev_ohlc["low"],
                prev_close=prev_ohlc["close"],
            )

            if cpr_levels:
                # Add metadata
                cpr_levels["prev_day_date"] = prev_ohlc.get("date")
                cpr_levels["calculated_at"] = datetime.now(IST)

                # Cache the result
                self._cpr_cache[symbol] = cpr_levels
                self._cpr_cache_date = today

                logger.info(
                    f"CPR calculated for {symbol}: "
                    f"Pivot={cpr_levels['pivot']}, "
                    f"TC={cpr_levels['tc']}, BC={cpr_levels['bc']}"
                )

            return cpr_levels

        except Exception as e:
            logger.error(f"Error calculating CPR for {symbol}: {e}")
            return None

    def get_cpr_with_current_price(self, symbol: str) -> Optional[Dict]:
        """
        Get CPR levels along with current price position

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Dict with CPR levels and current price position
        """
        try:
            # Get CPR levels
            cpr_levels = self.get_cpr_levels(symbol)

            if not cpr_levels:
                return None

            # Get current spot price
            spot_price = self.get_spot_price(symbol)

            if not spot_price:
                logger.error(f"Cannot get spot price for {symbol}")
                return None

            # Determine position relative to CPR
            from src.data.indicators import IndicatorEngine

            indicator_engine = IndicatorEngine()
            cpr_position = indicator_engine.get_cpr_position(spot_price, cpr_levels)

            result = {
                **cpr_levels,
                "spot_price": spot_price,
                "cpr_position": cpr_position,
            }

            logger.info(
                f"{symbol} CPR Status: Spot={spot_price}, "
                f"Position={cpr_position}, "
                f"CPR Range=[{cpr_levels['bc']}-{cpr_levels['tc']}]"
            )

            return result

        except Exception as e:
            logger.error(f"Error getting CPR with current price for {symbol}: {e}")
            return None
