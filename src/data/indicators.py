"""
Technical Indicators
Calculate EMAs, CPR (Central Pivot Range), and identify trends
"""
import logging
from typing import Dict, Optional, Tuple
import pandas as pd
import pandas_ta as ta

from config.settings import FAST_EMA, SLOW_EMA, EMA_FLAT_THRESHOLD
from config.constants import TREND_UPTREND, TREND_DOWNTREND, TREND_SIDEWAYS

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """Calculate technical indicators and identify trends"""

    def __init__(self):
        """Initialize indicator engine"""
        self.fast_ema_period = FAST_EMA
        self.slow_ema_period = SLOW_EMA

    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            df: DataFrame with 'close' prices
            period: EMA period

        Returns:
            Series with EMA values
        """
        try:
            if "close" not in df.columns:
                logger.error("DataFrame missing 'close' column")
                return pd.Series()

            ema = ta.ema(df["close"], length=period)
            return ema

        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return pd.Series()

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators (20 EMA and 50 EMA)

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with indicators added
        """
        try:
            if df.empty:
                logger.warning("Empty DataFrame provided")
                return df

            # Make a copy to avoid modifying original
            result_df = df.copy()

            # Calculate EMAs
            result_df["ema_20"] = self.calculate_ema(result_df, self.fast_ema_period)
            result_df["ema_50"] = self.calculate_ema(result_df, self.slow_ema_period)

            # Drop rows with NaN values (initial period where EMA can't be calculated)
            result_df = result_df.dropna()

            logger.debug(f"Calculated indicators for {len(result_df)} candles")

            return result_df

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    def identify_trend(
        self, current_price: float, ema_20: float, ema_50: float
    ) -> str:
        """
        Identify trend based on EMAs and price position

        Strategy Rules:
        - Uptrend: 20 EMA > 50 EMA AND price > 20 EMA
        - Downtrend: 20 EMA < 50 EMA AND price < 20 EMA
        - Sideways: EMAs are flat (difference < threshold)

        Args:
            current_price: Current spot price
            ema_20: 20 EMA value
            ema_50: 50 EMA value

        Returns:
            Trend type (UPTREND, DOWNTREND, SIDEWAYS)
        """
        try:
            # Calculate EMA difference percentage
            ema_diff_percent = abs((ema_20 - ema_50) / ema_50)

            # Check if EMAs are flat
            if ema_diff_percent < EMA_FLAT_THRESHOLD:
                logger.info(
                    f"Trend: SIDEWAYS (EMAs flat - diff: {ema_diff_percent:.4f})"
                )
                return TREND_SIDEWAYS

            # Check for uptrend
            if ema_20 > ema_50 and current_price > ema_20:
                logger.info(
                    f"Trend: UPTREND (Price: {current_price}, "
                    f"20EMA: {ema_20:.2f}, 50EMA: {ema_50:.2f})"
                )
                return TREND_UPTREND

            # Check for downtrend
            if ema_20 < ema_50 and current_price < ema_20:
                logger.info(
                    f"Trend: DOWNTREND (Price: {current_price}, "
                    f"20EMA: {ema_20:.2f}, 50EMA: {ema_50:.2f})"
                )
                return TREND_DOWNTREND

            # If conditions don't match clearly
            logger.info(
                f"Trend: SIDEWAYS (Mixed signals - Price: {current_price}, "
                f"20EMA: {ema_20:.2f}, 50EMA: {ema_50:.2f})"
            )
            return TREND_SIDEWAYS

        except Exception as e:
            logger.error(f"Error identifying trend: {e}")
            return TREND_SIDEWAYS

    def get_latest_trend(self, df: pd.DataFrame) -> Dict:
        """
        Get latest trend from DataFrame with indicators

        Args:
            df: DataFrame with OHLC and indicator data

        Returns:
            Dict with trend information
        """
        try:
            if df.empty or len(df) == 0:
                return {
                    "trend": TREND_SIDEWAYS,
                    "price": None,
                    "ema_20": None,
                    "ema_50": None,
                }

            # Get latest values
            latest = df.iloc[-1]

            current_price = latest["close"]
            ema_20 = latest.get("ema_20", None)
            ema_50 = latest.get("ema_50", None)

            if ema_20 is None or ema_50 is None:
                logger.warning("EMAs not calculated")
                return {
                    "trend": TREND_SIDEWAYS,
                    "price": current_price,
                    "ema_20": None,
                    "ema_50": None,
                }

            # Identify trend
            trend = self.identify_trend(current_price, ema_20, ema_50)

            return {
                "trend": trend,
                "price": current_price,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "timestamp": latest.get("date", None),
            }

        except Exception as e:
            logger.error(f"Error getting latest trend: {e}")
            return {
                "trend": TREND_SIDEWAYS,
                "price": None,
                "ema_20": None,
                "ema_50": None,
            }

    def is_strong_trend(self, ema_20: float, ema_50: float, threshold: float = 0.005) -> bool:
        """
        Check if trend is strong based on EMA separation

        Args:
            ema_20: 20 EMA value
            ema_50: 50 EMA value
            threshold: Minimum separation percentage (default 0.5%)

        Returns:
            True if trend is strong
        """
        try:
            separation = abs((ema_20 - ema_50) / ema_50)
            is_strong = separation >= threshold

            logger.debug(
                f"Trend strength: {separation:.4f} (threshold: {threshold}) "
                f"- {'Strong' if is_strong else 'Weak'}"
            )

            return is_strong

        except Exception as e:
            logger.error(f"Error checking trend strength: {e}")
            return False

    def get_ema_crossover(self, df: pd.DataFrame, lookback: int = 5) -> Optional[str]:
        """
        Detect recent EMA crossover

        Args:
            df: DataFrame with EMA data
            lookback: Number of candles to look back

        Returns:
            'bullish' for bullish crossover, 'bearish' for bearish crossover, None otherwise
        """
        try:
            if len(df) < lookback + 1:
                return None

            recent = df.tail(lookback + 1)

            # Check for bullish crossover (20 EMA crosses above 50 EMA)
            if (
                recent.iloc[-1]["ema_20"] > recent.iloc[-1]["ema_50"]
                and recent.iloc[0]["ema_20"] <= recent.iloc[0]["ema_50"]
            ):
                logger.info("Bullish EMA crossover detected")
                return "bullish"

            # Check for bearish crossover (20 EMA crosses below 50 EMA)
            if (
                recent.iloc[-1]["ema_20"] < recent.iloc[-1]["ema_50"]
                and recent.iloc[0]["ema_20"] >= recent.iloc[0]["ema_50"]
            ):
                logger.info("Bearish EMA crossover detected")
                return "bearish"

            return None

        except Exception as e:
            logger.error(f"Error detecting crossover: {e}")
            return None

    def validate_trend_quality(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate if the trend is of good quality for trading

        Args:
            df: DataFrame with indicator data

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            if df.empty or len(df) < 10:
                return False, "Insufficient data"

            latest = df.iloc[-1]
            ema_20 = latest.get("ema_20")
            ema_50 = latest.get("ema_50")

            if ema_20 is None or ema_50 is None:
                return False, "EMAs not calculated"

            # Check if EMAs are flat
            if abs((ema_20 - ema_50) / ema_50) < EMA_FLAT_THRESHOLD:
                return False, "EMAs are flat - no clear trend"

            # Check for strong trend
            if not self.is_strong_trend(ema_20, ema_50):
                return False, "Trend is not strong enough"

            # Check for consistent trend over last few candles
            last_n = df.tail(5)
            trends = []
            for idx, row in last_n.iterrows():
                price = row["close"]
                e20 = row["ema_20"]
                e50 = row["ema_50"]
                trend = self.identify_trend(price, e20, e50)
                trends.append(trend)

            # Count trend consistency
            if trends.count(TREND_UPTREND) >= 4:
                return True, "Strong uptrend"
            elif trends.count(TREND_DOWNTREND) >= 4:
                return True, "Strong downtrend"
            else:
                return False, "Inconsistent trend"

        except Exception as e:
            logger.error(f"Error validating trend quality: {e}")
            return False, f"Error: {e}"

    def calculate_cpr(
        self, prev_high: float, prev_low: float, prev_close: float
    ) -> Dict[str, float]:
        """
        Calculate Central Pivot Range (CPR) levels from previous day's OHLC

        CPR Components:
        - Pivot (P) = (High + Low + Close) / 3
        - Top CPR (TC) = (Pivot - BC) + Pivot = 2*P - BC
        - Bottom CPR (BC) = (High + Low) / 2

        Additional Levels:
        - R1 = (2 * Pivot) - Low
        - R2 = Pivot + (High - Low)
        - S1 = (2 * Pivot) - High
        - S2 = Pivot - (High - Low)

        Args:
            prev_high: Previous day's high
            prev_low: Previous day's low
            prev_close: Previous day's close

        Returns:
            Dict with CPR and pivot levels
        """
        try:
            # Calculate Pivot Point
            pivot = (prev_high + prev_low + prev_close) / 3

            # Calculate CPR (Central Pivot Range)
            bc = (prev_high + prev_low) / 2  # Bottom CPR
            tc = (2 * pivot) - bc  # Top CPR

            # Ensure TC > BC (swap if needed)
            if tc < bc:
                tc, bc = bc, tc

            # Calculate Support and Resistance levels
            r1 = (2 * pivot) - prev_low
            r2 = pivot + (prev_high - prev_low)
            s1 = (2 * pivot) - prev_high
            s2 = pivot - (prev_high - prev_low)

            cpr_levels = {
                "pivot": round(pivot, 2),
                "tc": round(tc, 2),  # Top CPR
                "bc": round(bc, 2),  # Bottom CPR
                "r1": round(r1, 2),  # Resistance 1
                "r2": round(r2, 2),  # Resistance 2
                "s1": round(s1, 2),  # Support 1
                "s2": round(s2, 2),  # Support 2
                "cpr_width": round(abs(tc - bc), 2),
                "cpr_width_percent": round((abs(tc - bc) / pivot) * 100, 4),
            }

            logger.info(
                f"CPR Levels - Pivot: {pivot:.2f}, TC: {tc:.2f}, BC: {bc:.2f}"
            )
            logger.debug(
                f"Support/Resistance - R1: {r1:.2f}, R2: {r2:.2f}, "
                f"S1: {s1:.2f}, S2: {s2:.2f}"
            )

            return cpr_levels

        except Exception as e:
            logger.error(f"Error calculating CPR: {e}")
            return {}

    def get_cpr_position(
        self, current_price: float, cpr_levels: Dict[str, float]
    ) -> str:
        """
        Determine price position relative to CPR

        Args:
            current_price: Current spot price
            cpr_levels: Dict with CPR levels (tc, bc, pivot)

        Returns:
            Position string: 'ABOVE_CPR', 'BELOW_CPR', or 'INSIDE_CPR'
        """
        try:
            if not cpr_levels:
                logger.warning("CPR levels not available")
                return "UNKNOWN"

            tc = cpr_levels.get("tc")
            bc = cpr_levels.get("bc")

            if tc is None or bc is None:
                return "UNKNOWN"

            if current_price > tc:
                position = "ABOVE_CPR"
                logger.info(
                    f"Price {current_price:.2f} is ABOVE CPR (TC: {tc:.2f})"
                )
            elif current_price < bc:
                position = "BELOW_CPR"
                logger.info(
                    f"Price {current_price:.2f} is BELOW CPR (BC: {bc:.2f})"
                )
            else:
                position = "INSIDE_CPR"
                logger.info(
                    f"Price {current_price:.2f} is INSIDE CPR "
                    f"(BC: {bc:.2f} - TC: {tc:.2f})"
                )

            return position

        except Exception as e:
            logger.error(f"Error determining CPR position: {e}")
            return "UNKNOWN"

    def validate_cpr_for_entry(
        self, current_price: float, cpr_levels: Dict[str, float], trend: str
    ) -> Tuple[bool, str]:
        """
        Validate if CPR condition is favorable for entry based on trend

        For Option Selling:
        - Bull Put Spread (UPTREND): Price should be ABOVE TC (Top CPR)
          → Confirms bullish strength, CPR acts as support
        - Bear Call Spread (DOWNTREND): Price should be BELOW BC (Bottom CPR)
          → Confirms bearish strength, CPR acts as resistance
        - INSIDE CPR: No trade (market is consolidating/indecisive)

        Args:
            current_price: Current spot price
            cpr_levels: Dict with CPR levels
            trend: UPTREND or DOWNTREND

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            if not cpr_levels:
                return False, "CPR levels not available"

            cpr_position = self.get_cpr_position(current_price, cpr_levels)

            tc = cpr_levels.get("tc", 0)
            bc = cpr_levels.get("bc", 0)

            # For Bull Put Spread (Uptrend) - Price must be above TC
            if trend == TREND_UPTREND:
                if cpr_position == "ABOVE_CPR":
                    reason = (
                        f"CPR OK: Price {current_price:.2f} > TC {tc:.2f} "
                        f"(bullish confirmation)"
                    )
                    logger.info(f"[OK] {reason}")
                    return True, reason
                elif cpr_position == "INSIDE_CPR":
                    reason = (
                        f"CPR FAIL: Price {current_price:.2f} inside CPR "
                        f"(BC: {bc:.2f} - TC: {tc:.2f}) - consolidation zone"
                    )
                    logger.warning(reason)
                    return False, reason
                else:  # BELOW_CPR
                    reason = (
                        f"CPR FAIL: Price {current_price:.2f} < BC {bc:.2f} "
                        f"- contradicts uptrend signal"
                    )
                    logger.warning(reason)
                    return False, reason

            # For Bear Call Spread (Downtrend) - Price must be below BC
            elif trend == TREND_DOWNTREND:
                if cpr_position == "BELOW_CPR":
                    reason = (
                        f"CPR OK: Price {current_price:.2f} < BC {bc:.2f} "
                        f"(bearish confirmation)"
                    )
                    logger.info(f"[OK] {reason}")
                    return True, reason
                elif cpr_position == "INSIDE_CPR":
                    reason = (
                        f"CPR FAIL: Price {current_price:.2f} inside CPR "
                        f"(BC: {bc:.2f} - TC: {tc:.2f}) - consolidation zone"
                    )
                    logger.warning(reason)
                    return False, reason
                else:  # ABOVE_CPR
                    reason = (
                        f"CPR FAIL: Price {current_price:.2f} > TC {tc:.2f} "
                        f"- contradicts downtrend signal"
                    )
                    logger.warning(reason)
                    return False, reason

            # Sideways or unknown trend
            return False, f"Invalid trend for CPR validation: {trend}"

        except Exception as e:
            logger.error(f"Error validating CPR for entry: {e}")
            return False, f"CPR validation error: {e}"
