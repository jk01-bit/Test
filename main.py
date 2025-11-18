"""
Main Trading Bot
Orchestrates the entire trading system
"""
import logging
import time
from datetime import datetime, time as dt_time
from typing import Optional
import pytz
import signal
import sys

from src.brokers.zerodha_broker import ZerodhaBroker
from src.data.market_data import MarketDataHandler
from src.data.indicators import IndicatorEngine
from src.data.option_chain import OptionChainHandler
from src.strategy.filters import EntryFilters
from src.strategy.signal_generator import SignalGenerator
from src.execution.order_manager import OrderManager
from src.execution.exit_manager import ExitManager
from src.risk.risk_manager import RiskManager
from src.database.db_manager import DatabaseManager
from src.utils.logger import setup_logger
from src.utils.notifications import NotificationManager

from config.settings import (
    TRADING_INSTRUMENTS,
    POSITION_CHECK_INTERVAL,
    DRY_RUN_MODE,
)
from config.credentials import Credentials

IST = pytz.timezone("Asia/Kolkata")


class TradingBot:
    """Main trading bot orchestrator"""

    def __init__(self):
        """Initialize trading bot"""
        # Setup logging
        self.logger = setup_logger("TradingBot")
        self.logger.info("="*60)
        self.logger.info("INITIALIZING TRADING BOT")
        self.logger.info("="*60)

        # Validate credentials
        try:
            Credentials.validate()
            self.logger.info("✓ Credentials validated")
        except ValueError as e:
            self.logger.error(f"Credential validation failed: {e}")
            sys.exit(1)

        # Initialize components
        self.logger.info("Initializing components...")

        # Database
        self.db = DatabaseManager()
        self.logger.info("✓ Database initialized")

        # Broker
        self.broker = ZerodhaBroker()
        self.logger.info("✓ Broker initialized")

        # Market data
        self.market_data = MarketDataHandler(self.broker, self.db)
        self.logger.info("✓ Market data handler initialized")

        # Indicators
        self.indicators = IndicatorEngine()
        self.logger.info("✓ Indicator engine initialized")

        # Option chain
        self.option_chain = OptionChainHandler(self.broker)
        self.logger.info("✓ Option chain handler initialized")

        # Filters
        self.filters = EntryFilters(self.db)
        self.logger.info("✓ Entry filters initialized")

        # Signal generator
        self.signal_generator = SignalGenerator(
            self.market_data,
            self.indicators,
            self.option_chain,
            self.filters,
            self.db,
        )
        self.logger.info("✓ Signal generator initialized")

        # Order manager
        self.order_manager = OrderManager(
            self.broker, self.option_chain, self.db
        )
        self.logger.info("✓ Order manager initialized")

        # Exit manager
        self.exit_manager = ExitManager(
            self.order_manager, self.option_chain, self.db
        )
        self.logger.info("✓ Exit manager initialized")

        # Risk manager
        self.risk_manager = RiskManager(self.db, self.option_chain)
        self.logger.info("✓ Risk manager initialized")

        # Notifications
        self.notifier = NotificationManager()
        self.logger.info("✓ Notification manager initialized")

        # State
        self.is_running = False
        self.is_connected = False
        self.signals_checked_today = False

        self.logger.info("="*60)
        self.logger.info("INITIALIZATION COMPLETE")
        self.logger.info("="*60 + "\n")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.warning("\nShutdown signal received")
        self.stop()

    def connect_broker(self, request_token: Optional[str] = None) -> bool:
        """
        Connect to broker

        Args:
            request_token: Zerodha request token (if manual login)

        Returns:
            True if connected
        """
        try:
            self.logger.info("Connecting to broker...")

            if DRY_RUN_MODE:
                self.logger.warning("DRY RUN MODE - Not connecting to broker")
                self.is_connected = True
                return True

            success = self.broker.connect(request_token)

            if success:
                self.is_connected = True
                self.logger.info("✅ Connected to broker successfully")
                return True
            else:
                self.logger.error("❌ Failed to connect to broker")
                return False

        except Exception as e:
            self.logger.error(f"Error connecting to broker: {e}")
            return False

    def check_and_generate_signals(self):
        """Check for entry signals"""
        try:
            self.logger.info("\n" + "="*60)
            self.logger.info("CHECKING FOR ENTRY SIGNALS")
            self.logger.info("="*60)

            # Check if we should stop trading
            should_stop, reason = self.risk_manager.should_stop_trading()
            if should_stop:
                self.logger.warning(f"Trading stopped: {reason}")
                return

            # Check for signals across all instruments
            signals = self.signal_generator.check_for_signals(TRADING_INSTRUMENTS)

            # Process valid signals
            for instrument, signal in signals.items():
                if signal and signal["filters_passed"]:
                    self.logger.info(f"✅ Valid signal for {instrument}")

                    # Check if we can take position
                    can_take, reason = self.risk_manager.can_take_new_position(
                        signal["required_margin"]
                    )

                    if not can_take:
                        self.logger.warning(f"Cannot take position: {reason}")
                        continue

                    # Execute trade (if not dry run)
                    if DRY_RUN_MODE:
                        self.logger.info("DRY RUN: Would execute trade here")
                    else:
                        self.execute_trade(signal)

            self.signals_checked_today = True
            self.logger.info("="*60 + "\n")

        except Exception as e:
            self.logger.error(f"Error checking signals: {e}", exc_info=True)

    def execute_trade(self, signal: dict):
        """
        Execute a trade based on signal

        Args:
            signal: Signal dictionary
        """
        try:
            self.logger.info(f"Executing trade for {signal['instrument']}...")

            # Execute spread order
            trade = self.order_manager.execute_spread_order(signal)

            if trade:
                self.logger.info(f"✅ Trade executed successfully: {trade['trade_id']}")

                # Send notification
                self.notifier.notify_trade_entry(trade)

                # Update signal as executed
                self.db.update_signal(
                    signal["signal_id"],
                    {"was_executed": True, "trade_id": trade["trade_id"]},
                )
            else:
                self.logger.error("❌ Failed to execute trade")

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}", exc_info=True)
            self.notifier.notify_error(f"Trade execution error: {e}")

    def monitor_and_exit_positions(self):
        """Monitor open positions and exit if needed"""
        try:
            # Check circuit breaker
            triggered, reason = self.risk_manager.check_circuit_breaker()
            if triggered:
                self.logger.error(f"⛔ CIRCUIT BREAKER TRIGGERED: {reason}")
                self.exit_manager.force_exit_all_positions(reason)
                self.notifier.notify_error(f"Circuit breaker: {reason}")
                self.stop()
                return

            # Monitor positions
            closed_trades = self.exit_manager.monitor_positions()

            # Send notifications for closed trades
            for trade in closed_trades:
                trade_record = self.db.get_trade(trade["trade_id"])
                if trade_record:
                    self.notifier.notify_trade_exit(
                        trade, trade_record.exit_reason, trade_record.net_pnl
                    )

                    # Special notification for stop loss
                    if trade_record.exit_reason == "STOP_LOSS":
                        self.notifier.notify_stop_loss_hit(
                            trade, trade_record.net_pnl
                        )

        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}", exc_info=True)

    def should_check_for_signals(self) -> bool:
        """
        Check if we should look for entry signals

        Returns:
            True if we should check for signals
        """
        # Check if already checked today
        if self.signals_checked_today:
            return False

        # Check if market is open
        if not self.market_data.is_market_open():
            return False

        # Check time window (9:35 AM - 10:30 AM)
        now = datetime.now(IST).time()
        from config.settings import ENTRY_START_TIME, ENTRY_END_TIME

        if ENTRY_START_TIME <= now <= ENTRY_END_TIME:
            return True

        return False

    def run(self):
        """Main trading loop"""
        try:
            self.is_running = True
            self.logger.info("🚀 TRADING BOT STARTED")
            self.notifier.notify_system_start()

            iteration = 0

            while self.is_running:
                iteration += 1
                current_time = datetime.now(IST)

                self.logger.debug(f"Iteration {iteration} - {current_time.strftime('%H:%M:%S')}")

                # Check if market is open
                if not self.market_data.is_market_open():
                    self.logger.info("Market is closed. Waiting...")
                    time.sleep(300)  # Check every 5 minutes
                    continue

                # Check for entry signals (during entry window)
                if self.should_check_for_signals():
                    self.check_and_generate_signals()

                # Monitor and exit positions (always during market hours)
                self.monitor_and_exit_positions()

                # Check if it's end of day
                if current_time.time() >= dt_time(15, 20):
                    self.logger.info("End of trading day. Shutting down...")
                    self.generate_daily_report()
                    self.stop()
                    break

                # Sleep before next iteration
                time.sleep(POSITION_CHECK_INTERVAL)

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
            self.notifier.notify_error(f"Critical error: {e}")
            self.stop()

    def generate_daily_report(self):
        """Generate and send daily report"""
        try:
            from datetime import date

            today = date.today()
            stats = self.db.get_performance_stats(today, today)

            if stats:
                report = {
                    "date": today.strftime("%Y-%m-%d"),
                    "total_trades": stats.get("total_trades", 0),
                    "winning_trades": stats.get("winning_trades", 0),
                    "losing_trades": stats.get("losing_trades", 0),
                    "win_rate": stats.get("win_rate", 0),
                    "net_pnl": stats.get("total_pnl", 0),
                    "largest_win": stats.get("largest_win", 0),
                    "largest_loss": stats.get("largest_loss", 0),
                    "return_percent": (stats.get("total_pnl", 0) / (TOTAL_CAPITAL * 0.4)) * 100,
                }

                self.notifier.notify_daily_report(report)
                self.logger.info("Daily report sent")

        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")

    def stop(self):
        """Stop the trading bot"""
        self.logger.info("Stopping trading bot...")
        self.is_running = False

        # Force exit any open positions
        open_trades = self.db.get_open_trades()
        if open_trades:
            self.logger.warning(f"Force exiting {len(open_trades)} open position(s)")
            self.exit_manager.force_exit_all_positions("SYSTEM_SHUTDOWN")

        self.notifier.notify_system_stop()
        self.logger.info("✅ Trading bot stopped")


def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         OPTIONS TRADING AUTOMATION SYSTEM                 ║
    ║         Trend Following + Option Selling Strategy         ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Initialize bot
    bot = TradingBot()

    # Get login URL for manual connection
    if not DRY_RUN_MODE:
        login_url = bot.broker.get_login_url()
        print(f"\n🔗 Login URL: {login_url}")
        print("\nPlease login and paste the request token from the redirect URL:")
        request_token = input("Request Token: ").strip()

        # Connect to broker
        if not bot.connect_broker(request_token):
            print("❌ Failed to connect to broker. Exiting...")
            sys.exit(1)
    else:
        print("\n⚠️  DRY RUN MODE - No real trades will be placed")
        bot.connect_broker()

    print("\n✅ Bot initialized successfully!")
    print("\nStarting trading bot...\n")

    # Run bot
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        bot.stop()
    except Exception as e:
        print(f"\n\n❌ Critical error: {e}")
        bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
