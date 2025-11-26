"""
Zerodha Broker Integration
Handles all Zerodha Kite API interactions
"""
import logging
import os
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from kiteconnect import KiteConnect
import pytz

from config.credentials import Credentials
from config.constants import (
    OPTION_TYPE_CE,
    OPTION_TYPE_PE,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_SELL,
    ORDER_STATUS_COMPLETE,
)
from config.settings import PRODUCT_TYPE, EXCHANGE, ORDER_TYPE_LIMIT

logger = logging.getLogger(__name__)

# Token cache file path
TOKEN_CACHE_FILE = Path("data/.token_cache.json")


class ZerodhaBroker:
    """Zerodha broker interface"""

    def __init__(self):
        """Initialize Zerodha connection"""
        self.kite = None
        self.access_token = None
        self.is_connected = False
        self._token_expiry = None

    def connect(self, request_token: Optional[str] = None) -> bool:
        """
        Connect to Zerodha Kite API

        Args:
            request_token: Request token from login (optional for automated login)

        Returns:
            bool: True if connection successful
        """
        try:
            self.kite = KiteConnect(api_key=Credentials.ZERODHA_API_KEY)

            if request_token:
                # Generate session using request token
                data = self.kite.generate_session(
                    request_token, api_secret=Credentials.ZERODHA_API_SECRET
                )
                self.access_token = data["access_token"]

                # Cache the token for future use
                self._save_token_cache(self.access_token)
            else:
                # For automated trading, you'd implement TOTP-based login here
                # This is a simplified version
                logger.warning(
                    "No request token provided. Manual login required."
                )
                return False

            self.kite.set_access_token(self.access_token)
            self.is_connected = True

            logger.info("Successfully connected to Zerodha Kite")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Zerodha: {e}")
            self.is_connected = False
            return False

    def auto_login(self, headless: bool = True) -> bool:
        """
        Perform automated login using stored credentials

        Args:
            headless: Run browser in headless mode (default: True)

        Returns:
            bool: True if login successful
        """
        try:
            # First, try to use cached token
            if self._try_cached_token():
                logger.info("Connected using cached token")
                return True

            # Check if auto-login credentials are configured
            if not Credentials.is_auto_login_configured():
                logger.warning("Auto-login credentials not configured")
                return False

            logger.info("Starting automated login process...")

            # Import here to avoid dependency issues
            from src.brokers.auto_login import perform_auto_login

            # Get login URL
            login_url = self.get_login_url()
            logger.info(f"Login URL: {login_url}")

            # Perform automated login
            success, request_token, error = perform_auto_login(
                login_url, headless=headless
            )

            if success and request_token:
                logger.info("Auto-login successful, connecting with request token...")
                return self.connect(request_token)
            else:
                logger.error(f"Auto-login failed: {error}")
                return False

        except Exception as e:
            logger.error(f"Auto-login error: {e}", exc_info=True)
            return False

    def _try_cached_token(self) -> bool:
        """
        Try to connect using a cached token

        Returns:
            bool: True if cached token is valid
        """
        try:
            cached_token = self._load_token_cache()
            if not cached_token:
                logger.debug("No cached token found")
                return False

            # Check if token is from today (Zerodha tokens expire at 6 AM next day)
            cache_date = cached_token.get("date")
            today = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")

            if cache_date != today:
                logger.info("Cached token is from a different day, requires fresh login")
                self._clear_token_cache()
                return False

            # Try to use the cached token
            self.kite = KiteConnect(api_key=Credentials.ZERODHA_API_KEY)
            self.access_token = cached_token.get("access_token")
            self.kite.set_access_token(self.access_token)

            # Validate the token by making a simple API call
            if self.validate_token():
                self.is_connected = True
                return True
            else:
                logger.info("Cached token is invalid")
                self._clear_token_cache()
                return False

        except Exception as e:
            logger.warning(f"Error using cached token: {e}")
            self._clear_token_cache()
            return False

    def validate_token(self) -> bool:
        """
        Validate the current access token

        Returns:
            bool: True if token is valid
        """
        try:
            if not self.kite or not self.access_token:
                return False

            # Make a simple API call to validate token
            profile = self.kite.profile()

            if profile and profile.get("user_id") == Credentials.ZERODHA_USER_ID:
                logger.info(f"Token validated for user: {profile.get('user_name')}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False

    def _save_token_cache(self, access_token: str):
        """Save access token to cache file"""
        try:
            # Ensure data directory exists
            TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "access_token": access_token,
                "date": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d"),
                "timestamp": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
            }

            with open(TOKEN_CACHE_FILE, "w") as f:
                json.dump(cache_data, f)

            logger.debug("Token cached successfully")

        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")

    def _load_token_cache(self) -> Optional[dict]:
        """Load access token from cache file"""
        try:
            if not TOKEN_CACHE_FILE.exists():
                return None

            with open(TOKEN_CACHE_FILE, "r") as f:
                return json.load(f)

        except Exception as e:
            logger.warning(f"Failed to load token cache: {e}")
            return None

    def _clear_token_cache(self):
        """Clear the token cache file"""
        try:
            if TOKEN_CACHE_FILE.exists():
                TOKEN_CACHE_FILE.unlink()
                logger.debug("Token cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear token cache: {e}")

    def get_login_url(self) -> str:
        """Get Zerodha login URL"""
        if not self.kite:
            self.kite = KiteConnect(api_key=Credentials.ZERODHA_API_KEY)
        return self.kite.login_url()

    # ========================================================================
    # MARKET DATA METHODS
    # ========================================================================

    def get_ltp(self, trading_symbol: str) -> Optional[float]:
        """
        Get Last Traded Price

        Args:
            trading_symbol: e.g., "NSE:NIFTY 50" or "NFO:NIFTY24123456000CE"

        Returns:
            float: Last traded price
        """
        try:
            data = self.kite.ltp([trading_symbol])
            return data[trading_symbol]["last_price"]
        except Exception as e:
            logger.error(f"Error fetching LTP for {trading_symbol}: {e}")
            return None

    def get_quote(self, trading_symbol: str) -> Optional[Dict]:
        """Get full quote for a symbol"""
        try:
            data = self.kite.quote([trading_symbol])
            return data[trading_symbol]
        except Exception as e:
            logger.error(f"Error fetching quote for {trading_symbol}: {e}")
            return None

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: datetime,
        to_date: datetime,
        interval: str = "15minute",
    ) -> pd.DataFrame:
        """
        Fetch historical data

        Args:
            instrument_token: Instrument token
            from_date: Start date
            to_date: End date
            interval: Candle interval (minute, 3minute, 5minute, 15minute, etc.)

        Returns:
            DataFrame with OHLC data
        """
        try:
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
            )
            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def get_instruments(self, exchange: str = "NFO") -> pd.DataFrame:
        """Get all instruments for an exchange"""
        try:
            instruments = self.kite.instruments(exchange)
            return pd.DataFrame(instruments)
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return pd.DataFrame()

    # ========================================================================
    # OPTION CHAIN METHODS
    # ========================================================================

    def get_option_chain(
        self, symbol: str, expiry: datetime
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get option chain for a symbol

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date

        Returns:
            Tuple of (call_chain, put_chain) DataFrames
        """
        try:
            # Get all NFO instruments
            instruments = self.get_instruments("NFO")

            # Filter for the symbol and expiry
            expiry_str = expiry.strftime("%Y-%m-%d")

            options = instruments[
                (instruments["name"] == symbol)
                & (instruments["expiry"].astype(str) == expiry_str)
                & (instruments["instrument_type"].isin(["CE", "PE"]))
            ]

            # Split into calls and puts
            calls = options[options["instrument_type"] == "CE"].copy()
            puts = options[options["instrument_type"] == "PE"].copy()

            # Fetch LTPs for all options (in production, use batch quote)
            # For now, returning the structure
            return calls, puts

        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def get_option_trading_symbol(
        self,
        symbol: str,
        expiry: datetime,
        strike: float,
        option_type: str,
    ) -> Optional[str]:
        """
        Get trading symbol for an option

        Args:
            symbol: NIFTY or BANKNIFTY
            expiry: Expiry date
            strike: Strike price
            option_type: CE or PE

        Returns:
            Trading symbol like "NIFTY24DEC19500CE"
        """
        try:
            instruments = self.get_instruments("NFO")
            expiry_str = expiry.strftime("%Y-%m-%d")

            option = instruments[
                (instruments["name"] == symbol)
                & (instruments["expiry"].astype(str) == expiry_str)
                & (instruments["strike"] == strike)
                & (instruments["instrument_type"] == option_type)
            ]

            if not option.empty:
                return option.iloc[0]["tradingsymbol"]
            return None

        except Exception as e:
            logger.error(f"Error getting option symbol: {e}")
            return None

    def get_atm_strike(self, symbol: str, spot_price: float) -> float:
        """
        Get ATM strike price

        Args:
            symbol: NIFTY or BANKNIFTY
            spot_price: Current spot price

        Returns:
            ATM strike price
        """
        from config.constants import STRIKE_INTERVALS

        interval = STRIKE_INTERVALS.get(symbol, 50)
        atm_strike = round(spot_price / interval) * interval
        return atm_strike

    # ========================================================================
    # ORDER METHODS
    # ========================================================================

    def place_order(
        self,
        trading_symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = ORDER_TYPE_LIMIT,
        price: Optional[float] = None,
        product: str = PRODUCT_TYPE,
        exchange: str = EXCHANGE,
    ) -> Optional[str]:
        """
        Place an order

        Args:
            trading_symbol: Trading symbol
            transaction_type: BUY or SELL
            quantity: Quantity to trade
            order_type: LIMIT or MARKET
            price: Price (required for LIMIT orders)
            product: NRML, MIS, CNC
            exchange: NSE, NFO, etc.

        Returns:
            Order ID if successful
        """
        try:
            order_params = {
                "tradingsymbol": trading_symbol,
                "exchange": exchange,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product,
                "variety": self.kite.VARIETY_REGULAR,
            }

            if order_type == ORDER_TYPE_LIMIT and price:
                order_params["price"] = price

            order_id = self.kite.place_order(**order_params)
            logger.info(
                f"Order placed: {trading_symbol} {transaction_type} "
                f"{quantity} @ {price} - Order ID: {order_id}"
            )
            return order_id

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def place_spread_order(
        self,
        sell_symbol: str,
        sell_price: float,
        buy_symbol: str,
        buy_price: float,
        quantity: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Place both legs of a spread order

        Args:
            sell_symbol: Symbol to sell
            sell_price: Sell price
            buy_symbol: Symbol to buy
            buy_price: Buy price
            quantity: Quantity for both legs

        Returns:
            Tuple of (sell_order_id, buy_order_id)
        """
        try:
            # Place sell order
            sell_order_id = self.place_order(
                trading_symbol=sell_symbol,
                transaction_type=TRANSACTION_TYPE_SELL,
                quantity=quantity,
                order_type=ORDER_TYPE_LIMIT,
                price=sell_price,
            )

            # Place buy order
            buy_order_id = self.place_order(
                trading_symbol=buy_symbol,
                transaction_type=TRANSACTION_TYPE_BUY,
                quantity=quantity,
                order_type=ORDER_TYPE_LIMIT,
                price=buy_price,
            )

            return sell_order_id, buy_order_id

        except Exception as e:
            logger.error(f"Error placing spread order: {e}")
            return None, None

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        try:
            orders = self.kite.orders()
            for order in orders:
                if order["order_id"] == order_id:
                    return order
            return None
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            return None

    def cancel_order(self, order_id: str, variety: str = "regular") -> bool:
        """Cancel an order"""
        try:
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    # ========================================================================
    # POSITION METHODS
    # ========================================================================

    def get_positions(self) -> Dict:
        """Get all positions"""
        try:
            return self.kite.positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {"net": [], "day": []}

    def get_holdings(self) -> List[Dict]:
        """Get holdings"""
        try:
            return self.kite.holdings()
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []

    # ========================================================================
    # ACCOUNT METHODS
    # ========================================================================

    def get_margins(self) -> Dict:
        """Get account margins"""
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Error fetching margins: {e}")
            return {}

    def get_profile(self) -> Dict:
        """Get user profile"""
        try:
            return self.kite.profile()
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return {}
