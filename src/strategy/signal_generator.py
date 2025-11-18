"""
Signal Generator
Generates trading signals based on trend and filters
"""
import logging
from datetime import datetime
from typing import Optional, Dict
import uuid
import pytz

from src.data.market_data import MarketDataHandler
from src.data.indicators import IndicatorEngine
from src.data.option_chain import OptionChainHandler
from src.strategy.filters import EntryFilters
from src.database.db_manager import DatabaseManager

from config.constants import (
    TREND_UPTREND,
    TREND_DOWNTREND,
    TREND_SIDEWAYS,
    OPTION_TYPE_CE,
    OPTION_TYPE_PE,
    SPREAD_TYPE_BULL_PUT,
    SPREAD_TYPE_BEAR_CALL,
)
from config.settings import (
    ATM_OFFSET_MIN,
    TOTAL_CAPITAL,
    MARGIN_UTILIZATION,
    MAX_DAILY_LOSS,
    POSITION_SIZE,
)

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class SignalGenerator:
    """Generate trading signals"""

    def __init__(
        self,
        market_data: MarketDataHandler,
        indicator_engine: IndicatorEngine,
        option_chain: OptionChainHandler,
        filters: EntryFilters,
        db: DatabaseManager,
    ):
        """
        Initialize signal generator

        Args:
            market_data: Market data handler
            indicator_engine: Indicator engine
            option_chain: Option chain handler
            filters: Entry filters
            db: Database manager
        """
        self.market_data = market_data
        self.indicators = indicator_engine
        self.option_chain = option_chain
        self.filters = filters
        self.db = db

    def generate_signal(self, symbol: str) -> Optional[Dict]:
        """
        Generate trading signal for a symbol

        Args:
            symbol: NIFTY or BANKNIFTY

        Returns:
            Signal dict if valid signal found, None otherwise
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"GENERATING SIGNAL FOR {symbol}")
            logger.info(f"{'='*60}")

            # Step 1: Get market data
            logger.info("Step 1: Fetching market data...")
            candles = self.market_data.get_latest_candles(
                symbol=symbol, num_candles=100, interval="15minute"
            )

            if candles.empty:
                logger.error("Failed to fetch market data")
                return None

            # Step 2: Calculate indicators
            logger.info("Step 2: Calculating indicators...")
            candles_with_indicators = self.indicators.calculate_all_indicators(candles)

            if candles_with_indicators.empty:
                logger.error("Failed to calculate indicators")
                return None

            # Step 3: Identify trend
            logger.info("Step 3: Identifying trend...")
            trend_info = self.indicators.get_latest_trend(candles_with_indicators)

            trend = trend_info["trend"]
            spot_price = trend_info["price"]
            ema_20 = trend_info["ema_20"]
            ema_50 = trend_info["ema_50"]

            if trend == TREND_SIDEWAYS:
                logger.info("No clear trend - skipping signal")
                return None

            logger.info(
                f"Trend: {trend}, Spot: {spot_price}, "
                f"20EMA: {ema_20:.2f}, 50EMA: {ema_50:.2f}"
            )

            # Step 4: Get market conditions
            logger.info("Step 4: Checking market conditions...")
            india_vix = self.market_data.get_india_vix()
            gap_info = self.market_data.detect_gap(symbol)
            gap_percent = gap_info.get("gap_percent", 0)

            logger.info(f"India VIX: {india_vix}, Gap: {gap_percent:.2f}%")

            # Step 5: Determine spread type and option type
            if trend == TREND_UPTREND:
                spread_type = SPREAD_TYPE_BULL_PUT
                option_type = OPTION_TYPE_PE
                logger.info("Signal Type: Bull Put Spread (Sell Put Spread)")
            else:  # DOWNTREND
                spread_type = SPREAD_TYPE_BEAR_CALL
                option_type = OPTION_TYPE_CE
                logger.info("Signal Type: Bear Call Spread (Sell Call Spread)")

            # Step 6: Select strikes
            logger.info("Step 6: Selecting strikes...")
            expiry = self.market_data.get_next_expiry(symbol)

            if not expiry:
                logger.error("Failed to get expiry date")
                return None

            sell_strike, buy_strike = self.option_chain.select_strikes_for_spread(
                symbol=symbol,
                spot_price=spot_price,
                option_type=option_type,
                offset=ATM_OFFSET_MIN,
            )

            if not sell_strike or not buy_strike:
                logger.error("Failed to select strikes")
                return None

            # Step 7: Get premiums
            logger.info("Step 7: Fetching option premiums...")
            premiums = self.option_chain.get_spread_premiums(
                symbol=symbol,
                expiry=expiry,
                sell_strike=sell_strike,
                buy_strike=buy_strike,
                option_type=option_type,
            )

            if premiums["net_credit"] is None:
                logger.error("Failed to fetch premiums")
                return None

            # Step 8: Calculate position size
            logger.info("Step 8: Calculating position size...")
            lot_quantity = POSITION_SIZE.get(symbol, 2)

            # Step 9: Calculate margin
            logger.info("Step 9: Calculating margin requirement...")
            required_margin = self.option_chain.calculate_margin_required(
                symbol=symbol,
                lot_quantity=lot_quantity,
                sell_premium=premiums["sell_premium"],
                buy_premium=premiums["buy_premium"],
            )

            available_capital = TOTAL_CAPITAL * MARGIN_UTILIZATION

            # Step 10: Apply filters
            logger.info("Step 10: Applying entry filters...")
            filters_passed, filter_reason = self.filters.apply_all_filters(
                trend=trend,
                india_vix=india_vix,
                gap_percent=gap_percent,
                expiry_date=expiry,
                required_margin=required_margin,
                available_capital=available_capital,
                daily_loss_limit=MAX_DAILY_LOSS,
            )

            # Create signal object
            signal = {
                "signal_id": str(uuid.uuid4()),
                "timestamp": datetime.now(IST),
                "instrument": symbol,
                "trend": trend,
                "spread_type": spread_type,
                "spot_price": spot_price,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "india_vix": india_vix,
                "gap_percent": gap_percent,
                "option_type": option_type,
                "sell_strike": sell_strike,
                "buy_strike": buy_strike,
                "sell_premium": premiums["sell_premium"],
                "buy_premium": premiums["buy_premium"],
                "net_credit": premiums["net_credit"],
                "lot_quantity": lot_quantity,
                "required_margin": required_margin,
                "expiry": expiry,
                "filters_passed": filters_passed,
                "filter_reason": filter_reason,
            }

            # Save signal to database
            self._save_signal_to_db(signal)

            if filters_passed:
                logger.info("[VALID SIGNAL] SIGNAL GENERATED!")
                logger.info(f"{'='*60}\n")
                return signal
            else:
                logger.warning(f"[FILTERED] Signal filtered out: {filter_reason}")
                logger.info(f"{'='*60}\n")
                return None

        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return None

    def _save_signal_to_db(self, signal: Dict):
        """Save signal to database for tracking"""
        try:
            signal_data = {
                "signal_id": signal["signal_id"],
                "timestamp": signal["timestamp"],
                "instrument": signal["instrument"],
                "trend": signal["trend"],
                "signal_type": "ENTRY",
                "spot_price": signal["spot_price"],
                "ema_20": signal["ema_20"],
                "ema_50": signal["ema_50"],
                "india_vix": signal["india_vix"],
                "gap_percent": signal["gap_percent"],
                "is_valid": signal["filters_passed"],
                "filter_passed": signal["filters_passed"],
                "filter_reason": signal["filter_reason"] if not signal["filters_passed"] else None,
                "was_executed": False,
            }

            self.db.create_signal(signal_data)
            logger.debug("Signal saved to database")

        except Exception as e:
            logger.error(f"Error saving signal to database: {e}")

    def check_for_signals(self, instruments: list) -> Dict[str, Optional[Dict]]:
        """
        Check for signals across multiple instruments

        Args:
            instruments: List of instruments to check

        Returns:
            Dict of {instrument: signal}
        """
        signals = {}

        for instrument in instruments:
            signal = self.generate_signal(instrument)
            signals[instrument] = signal

        return signals
