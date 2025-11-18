"""
Notification System
Send notifications via Telegram and Email
"""
import logging
from typing import Optional
from datetime import datetime
import asyncio

try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

from config.credentials import Credentials
from config.settings import ENABLE_TELEGRAM, ENABLE_EMAIL

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manage notifications"""

    def __init__(self):
        """Initialize notification manager"""
        self.telegram_enabled = ENABLE_TELEGRAM and TELEGRAM_AVAILABLE
        self.email_enabled = ENABLE_EMAIL

        # Initialize Telegram bot
        self.telegram_bot = None
        if self.telegram_enabled and Credentials.TELEGRAM_BOT_TOKEN:
            try:
                self.telegram_bot = Bot(token=Credentials.TELEGRAM_BOT_TOKEN)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.telegram_enabled = False

    async def _send_telegram_async(self, message: str):
        """Send Telegram message asynchronously"""
        try:
            if self.telegram_bot and Credentials.TELEGRAM_CHAT_ID:
                await self.telegram_bot.send_message(
                    chat_id=Credentials.TELEGRAM_CHAT_ID, text=message, parse_mode="HTML"
                )
                logger.debug("Telegram notification sent")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    def send_telegram(self, message: str):
        """
        Send Telegram notification (sync wrapper)

        Args:
            message: Message to send
        """
        if not self.telegram_enabled:
            return

        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_telegram_async(message))
            loop.close()
        except Exception as e:
            logger.error(f"Error in Telegram notification: {e}")

    def send_email(self, subject: str, body: str):
        """
        Send email notification

        Args:
            subject: Email subject
            body: Email body
        """
        if not self.email_enabled:
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = Credentials.EMAIL_FROM
            msg["To"] = Credentials.EMAIL_TO
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            # Send via Gmail SMTP
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(Credentials.EMAIL_FROM, Credentials.EMAIL_PASSWORD)
                server.send_message(msg)

            logger.debug("Email notification sent")

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")

    def notify_trade_entry(self, trade: dict):
        """Notify trade entry"""
        message = (
            f"<b>TRADE ENTERED</b>\n\n"
            f"ID: {trade['trade_id']}\n"
            f"Instrument: {trade['instrument']}\n"
            f"Type: {trade['spread_type']}\n"
            f"Strikes: {trade['sell_strike']} / {trade['buy_strike']} {trade['option_type']}\n"
            f"Premium: ₹{trade['net_premium']:.2f}\n"
            f"Quantity: {trade['quantity']}\n"
            f"Spot: {trade['entry_spot_price']:.2f}\n"
            f"Trend: {trade['trend']}\n"
            f"Stop Loss: ₹{trade.get('stop_loss_value', 0):.2f}"
        )

        self.send_telegram(message)

    def notify_trade_exit(self, trade: dict, exit_reason: str, pnl: float):
        """Notify trade exit"""
        emoji = "[WIN]" if pnl > 0 else "[LOSS]"

        message = (
            f"<b>{emoji} TRADE EXITED</b>\n\n"
            f"ID: {trade['trade_id']}\n"
            f"Reason: {exit_reason}\n"
            f"P&L: ₹{pnl:.2f}\n"
            f"Entry Premium: ₹{trade['net_premium']:.2f}\n"
            f"Duration: {(datetime.now() - trade['entry_time']).seconds // 60} min"
        )

        self.send_telegram(message)

    def notify_stop_loss_hit(self, trade: dict, pnl: float):
        """Notify stop loss hit"""
        message = (
            f"<b>STOP LOSS HIT</b>\n\n"
            f"ID: {trade['trade_id']}\n"
            f"Instrument: {trade['instrument']}\n"
            f"Loss: ₹{pnl:.2f}\n"
            f"Please review strategy!"
        )

        self.send_telegram(message)
        self.send_email("[WARNING] Stop Loss Hit", message.replace("<b>", "").replace("</b>", ""))

    def notify_daily_loss_limit(self, daily_pnl: float, limit: float):
        """Notify daily loss limit reached"""
        message = (
            f"<b>DAILY LOSS LIMIT REACHED</b>\n\n"
            f"Daily P&L: ₹{daily_pnl:.2f}\n"
            f"Limit: ₹{limit:.2f}\n"
            f"Trading stopped for today."
        )

        self.send_telegram(message)
        self.send_email("[ALERT] Daily Loss Limit Reached", message.replace("<b>", "").replace("</b>", ""))

    def notify_error(self, error_msg: str):
        """Notify error"""
        message = f"<b>[ERROR]</b>\n\n{error_msg}"
        self.send_telegram(message)

    def notify_daily_report(self, report: dict):
        """Send daily performance report"""
        message = (
            f"<b>DAILY REPORT</b>\n"
            f"{'='*30}\n"
            f"Date: {report.get('date', 'N/A')}\n\n"
            f"<b>Trades:</b>\n"
            f"Total: {report.get('total_trades', 0)}\n"
            f"Winners: {report.get('winning_trades', 0)}\n"
            f"Losers: {report.get('losing_trades', 0)}\n"
            f"Win Rate: {report.get('win_rate', 0):.1f}%\n\n"
            f"<b>P&L:</b>\n"
            f"Net P&L: ₹{report.get('net_pnl', 0):.2f}\n"
            f"Largest Win: ₹{report.get('largest_win', 0):.2f}\n"
            f"Largest Loss: ₹{report.get('largest_loss', 0):.2f}\n\n"
            f"<b>Capital:</b>\n"
            f"Return: {report.get('return_percent', 0):.2f}%"
        )

        self.send_telegram(message)
        self.send_email(
            f"Daily Trading Report - {report.get('date', 'N/A')}",
            message.replace("<b>", "").replace("</b>", "").replace("='*30}", ""),
        )

    def notify_system_start(self):
        """Notify system start"""
        message = (
            f"<b>TRADING BOT STARTED</b>\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Mode: {Credentials.TRADING_MODE.upper()}"
        )
        self.send_telegram(message)

    def notify_system_stop(self):
        """Notify system stop"""
        message = (
            f"<b>TRADING BOT STOPPED</b>\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_telegram(message)
