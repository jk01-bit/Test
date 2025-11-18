"""
Logging Configuration
Set up logging for the trading bot
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, MAX_LOG_SIZE, BACKUP_COUNT


def setup_logger(name: str = "TradingBot") -> logging.Logger:
    """
    Set up logger with console and file handlers

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Ensure logs directory exists
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class TradeLogger:
    """Special logger for trade events"""

    def __init__(self):
        """Initialize trade logger"""
        self.logger = logging.getLogger("TradeLogger")

        # Create separate log file for trades
        trade_log_file = "logs/trades.log"
        os.makedirs(os.path.dirname(trade_log_file), exist_ok=True)

        formatter = logging.Formatter(
            "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        handler = RotatingFileHandler(
            trade_log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_trade_entry(self, trade: dict):
        """Log trade entry"""
        msg = (
            f"ENTRY | {trade['trade_id']} | {trade['instrument']} | "
            f"{trade['spread_type']} | Strikes: {trade['sell_strike']}/{trade['buy_strike']} | "
            f"Premium: ₹{trade['net_premium']:.2f} | Qty: {trade['quantity']} | "
            f"Spot: {trade['entry_spot_price']:.2f}"
        )
        self.logger.info(msg)

    def log_trade_exit(self, trade: dict, exit_data: dict):
        """Log trade exit"""
        msg = (
            f"EXIT | {trade['trade_id']} | Reason: {exit_data.get('exit_reason', 'N/A')} | "
            f"P&L: ₹{exit_data.get('net_pnl', 0):.2f} | "
            f"Duration: {(exit_data.get('exit_time', datetime.now()) - trade['entry_time']).seconds // 60} min"
        )
        self.logger.info(msg)

    def log_signal(self, signal: dict):
        """Log signal generation"""
        msg = (
            f"SIGNAL | {signal['instrument']} | {signal['trend']} | "
            f"Spot: {signal['spot_price']:.2f} | VIX: {signal['india_vix']:.2f} | "
            f"Valid: {signal['filters_passed']}"
        )
        self.logger.info(msg)
