"""
Option Chain Handler
Manages option chain data and strike selection
"""
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import pandas as pd

from src.brokers.zerodha_broker import ZerodhaBroker
from config.constants import OPTION_TYPE_CE, OPTION_TYPE_PE, LOT_SIZES, STRIKE_INTERVALS
from config.settings import ATM_OFFSET_MIN, ATM_OFFSET_MAX, SPREAD_WIDTH

logger = logging.getLogger(__name__)


class OptionChainHandler:
    """Handle option chain operations"""

    def __init__(self, broker: ZerodhaBroker):
        """
        Initialize option chain handler

        Args:
            broker: Broker instance
        """
        self.broker = broker

    def get_atm_strike(self, symbol: str, spot_price: float) -> float:
        """
        Get ATM strike for a given spot price

        Args:
            symbol: NIFTY or BANKNIFTY
            spot_price: Current spot price

        Returns:
            ATM strike price
        """
        return self.broker.get_atm_strike(symbol, spot_price)

    def select_strikes_for_spread(
        self,
        symbol: str,
        spot_price: float,
        option_type: str,
        offset: int = ATM_OFFSET_MIN,
    ) -> Tuple[float, float]:
        """
        Select strikes for a spread based on strategy rules

        For Bull Put Spread (uptrend):
        - Sell: ATM + 150 (or +200) PE
        - Buy: Sell Strike - 200 PE

        For Bear Call Spread (downtrend):
        - Sell: ATM + 150 (or +200) CE
        - Buy: Sell Strike + 200 CE

        Args:
            symbol: NIFTY or BANKNIFTY
            spot_price: Current spot price
            option_type: CE or PE
            offset: Offset from ATM (150 or 200)

        Returns:
            Tuple of (sell_strike, buy_strike)
        """
        try:
            atm_strike = self.get_atm_strike(symbol, spot_price)

            # Get strike interval for the symbol (NIFTY=50, BANKNIFTY=100)
            strike_interval = STRIKE_INTERVALS.get(symbol, 50)

            # Round offset and spread width to valid multiples of strike interval
            # For NIFTY (50): 150 -> 150, 200 -> 200
            # For BANKNIFTY (100): 150 -> 200, 200 -> 200
            adjusted_offset = round(offset / strike_interval) * strike_interval
            adjusted_spread_width = round(SPREAD_WIDTH / strike_interval) * strike_interval

            logger.info(
                f"Strike interval for {symbol}: {strike_interval}, "
                f"Adjusted offset: {adjusted_offset}, Adjusted spread width: {adjusted_spread_width}"
            )

            if option_type == OPTION_TYPE_PE:
                # Bull Put Spread
                # Sell ATM - offset (OTM put)
                sell_strike = atm_strike - adjusted_offset

                # Buy further OTM (Sell - SPREAD_WIDTH)
                buy_strike = sell_strike - adjusted_spread_width

                logger.info(
                    f"Bull Put Spread strikes: Sell {sell_strike} PE, "
                    f"Buy {buy_strike} PE (ATM: {atm_strike})"
                )

            else:  # CE
                # Bear Call Spread
                # Sell ATM + offset (OTM call)
                sell_strike = atm_strike + adjusted_offset

                # Buy further OTM (Sell + SPREAD_WIDTH)
                buy_strike = sell_strike + adjusted_spread_width

                logger.info(
                    f"Bear Call Spread strikes: Sell {sell_strike} CE, "
                    f"Buy {buy_strike} CE (ATM: {atm_strike})"
                )

            return sell_strike, buy_strike

        except Exception as e:
            logger.error(f"Error selecting strikes: {e}")
            return None, None

    def get_option_premium(
        self,
        symbol: str,
        expiry: datetime,
        strike: float,
        option_type: str,
    ) -> Optional[float]:
        """
        Get current premium for an option

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date
            strike: Strike price
            option_type: CE or PE

        Returns:
            Current premium (LTP)
        """
        try:
            trading_symbol = self.broker.get_option_trading_symbol(
                symbol=symbol,
                expiry=expiry,
                strike=strike,
                option_type=option_type,
            )

            if not trading_symbol:
                logger.error(
                    f"Could not find trading symbol for {symbol} {int(strike)} {option_type} "
                    f"expiry={expiry.strftime('%Y-%m-%d')}"
                )
                return None

            premium = self.broker.get_ltp(f"NFO:{trading_symbol}")

            if premium:
                logger.debug(
                    f"{trading_symbol} premium: ₹{premium}"
                )

            return premium

        except Exception as e:
            logger.error(f"Error fetching option premium: {e}")
            return None

    def get_spread_premiums(
        self,
        symbol: str,
        expiry: datetime,
        sell_strike: float,
        buy_strike: float,
        option_type: str,
    ) -> Dict:
        """
        Get premiums for both legs of a spread

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date
            sell_strike: Strike price to sell
            buy_strike: Strike price to buy
            option_type: CE or PE

        Returns:
            Dict with sell_premium, buy_premium, and net_credit
        """
        try:
            sell_premium = self.get_option_premium(
                symbol, expiry, sell_strike, option_type
            )

            buy_premium = self.get_option_premium(
                symbol, expiry, buy_strike, option_type
            )

            if sell_premium is None or buy_premium is None:
                return {
                    "sell_premium": None,
                    "buy_premium": None,
                    "net_credit": None,
                }

            net_credit = sell_premium - buy_premium

            logger.info(
                f"Spread premiums: Sell @ ₹{sell_premium}, "
                f"Buy @ ₹{buy_premium}, Net Credit: ₹{net_credit}"
            )

            return {
                "sell_premium": sell_premium,
                "buy_premium": buy_premium,
                "net_credit": net_credit,
            }

        except Exception as e:
            logger.error(f"Error getting spread premiums: {e}")
            return {
                "sell_premium": None,
                "buy_premium": None,
                "net_credit": None,
            }

    def get_trading_symbols(
        self,
        symbol: str,
        expiry: datetime,
        sell_strike: float,
        buy_strike: float,
        option_type: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get trading symbols for both legs

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date
            sell_strike: Sell strike
            buy_strike: Buy strike
            option_type: CE or PE

        Returns:
            Tuple of (sell_symbol, buy_symbol)
        """
        try:
            sell_symbol = self.broker.get_option_trading_symbol(
                symbol, expiry, sell_strike, option_type
            )

            buy_symbol = self.broker.get_option_trading_symbol(
                symbol, expiry, buy_strike, option_type
            )

            if sell_symbol and buy_symbol:
                logger.info(
                    f"Trading symbols: Sell {sell_symbol}, Buy {buy_symbol}"
                )

            return sell_symbol, buy_symbol

        except Exception as e:
            logger.error(f"Error getting trading symbols: {e}")
            return None, None

    def calculate_margin_required(
        self,
        symbol: str,
        lot_quantity: int,
        sell_premium: float,
        buy_premium: float,
    ) -> float:
        """
        Estimate margin required for the spread
        (Simplified calculation - actual margin may vary)

        Args:
            symbol: NIFTY or BANKNIFTY
            lot_quantity: Number of lots
            sell_premium: Premium received from selling
            buy_premium: Premium paid for buying

        Returns:
            Estimated margin required
        """
        try:
            lot_size = LOT_SIZES.get(symbol, 25)
            total_quantity = lot_quantity * lot_size

            # For credit spreads, margin is approximately:
            # (Spread Width × Lot Size × Lots) - Net Premium Received
            spread_width = SPREAD_WIDTH
            max_loss = (spread_width * total_quantity) - (
                (sell_premium - buy_premium) * total_quantity
            )

            # Add buffer for broker margin requirements (~20%)
            estimated_margin = max_loss * 1.2

            logger.debug(
                f"Estimated margin for {lot_quantity} lots of {symbol}: "
                f"₹{estimated_margin:.2f}"
            )

            return estimated_margin

        except Exception as e:
            logger.error(f"Error calculating margin: {e}")
            return 0

    def validate_strikes(
        self,
        symbol: str,
        expiry: datetime,
        sell_strike: float,
        buy_strike: float,
        option_type: str,
    ) -> Tuple[bool, str]:
        """
        Validate if the selected strikes are tradeable

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date
            sell_strike: Sell strike
            buy_strike: Buy strike
            option_type: CE or PE

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Get trading symbols
            sell_symbol, buy_symbol = self.get_trading_symbols(
                symbol, expiry, sell_strike, buy_strike, option_type
            )

            if not sell_symbol or not buy_symbol:
                return False, "Strike prices not available in option chain"

            # Get premiums
            premiums = self.get_spread_premiums(
                symbol, expiry, sell_strike, buy_strike, option_type
            )

            if premiums["net_credit"] is None:
                return False, "Unable to fetch premiums"

            # Check if net credit is positive
            if premiums["net_credit"] <= 0:
                return False, f"Negative or zero credit: ₹{premiums['net_credit']}"

            # Check if premium is reasonable (not too low)
            if premiums["net_credit"] < 5:
                return False, f"Credit too low: ₹{premiums['net_credit']}"

            return True, "Strikes are valid"

        except Exception as e:
            logger.error(f"Error validating strikes: {e}")
            return False, f"Validation error: {e}"
