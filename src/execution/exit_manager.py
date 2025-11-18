"""
Exit Manager
Monitors positions and manages exits
"""
import logging
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
import pytz

from src.execution.order_manager import OrderManager
from src.data.option_chain import OptionChainHandler
from src.database.db_manager import DatabaseManager

from config.settings import (
    EXIT_TIME,
    PROFIT_TARGET_MIN,
    PROFIT_TARGET_MAX,
    STOP_LOSS_MULTIPLIER,
)
from config.constants import (
    EXIT_REASON_PROFIT_TARGET,
    EXIT_REASON_STOP_LOSS,
    EXIT_REASON_TIME_EXIT,
    EXIT_REASON_DAILY_LOSS_LIMIT,
)

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class ExitManager:
    """Manage position exits"""

    def __init__(
        self,
        order_manager: OrderManager,
        option_chain: OptionChainHandler,
        db: DatabaseManager,
    ):
        """
        Initialize exit manager

        Args:
            order_manager: Order manager instance
            option_chain: Option chain handler
            db: Database manager
        """
        self.order_manager = order_manager
        self.option_chain = option_chain
        self.db = db

    def check_exit_conditions(self, trade: Dict) -> Tuple[bool, str]:
        """
        Check if any exit condition is met

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (should_exit, reason)
        """
        try:
            # Get current premiums
            symbol = trade["instrument"]
            expiry = datetime.fromisoformat(str(trade["entry_time"]))  # Simplification

            # Fetch actual expiry (should be stored in trade)
            from src.data.market_data import MarketDataHandler
            # This is simplified - in production, store expiry in trade

            current_sell_premium = self.option_chain.get_option_premium(
                symbol=symbol,
                expiry=expiry,
                strike=trade["sell_strike"],
                option_type=trade["option_type"],
            )

            if current_sell_premium is None:
                logger.warning(f"Failed to fetch current premium for {trade['trade_id']}")
                return False, "Unable to fetch premium"

            # Calculate current status
            entry_net_premium = trade["net_premium"]

            # For profit, we want the premium to decay (go lower)
            # Current P&L per lot
            premium_decay_percent = (
                (entry_net_premium - current_sell_premium) / entry_net_premium
            ) * 100 if entry_net_premium > 0 else 0

            logger.debug(
                f"{trade['trade_id']}: Entry ₹{entry_net_premium:.2f}, "
                f"Current ₹{current_sell_premium:.2f}, "
                f"Decay {premium_decay_percent:.2f}%"
            )

            # Check 1: Profit Target (40-50% premium decay)
            if premium_decay_percent >= (PROFIT_TARGET_MIN * 100):
                logger.info(
                    f"[TARGET] Profit target reached: {premium_decay_percent:.2f}% decay"
                )
                return True, EXIT_REASON_PROFIT_TARGET

            # Check 2: Stop Loss (sold premium × 1.5)
            stop_loss_value = trade.get("stop_loss_value", entry_net_premium * STOP_LOSS_MULTIPLIER)

            if current_sell_premium >= stop_loss_value:
                logger.warning(
                    f"[STOPLOSS] Stop loss hit: Current Rs.{current_sell_premium:.2f} >= SL Rs.{stop_loss_value:.2f}"
                )
                return True, EXIT_REASON_STOP_LOSS

            # Check 3: Time Exit (3:10 PM)
            current_time = datetime.now(IST).time()

            if current_time >= EXIT_TIME:
                logger.info(f"[TIME EXIT] Time exit: {current_time.strftime('%H:%M')} >= {EXIT_TIME.strftime('%H:%M')}")
                return True, EXIT_REASON_TIME_EXIT

            # No exit condition met
            return False, "Position OK"

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, f"Error: {e}"

    def monitor_positions(self) -> List[Dict]:
        """
        Monitor all open positions and exit if needed

        Returns:
            List of closed trades
        """
        try:
            closed_trades = []

            # Get all open positions
            open_trades = self.order_manager.get_open_positions()

            if not open_trades:
                logger.debug("No open positions to monitor")
                return closed_trades

            logger.info(f"Monitoring {len(open_trades)} open position(s)...")

            for trade in open_trades:
                # Convert SQLAlchemy object to dict
                trade_dict = {
                    "trade_id": trade.trade_id,
                    "instrument": trade.instrument,
                    "sell_strike": trade.sell_strike,
                    "buy_strike": trade.buy_strike,
                    "option_type": trade.option_type,
                    "net_premium": trade.net_premium,
                    "entry_time": trade.entry_time,
                    "stop_loss_value": trade.stop_loss_value,
                    "quantity": trade.quantity,
                    "lot_size": trade.lot_size,
                }

                # Check exit conditions
                should_exit, reason = self.check_exit_conditions(trade_dict)

                if should_exit:
                    logger.info(
                        f"Exit signal for {trade.trade_id}: {reason}"
                    )

                    # Execute exit
                    success = self.order_manager.close_position(trade_dict)

                    if success:
                        # Update exit reason in database
                        self.db.update_trade(
                            trade.trade_id, {"exit_reason": reason}
                        )
                        closed_trades.append(trade_dict)
                        logger.info(f"Position closed successfully: {trade.trade_id}")
                    else:
                        logger.error(f"Failed to close position: {trade.trade_id}")

            return closed_trades

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return []

    def force_exit_all_positions(self, reason: str = "MANUAL") -> int:
        """
        Force exit all open positions (emergency stop)

        Args:
            reason: Reason for force exit

        Returns:
            Number of positions closed
        """
        try:
            logger.warning(f"FORCE EXITING ALL POSITIONS: {reason}")

            open_trades = self.order_manager.get_open_positions()
            closed_count = 0

            for trade in open_trades:
                trade_dict = {
                    "trade_id": trade.trade_id,
                    "instrument": trade.instrument,
                    "sell_strike": trade.sell_strike,
                    "buy_strike": trade.buy_strike,
                    "option_type": trade.option_type,
                    "net_premium": trade.net_premium,
                    "entry_time": trade.entry_time,
                    "quantity": trade.quantity,
                    "lot_size": trade.lot_size,
                }

                success = self.order_manager.close_position(trade_dict)

                if success:
                    self.db.update_trade(trade.trade_id, {"exit_reason": reason})
                    closed_count += 1

            logger.info(f"Force exited {closed_count}/{len(open_trades)} positions")
            return closed_count

        except Exception as e:
            logger.error(f"Error in force exit: {e}")
            return 0

    def get_position_status(self, trade_id: str) -> Optional[Dict]:
        """
        Get current status of a position

        Args:
            trade_id: Trade ID

        Returns:
            Dict with position status
        """
        try:
            trade = self.db.get_trade(trade_id)

            if not trade or trade.status != "OPEN":
                return None

            # Fetch current premiums
            current_sell_premium = self.option_chain.get_option_premium(
                symbol=trade.instrument,
                expiry=trade.entry_time,  # Simplified
                strike=trade.sell_strike,
                option_type=trade.option_type,
            )

            if not current_sell_premium:
                return None

            # Calculate metrics
            entry_premium = trade.net_premium
            premium_decay = (
                (entry_premium - current_sell_premium) / entry_premium
            ) * 100 if entry_premium > 0 else 0

            # Calculate unrealized P&L
            pnl_per_lot = (entry_premium - current_sell_premium) * trade.lot_size
            unrealized_pnl = pnl_per_lot * (trade.quantity / trade.lot_size)

            # Time held
            time_held = datetime.now(IST) - trade.entry_time

            status = {
                "trade_id": trade_id,
                "entry_time": trade.entry_time,
                "time_held_minutes": time_held.total_seconds() / 60,
                "entry_premium": entry_premium,
                "current_premium": current_sell_premium,
                "premium_decay_percent": premium_decay,
                "unrealized_pnl": unrealized_pnl,
                "stop_loss_value": trade.stop_loss_value,
                "target_value": trade.target_value,
                "distance_to_sl_percent": (
                    (current_sell_premium - trade.stop_loss_value) / current_sell_premium * 100
                ),
                "distance_to_target_percent": (
                    (current_sell_premium - trade.target_value) / current_sell_premium * 100
                ),
            }

            return status

        except Exception as e:
            logger.error(f"Error getting position status: {e}")
            return None

    def should_time_exit(self) -> bool:
        """Check if it's time for time-based exit"""
        current_time = datetime.now(IST).time()
        return current_time >= EXIT_TIME

    def get_time_until_exit(self) -> int:
        """
        Get minutes until time exit

        Returns:
            Minutes until exit time
        """
        try:
            now = datetime.now(IST)
            exit_datetime = now.replace(
                hour=EXIT_TIME.hour,
                minute=EXIT_TIME.minute,
                second=0,
                microsecond=0,
            )

            if exit_datetime < now:
                return 0

            time_diff = exit_datetime - now
            minutes = int(time_diff.total_seconds() / 60)

            return minutes

        except Exception as e:
            logger.error(f"Error calculating time until exit: {e}")
            return 0
