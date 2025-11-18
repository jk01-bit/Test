"""
Entry Filters
Validate conditions before taking a trade
"""
import logging
from datetime import datetime, time
from typing import Tuple
import pytz

from config.settings import (
    MAX_VIX,
    MAX_GAP_PERCENT,
    ENTRY_START_TIME,
    ENTRY_END_TIME,
    EXPIRY_CUTOFF_TIME,
    MAX_POSITIONS,
)
from config.constants import (
    FILTER_VIX_HIGH,
    FILTER_GAP_LARGE,
    FILTER_OUTSIDE_TIME,
    FILTER_EXPIRY_LATE,
    FILTER_NO_TREND,
    FILTER_POSITION_EXISTS,
    FILTER_CAPITAL_INSUFFICIENT,
    FILTER_DAILY_LOSS_LIMIT,
    TREND_UPTREND,
    TREND_DOWNTREND,
)

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class EntryFilters:
    """Apply entry filters to validate trade signals"""

    def __init__(self, db_manager):
        """
        Initialize filters

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    def check_vix_filter(self, india_vix: float) -> Tuple[bool, str]:
        """
        Check if India VIX is within acceptable range

        Args:
            india_vix: Current India VIX value

        Returns:
            Tuple of (passed, reason)
        """
        if india_vix is None:
            logger.warning("India VIX value is None")
            return False, "Unable to fetch India VIX"

        if india_vix > MAX_VIX:
            logger.warning(
                f"India VIX too high: {india_vix} (Max: {MAX_VIX})"
            )
            return False, FILTER_VIX_HIGH

        logger.info(f"✓ VIX filter passed: {india_vix} < {MAX_VIX}")
        return True, "VIX OK"

    def check_gap_filter(self, gap_percent: float) -> Tuple[bool, str]:
        """
        Check if gap is within acceptable range

        Args:
            gap_percent: Gap percentage (absolute value)

        Returns:
            Tuple of (passed, reason)
        """
        if gap_percent is None:
            gap_percent = 0

        if gap_percent > MAX_GAP_PERCENT:
            logger.warning(
                f"Gap too large: {gap_percent:.2f}% (Max: {MAX_GAP_PERCENT}%)"
            )
            return False, FILTER_GAP_LARGE

        logger.info(
            f"✓ Gap filter passed: {gap_percent:.2f}% < {MAX_GAP_PERCENT}%"
        )
        return True, "Gap OK"

    def check_time_filter(self, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Check if current time is within entry window

        Args:
            current_time: Current time (defaults to now)

        Returns:
            Tuple of (passed, reason)
        """
        if current_time is None:
            current_time = datetime.now(IST)

        time_now = current_time.time()

        # Check if within entry window
        if ENTRY_START_TIME <= time_now <= ENTRY_END_TIME:
            logger.info(
                f"✓ Time filter passed: {time_now.strftime('%H:%M')} "
                f"in window [{ENTRY_START_TIME.strftime('%H:%M')} - "
                f"{ENTRY_END_TIME.strftime('%H:%M')}]"
            )
            return True, "Time OK"

        logger.warning(
            f"Outside entry window: {time_now.strftime('%H:%M')} "
            f"(Window: {ENTRY_START_TIME.strftime('%H:%M')} - "
            f"{ENTRY_END_TIME.strftime('%H:%M')})"
        )
        return False, FILTER_OUTSIDE_TIME

    def check_expiry_filter(
        self, expiry_date: datetime, current_time: datetime = None
    ) -> Tuple[bool, str]:
        """
        Check if it's safe to trade on expiry day

        Args:
            expiry_date: Expiry date
            current_time: Current time (defaults to now)

        Returns:
            Tuple of (passed, reason)
        """
        if current_time is None:
            current_time = datetime.now(IST)

        # Check if today is expiry day
        is_expiry_day = expiry_date.date() == current_time.date()

        if is_expiry_day:
            time_now = current_time.time()

            # Don't trade after cutoff time on expiry day
            if time_now >= EXPIRY_CUTOFF_TIME:
                logger.warning(
                    f"Expiry day - too late to trade: {time_now.strftime('%H:%M')} "
                    f"(Cutoff: {EXPIRY_CUTOFF_TIME.strftime('%H:%M')})"
                )
                return False, FILTER_EXPIRY_LATE

            logger.info(
                f"✓ Expiry filter passed: Expiry day but before cutoff time"
            )
            return True, "Expiry OK"

        logger.info("✓ Expiry filter passed: Not expiry day")
        return True, "Not expiry day"

    def check_trend_filter(self, trend: str) -> Tuple[bool, str]:
        """
        Check if trend is valid for trading

        Args:
            trend: Identified trend

        Returns:
            Tuple of (passed, reason)
        """
        if trend not in [TREND_UPTREND, TREND_DOWNTREND]:
            logger.warning(f"No clear trend: {trend}")
            return False, FILTER_NO_TREND

        logger.info(f"✓ Trend filter passed: {trend}")
        return True, f"Trend: {trend}"

    def check_position_filter(self) -> Tuple[bool, str]:
        """
        Check if we already have open positions

        Returns:
            Tuple of (passed, reason)
        """
        open_trades = self.db.get_open_trades()

        if len(open_trades) >= MAX_POSITIONS:
            logger.warning(
                f"Max positions reached: {len(open_trades)}/{MAX_POSITIONS}"
            )
            return False, FILTER_POSITION_EXISTS

        logger.info(
            f"✓ Position filter passed: {len(open_trades)}/{MAX_POSITIONS} positions"
        )
        return True, "No blocking positions"

    def check_capital_filter(
        self, required_margin: float, available_capital: float
    ) -> Tuple[bool, str]:
        """
        Check if sufficient capital is available

        Args:
            required_margin: Required margin for trade
            available_capital: Available capital

        Returns:
            Tuple of (passed, reason)
        """
        if available_capital < required_margin:
            logger.warning(
                f"Insufficient capital: Required ₹{required_margin:.2f}, "
                f"Available ₹{available_capital:.2f}"
            )
            return False, FILTER_CAPITAL_INSUFFICIENT

        logger.info(
            f"✓ Capital filter passed: ₹{available_capital:.2f} >= "
            f"₹{required_margin:.2f}"
        )
        return True, "Capital OK"

    def check_daily_loss_limit(self, daily_loss_limit: float) -> Tuple[bool, str]:
        """
        Check if daily loss limit has been reached

        Args:
            daily_loss_limit: Maximum daily loss allowed

        Returns:
            Tuple of (passed, reason)
        """
        from datetime import date

        today = date.today()
        daily_pnl = self.db.calculate_daily_pnl(today)

        if daily_pnl < 0 and abs(daily_pnl) >= daily_loss_limit:
            logger.warning(
                f"Daily loss limit reached: ₹{daily_pnl:.2f} "
                f"(Limit: ₹{daily_loss_limit})"
            )
            return False, FILTER_DAILY_LOSS_LIMIT

        logger.info(
            f"✓ Daily loss filter passed: P&L ₹{daily_pnl:.2f} "
            f"(Limit: ₹{daily_loss_limit})"
        )
        return True, "Within daily limit"

    def apply_all_filters(
        self,
        trend: str,
        india_vix: float,
        gap_percent: float,
        expiry_date: datetime,
        required_margin: float,
        available_capital: float,
        daily_loss_limit: float,
        current_time: datetime = None,
    ) -> Tuple[bool, str]:
        """
        Apply all entry filters

        Args:
            trend: Identified trend
            india_vix: India VIX value
            gap_percent: Gap percentage
            expiry_date: Expiry date
            required_margin: Required margin
            available_capital: Available capital
            daily_loss_limit: Daily loss limit
            current_time: Current time (defaults to now)

        Returns:
            Tuple of (all_passed, failure_reason)
        """
        logger.info("=" * 60)
        logger.info("APPLYING ENTRY FILTERS")
        logger.info("=" * 60)

        # List of all filters to check
        filters = [
            ("Daily Loss Limit", self.check_daily_loss_limit(daily_loss_limit)),
            ("Time Window", self.check_time_filter(current_time)),
            ("Trend", self.check_trend_filter(trend)),
            ("VIX", self.check_vix_filter(india_vix)),
            ("Gap", self.check_gap_filter(gap_percent)),
            ("Expiry", self.check_expiry_filter(expiry_date, current_time)),
            ("Position Limit", self.check_position_filter()),
            ("Capital", self.check_capital_filter(required_margin, available_capital)),
        ]

        # Check each filter
        failed_filters = []
        for filter_name, (passed, reason) in filters:
            if not passed:
                failed_filters.append(f"{filter_name}: {reason}")
                logger.error(f"✗ {filter_name} filter FAILED: {reason}")

        logger.info("=" * 60)

        if failed_filters:
            failure_reason = " | ".join(failed_filters)
            logger.warning(f"FILTERS FAILED: {failure_reason}")
            return False, failure_reason

        logger.info("✓ ALL FILTERS PASSED - SIGNAL IS VALID")
        logger.info("=" * 60)
        return True, "All filters passed"
