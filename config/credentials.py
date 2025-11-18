"""
Credentials Management
Loads credentials from environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Credentials:
    """Manage API credentials and secrets"""

    # Zerodha API
    ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY")
    ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET")
    ZERODHA_USER_ID = os.getenv("ZERODHA_USER_ID")
    ZERODHA_PASSWORD = os.getenv("ZERODHA_PASSWORD")
    ZERODHA_TOTP_SECRET = os.getenv("ZERODHA_TOTP_SECRET")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Email
    EMAIL_FROM = os.getenv("EMAIL_FROM")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_TO = os.getenv("EMAIL_TO")

    # Trading Mode
    TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # paper or live

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/trading.db")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate that all required credentials are present"""
        required = [
            ("ZERODHA_API_KEY", cls.ZERODHA_API_KEY),
            ("ZERODHA_API_SECRET", cls.ZERODHA_API_SECRET),
            ("ZERODHA_USER_ID", cls.ZERODHA_USER_ID),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(
                f"Missing required credentials: {', '.join(missing)}. "
                "Please check your .env file."
            )

        return True

    @classmethod
    def is_live_trading(cls):
        """Check if we're in live trading mode"""
        return cls.TRADING_MODE.lower() == "live"

    @classmethod
    def is_paper_trading(cls):
        """Check if we're in paper trading mode"""
        return cls.TRADING_MODE.lower() == "paper"
