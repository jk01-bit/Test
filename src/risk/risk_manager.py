"""
Risk Management Module
Monitors and manages trading risk
"""
import logging
from datetime import date, datetime
from typing import Dict, Tuple, Optional
import pytz

from src.database.db_manager import DatabaseManager
from src.data.option_chain import OptionChainHandler

from config.settings import (
    TOTAL_CAPITAL,
    MARGIN_UTILIZATION,
    MAX_DAILY_LOSS,
    MAX_POSITIONS,
)

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class RiskManager:
    """Manage trading risk and position limits"""

    def __init__(self, db: DatabaseManager, option_chain: OptionChainHandler):
        """
        Initialize risk manager

        Args:
            db: Database manager
            option_chain: Option chain handler
        """
        self.db = db
        self.option_chain = option_chain
        self.total_capital = TOTAL_CAPITAL
        self.margin_utilization = MARGIN_UTILIZATION
        self.max_daily_loss = MAX_DAILY_LOSS
        self.max_positions = MAX_POSITIONS

    def get_available_capital(self) -> float:
        """
        Calculate available capital for trading

        Returns:
            Available capital
        """
        try:
            # Total allowed capital
            allowed_capital = self.total_capital * self.margin_utilization

            # Get current open positions
            open_trades = self.db.get_open_trades()

            # Calculate used margin
            used_margin = sum(
                trade.margin_used for trade in open_trades if trade.margin_used
            )

            available = allowed_capital - used_margin

            logger.info(
                f"Capital: Total ₹{self.total_capital}, "
                f"Allowed (40%) ₹{allowed_capital:.2f}, "
                f"Used ₹{used_margin:.2f}, "
                f"Available ₹{available:.2f}"
            )

            return available

        except Exception as e:
            logger.error(f"Error calculating available capital: {e}")
            return 0

    def can_take_new_position(self, required_margin: float) -> Tuple[bool, str]:
        """
        Check if we can take a new position

        Args:
            required_margin: Margin required for new position

        Returns:
            Tuple of (can_take, reason)
        """
        try:
            # Check position limit
            open_trades = self.db.get_open_trades()

            if len(open_trades) >= self.max_positions:
                return False, f"Max positions reached ({len(open_trades)}/{self.max_positions})"

            # Check available capital
            available = self.get_available_capital()

            if available < required_margin:
                return (
                    False,
                    f"Insufficient capital: Required ₹{required_margin:.2f}, Available ₹{available:.2f}",
                )

            # Check daily loss limit
            if self.is_daily_loss_limit_reached():
                return False, "Daily loss limit reached"

            return True, "OK to take position"

        except Exception as e:
            logger.error(f"Error checking position eligibility: {e}")
            return False, f"Error: {e}"

    def is_daily_loss_limit_reached(self) -> bool:
        """
        Check if daily loss limit has been reached

        Returns:
            True if limit reached
        """
        try:
            today = date.today()
            daily_pnl = self.db.calculate_daily_pnl(today)

            if daily_pnl < 0 and abs(daily_pnl) >= self.max_daily_loss:
                logger.warning(
                    f"Daily loss limit reached: ₹{daily_pnl:.2f} "
                    f"(Limit: ₹{self.max_daily_loss})"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return False

    def get_daily_pnl(self) -> float:
        """Get today's P&L"""
        try:
            today = date.today()
            return self.db.calculate_daily_pnl(today)
        except Exception as e:
            logger.error(f"Error getting daily P&L: {e}")
            return 0

    def should_stop_trading(self) -> Tuple[bool, str]:
        """
        Check if trading should be stopped

        Returns:
            Tuple of (should_stop, reason)
        """
        try:
            # Check daily loss limit
            if self.is_daily_loss_limit_reached():
                return True, "Daily loss limit reached"

            # Check if capital is critically low
            available = self.get_available_capital()
            if available < (self.total_capital * 0.1):  # Less than 10% available
                return True, "Capital critically low"

            return False, "Trading can continue"

        except Exception as e:
            logger.error(f"Error checking trading status: {e}")
            return True, f"Error: {e}"

    def calculate_position_risk(self, trade: Dict) -> Dict:
        """
        Calculate risk metrics for a position

        Args:
            trade: Trade dictionary

        Returns:
            Dict with risk metrics
        """
        try:
            # Maximum loss for the spread
            spread_width = abs(trade["sell_strike"] - trade["buy_strike"])
            max_loss_per_lot = (
                spread_width * trade["lot_size"] - trade["net_premium"] * trade["lot_size"]
            )

            lot_quantity = trade["quantity"] / trade["lot_size"]
            total_max_loss = max_loss_per_lot * lot_quantity

            # Risk to reward ratio
            potential_profit = trade["net_premium"] * trade["quantity"]
            risk_reward_ratio = total_max_loss / potential_profit if potential_profit > 0 else 0

            # Risk as percentage of capital
            risk_percent = (total_max_loss / self.total_capital) * 100

            risk_metrics = {
                "max_loss": total_max_loss,
                "potential_profit": potential_profit,
                "risk_reward_ratio": risk_reward_ratio,
                "risk_percent": risk_percent,
                "stop_loss_value": trade.get("stop_loss_value", 0),
            }

            logger.debug(
                f"Position Risk: Max Loss ₹{total_max_loss:.2f}, "
                f"Potential Profit ₹{potential_profit:.2f}, "
                f"R:R {risk_reward_ratio:.2f}, "
                f"Risk {risk_percent:.2f}% of capital"
            )

            return risk_metrics

        except Exception as e:
            logger.error(f"Error calculating position risk: {e}")
            return {}

    def get_portfolio_risk(self) -> Dict:
        """
        Calculate overall portfolio risk

        Returns:
            Dict with portfolio risk metrics
        """
        try:
            open_trades = self.db.get_open_trades()

            if not open_trades:
                return {
                    "total_positions": 0,
                    "total_margin_used": 0,
                    "total_max_loss": 0,
                    "total_potential_profit": 0,
                    "capital_at_risk_percent": 0,
                }

            total_margin = sum(t.margin_used for t in open_trades if t.margin_used)
            total_max_loss = 0
            total_potential_profit = 0

            for trade in open_trades:
                trade_dict = {
                    "sell_strike": trade.sell_strike,
                    "buy_strike": trade.buy_strike,
                    "net_premium": trade.net_premium,
                    "lot_size": trade.lot_size,
                    "quantity": trade.quantity,
                    "stop_loss_value": trade.stop_loss_value,
                }

                risk = self.calculate_position_risk(trade_dict)
                total_max_loss += risk.get("max_loss", 0)
                total_potential_profit += risk.get("potential_profit", 0)

            capital_at_risk_percent = (total_max_loss / self.total_capital) * 100

            portfolio_risk = {
                "total_positions": len(open_trades),
                "total_margin_used": total_margin,
                "total_max_loss": total_max_loss,
                "total_potential_profit": total_potential_profit,
                "capital_at_risk_percent": capital_at_risk_percent,
            }

            logger.info(
                f"Portfolio Risk: {len(open_trades)} positions, "
                f"Margin ₹{total_margin:.2f}, "
                f"Max Loss ₹{total_max_loss:.2f} ({capital_at_risk_percent:.2f}%)"
            )

            return portfolio_risk

        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {}

    def check_circuit_breaker(self) -> Tuple[bool, str]:
        """
        Emergency circuit breaker checks

        Returns:
            Tuple of (triggered, reason)
        """
        try:
            # Check daily loss
            daily_pnl = self.get_daily_pnl()

            # Trigger if loss exceeds 1.5x daily limit
            if daily_pnl < 0 and abs(daily_pnl) >= (self.max_daily_loss * 1.5):
                return True, f"Emergency stop: Daily loss ₹{daily_pnl:.2f}"

            # Check portfolio risk
            portfolio = self.get_portfolio_risk()

            # Trigger if more than 50% of capital at risk
            if portfolio.get("capital_at_risk_percent", 0) > 50:
                return True, "Emergency stop: Excessive capital at risk"

            return False, "No circuit breaker triggered"

        except Exception as e:
            logger.error(f"Error in circuit breaker check: {e}")
            return True, f"Circuit breaker error: {e}"
