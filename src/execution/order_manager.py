"""
Order Execution Manager
Handles order placement and tracking
"""
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
import uuid
import time
import pytz

from src.brokers.zerodha_broker import ZerodhaBroker
from src.data.option_chain import OptionChainHandler
from src.database.db_manager import DatabaseManager

from config.constants import (
    LOT_SIZES,
    ORDER_STATUS_COMPLETE,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_SELL,
)
from config.settings import PRODUCT_TYPE, ORDER_TYPE_LIMIT, STOP_LOSS_MULTIPLIER, PROFIT_TARGET_PER_LOT

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class OrderManager:
    """Manage order execution"""

    def __init__(
        self,
        broker: ZerodhaBroker,
        option_chain: OptionChainHandler,
        db: DatabaseManager,
    ):
        """
        Initialize order manager

        Args:
            broker: Broker instance
            option_chain: Option chain handler
            db: Database manager
        """
        self.broker = broker
        self.option_chain = option_chain
        self.db = db

    def execute_spread_order(self, signal: Dict) -> Optional[Dict]:
        """
        Execute spread order based on signal

        Args:
            signal: Signal dictionary

        Returns:
            Trade dict if successful, None otherwise
        """
        try:
            order_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"\n{'='*60}")
            logger.info(f"EXECUTING SPREAD ORDER - {order_time}")
            logger.info(f"{'='*60}")

            symbol = signal["instrument"]
            expiry = signal["expiry"]
            sell_strike = signal["sell_strike"]
            buy_strike = signal["buy_strike"]
            option_type = signal["option_type"]
            lot_quantity = signal["lot_quantity"]

            logger.info(f"Instrument: {symbol}")
            logger.info(f"Spread Type: {signal['spread_type']}")
            logger.info(f"Option Type: {option_type}")
            logger.info(f"Sell Strike: {sell_strike} | Buy Strike: {buy_strike}")
            logger.info(f"Expiry: {expiry.strftime('%Y-%m-%d') if hasattr(expiry, 'strftime') else expiry}")
            logger.info(f"Trend: {signal['trend']}")
            logger.info(f"Spot Price: Rs.{signal['spot_price']}")

            # Step 1: Get trading symbols
            logger.info("\nStep 1: Getting trading symbols...")
            sell_symbol, buy_symbol = self.option_chain.get_trading_symbols(
                symbol=symbol,
                expiry=expiry,
                sell_strike=sell_strike,
                buy_strike=buy_strike,
                option_type=option_type,
            )

            if not sell_symbol or not buy_symbol:
                logger.error("Failed to get trading symbols")
                return None

            logger.info(f"Sell: {sell_symbol}, Buy: {buy_symbol}")

            # Step 2: Calculate quantity
            lot_size = LOT_SIZES.get(symbol, 25)
            quantity = lot_quantity * lot_size

            logger.info(f"Quantity: {lot_quantity} lots × {lot_size} = {quantity}")

            # Step 3: Get current premiums
            logger.info("Step 2: Fetching current premiums...")
            sell_premium = self.option_chain.get_option_premium(
                symbol, expiry, sell_strike, option_type
            )
            buy_premium = self.option_chain.get_option_premium(
                symbol, expiry, buy_strike, option_type
            )

            if not sell_premium or not buy_premium:
                logger.error("Failed to fetch premiums")
                return None

            net_premium = sell_premium - buy_premium

            logger.info(
                f"Premiums: Sell ₹{sell_premium}, Buy ₹{buy_premium}, "
                f"Net Credit: ₹{net_premium}"
            )

            # Step 4: Place orders
            logger.info("Step 3: Placing spread orders...")
            sell_order_id, buy_order_id = self.broker.place_spread_order(
                sell_symbol=sell_symbol,
                sell_price=sell_premium,
                buy_symbol=buy_symbol,
                buy_price=buy_premium,
                quantity=quantity,
            )

            if not sell_order_id or not buy_order_id:
                logger.error("Failed to place orders")
                return None

            logger.info(
                f"Orders placed: Sell Order {sell_order_id}, Buy Order {buy_order_id}"
            )

            # Step 5: Verify order execution
            logger.info("Step 4: Verifying order execution...")
            time.sleep(2)  # Wait for orders to execute

            sell_status = self.broker.get_order_status(sell_order_id)
            buy_status = self.broker.get_order_status(buy_order_id)

            if not sell_status or not buy_status:
                logger.error("Failed to verify order status")
                # Should implement order cancellation here
                return None

            # Step 6: Create trade record
            logger.info("Step 5: Creating trade record...")
            trade_id = f"{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}"

            # Calculate stop loss
            stop_loss = sell_premium * STOP_LOSS_MULTIPLIER

            # Calculate target premium based on Rs.600 profit per lot
            # P&L per lot = (entry_net_premium - target_net_premium) × lot_size
            # 600 = (net_premium - target_net_premium) × lot_size
            # target_net_premium = net_premium - (600 / lot_size)
            lot_size = LOT_SIZES.get(symbol, 25)
            target_premium = net_premium - (PROFIT_TARGET_PER_LOT / lot_size)

            trade_data = {
                "trade_id": trade_id,
                "instrument": symbol,
                "spread_type": signal["spread_type"],
                "entry_time": datetime.now(IST),
                "expiry": expiry,  # Store option expiry date
                "entry_spot_price": signal["spot_price"],
                "trend": signal["trend"],
                "sell_strike": sell_strike,
                "buy_strike": buy_strike,
                "option_type": option_type,
                "sell_premium": sell_premium,
                "buy_premium": buy_premium,
                "net_premium": net_premium,
                "lot_size": lot_size,
                "quantity": quantity,
                "margin_used": signal["required_margin"],
                "sell_order_id": sell_order_id,
                "buy_order_id": buy_order_id,
                "stop_loss_value": stop_loss,
                "target_value": target_premium,
                "status": "OPEN",
            }

            # Save to database
            trade = self.db.create_trade(trade_data)

            logger.info(f"[OK] Trade created successfully: {trade_id}")
            logger.info(f"Stop Loss: Rs.{stop_loss:.2f} (sell premium)")
            logger.info(f"Target: Rs.{PROFIT_TARGET_PER_LOT} profit per lot (Net premium: Rs.{target_premium:.2f})")
            logger.info(f"Entry Net Premium: Rs.{net_premium:.2f}")
            logger.info(f"{'='*60}\n")

            return trade_data

        except Exception as e:
            logger.error(f"Error executing spread order: {e}", exc_info=True)
            return None

    def close_position(self, trade: Dict) -> bool:
        """
        Close an open position

        Args:
            trade: Trade dictionary

        Returns:
            True if successful
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"CLOSING POSITION: {trade['trade_id']}")
            logger.info(f"{'='*60}")

            symbol = trade["instrument"]

            # Use the stored expiry from the trade
            expiry = trade.get("expiry")
            if expiry is None:
                logger.error("Trade does not have expiry information")
                return False

            # Ensure expiry is a datetime object
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry)

            # Get trading symbols
            sell_symbol, buy_symbol = self.option_chain.get_trading_symbols(
                symbol=symbol,
                expiry=expiry,
                sell_strike=trade["sell_strike"],
                buy_strike=trade["buy_strike"],
                option_type=trade["option_type"],
            )

            if not sell_symbol or not buy_symbol:
                logger.error("Failed to get trading symbols for exit")
                return False

            # Get current premiums
            exit_sell_premium = self.option_chain.get_option_premium(
                symbol, expiry, trade["sell_strike"], trade["option_type"]
            )
            exit_buy_premium = self.option_chain.get_option_premium(
                symbol, expiry, trade["buy_strike"], trade["option_type"]
            )

            if not exit_sell_premium or not exit_buy_premium:
                logger.error("Failed to fetch exit premiums")
                return False

            exit_net_premium = exit_sell_premium - exit_buy_premium

            # To close spread: Buy back sold option first, then Sell bought option
            # BUY BACK the sold leg FIRST (cover short position to reduce risk)
            logger.info(f"Placing BUY order first to cover short: {sell_symbol} @ {exit_sell_premium}")
            buy_back_order_id = self.broker.place_order(
                trading_symbol=sell_symbol,
                transaction_type=TRANSACTION_TYPE_BUY,
                quantity=trade["quantity"],
                order_type=ORDER_TYPE_LIMIT,
                price=exit_sell_premium,
            )

            if not buy_back_order_id:
                logger.error("BUY order failed, not placing SELL order")
                return False

            # Wait for BUY order to execute before placing SELL
            # This ensures margin benefit - BUY must complete first
            logger.info(f"Waiting for BUY order {buy_back_order_id} to execute...")
            max_wait_time = 30  # Maximum wait time in seconds
            wait_interval = 1  # Check every 1 second
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                buy_status = self.broker.get_order_status(buy_back_order_id)
                if buy_status and buy_status.get("status") == ORDER_STATUS_COMPLETE:
                    logger.info(f"BUY order {buy_back_order_id} executed successfully")
                    break
                elif buy_status and buy_status.get("status") in ["REJECTED", "CANCELLED"]:
                    logger.error(f"BUY order {buy_back_order_id} was {buy_status.get('status')}: {buy_status.get('status_message', '')}")
                    return False
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            else:
                logger.error(f"BUY order {buy_back_order_id} did not execute within {max_wait_time}s")
                # Cancel the pending buy order
                self.broker.cancel_order(buy_back_order_id)
                return False

            # SELL the bought leg SECOND (close long position)
            logger.info(f"Placing SELL order: {buy_symbol} @ {exit_buy_premium}")
            sell_back_order_id = self.broker.place_order(
                trading_symbol=buy_symbol,
                transaction_type=TRANSACTION_TYPE_SELL,
                quantity=trade["quantity"],
                order_type=ORDER_TYPE_LIMIT,
                price=exit_buy_premium,
            )

            if not sell_back_order_id:
                logger.error("Failed to place SELL exit order")
                return False

            # Calculate P&L
            # Entry: Received net_premium
            # Exit: Pay exit_net_premium
            # P&L = (Entry Premium - Exit Premium) × Quantity
            pnl_per_lot = (trade["net_premium"] - exit_net_premium) * trade["lot_size"]
            gross_pnl = pnl_per_lot * (trade["quantity"] / trade["lot_size"])

            # Estimate commission (₹20 per order × 4 orders)
            commission = 80
            net_pnl = gross_pnl - commission

            margin_used = trade.get("margin_used", 0)
            pnl_percent = (net_pnl / margin_used) * 100 if margin_used > 0 else 0

            is_winning = net_pnl > 0

            # Update trade in database
            update_data = {
                "exit_time": datetime.now(IST),
                "exit_sell_premium": exit_sell_premium,
                "exit_buy_premium": exit_buy_premium,
                "exit_net_premium": exit_net_premium,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "commission": commission,
                "pnl_percent": pnl_percent,
                "status": "CLOSED",
                "is_winning_trade": is_winning,
            }

            self.db.update_trade(trade["trade_id"], update_data)

            logger.info(f"Position closed successfully")
            logger.info(f"Entry Premium: Rs.{trade['net_premium']:.2f}")
            logger.info(f"Exit Premium: Rs.{exit_net_premium:.2f}")
            logger.info(f"Gross P&L: Rs.{gross_pnl:.2f}")
            logger.info(f"Net P&L: Rs.{net_pnl:.2f} ({pnl_percent:.2f}%)")
            logger.info(f"Result: {'[WIN]' if is_winning else '[LOSS]'}")
            logger.info(f"{'='*60}\n")

            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            return False

    def get_open_positions(self) -> list:
        """Get all open positions"""
        try:
            return self.db.get_open_trades()
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return []

    def cancel_pending_orders(self, trade_id: str) -> bool:
        """Cancel pending orders for a trade"""
        try:
            trade = self.db.get_trade(trade_id)
            if not trade:
                return False

            # Cancel sell and buy orders
            if trade.sell_order_id:
                self.broker.cancel_order(trade.sell_order_id)

            if trade.buy_order_id:
                self.broker.cancel_order(trade.buy_order_id)

            return True

        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            return False
