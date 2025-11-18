"""
Backtesting Engine
Test the strategy on historical data
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np

from src.data.indicators import IndicatorEngine
from config.settings import (
    BACKTEST_START_DATE,
    BACKTEST_CAPITAL,
    POSITION_SIZE,
    MAX_DAILY_LOSS,
)
from config.constants import TREND_UPTREND, TREND_DOWNTREND

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest trading strategy on historical data"""

    def __init__(self):
        """Initialize backtest engine"""
        self.indicators = IndicatorEngine()
        self.capital = BACKTEST_CAPITAL
        self.trades = []
        self.daily_pnl = {}

    def load_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load historical data for backtesting

        Args:
            symbol: NIFTY or BANKNIFTY
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with historical data
        """
        # TODO: Implement data loading from CSV or database
        # For now, returning empty DataFrame
        # In production, you'd load from:
        # 1. Saved CSV files
        # 2. Database
        # 3. API (if available)

        logger.warning("Historical data loading not implemented yet")
        return pd.DataFrame()

    def simulate_option_pricing(
        self,
        spot_price: float,
        strike: float,
        option_type: str,
        days_to_expiry: int,
    ) -> float:
        """
        Simulate option pricing (simplified)

        Args:
            spot_price: Current spot price
            strike: Strike price
            option_type: CE or PE
            days_to_expiry: Days until expiry

        Returns:
            Estimated option premium
        """
        # Simplified option pricing model
        # In production, use Black-Scholes or historical option data

        if option_type == "PE":
            # Put option
            if spot_price > strike:
                # OTM Put
                distance = spot_price - strike
                premium = max(1, (distance / spot_price) * 100 * (days_to_expiry / 30))
            else:
                # ITM Put
                intrinsic = strike - spot_price
                premium = intrinsic + (intrinsic * 0.1)
        else:
            # Call option
            if spot_price < strike:
                # OTM Call
                distance = strike - spot_price
                premium = max(1, (distance / spot_price) * 100 * (days_to_expiry / 30))
            else:
                # ITM Call
                intrinsic = spot_price - strike
                premium = intrinsic + (intrinsic * 0.1)

        return premium

    def backtest(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """
        Run backtest

        Args:
            symbol: Instrument to backtest
            start_date: Start date
            end_date: End date

        Returns:
            Backtest results
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")

        # Load data
        df = self.load_historical_data(symbol, start_date, end_date)

        if df.empty:
            logger.error("No data available for backtesting")
            return {}

        # Calculate indicators
        df = self.indicators.calculate_all_indicators(df)

        # Initialize tracking
        current_position = None
        entry_date = None

        # Iterate through data
        for idx in range(50, len(df)):  # Start after enough data for EMAs
            current_row = df.iloc[idx]
            current_date = current_row["date"]

            # Get trend
            trend_info = self.indicators.get_latest_trend(df.iloc[:idx+1])
            trend = trend_info["trend"]
            spot_price = current_row["close"]

            # Check for entry (if no position)
            if current_position is None and trend in [TREND_UPTREND, TREND_DOWNTREND]:
                # Simulate entry
                if self._check_entry_time(current_date):
                    current_position = self._simulate_entry(
                        symbol, spot_price, trend, current_date
                    )
                    entry_date = current_date

            # Check for exit (if position exists)
            elif current_position is not None:
                should_exit, exit_pnl = self._check_exit_conditions(
                    current_position, spot_price, current_date, entry_date
                )

                if should_exit:
                    # Record trade
                    self.trades.append({
                        "symbol": symbol,
                        "entry_date": entry_date,
                        "exit_date": current_date,
                        "entry_price": current_position["entry_price"],
                        "exit_price": spot_price,
                        "pnl": exit_pnl,
                        "trend": current_position["trend"],
                    })

                    # Update daily P&L
                    date_key = current_date.date()
                    self.daily_pnl[date_key] = self.daily_pnl.get(date_key, 0) + exit_pnl

                    # Reset position
                    current_position = None
                    entry_date = None

        # Calculate results
        results = self._calculate_results()

        return results

    def _check_entry_time(self, timestamp: datetime) -> bool:
        """Check if timestamp is within entry window"""
        time = timestamp.time()
        from config.settings import ENTRY_START_TIME, ENTRY_END_TIME
        return ENTRY_START_TIME <= time <= ENTRY_END_TIME

    def _simulate_entry(self, symbol: str, spot_price: float, trend: str, date: datetime) -> Dict:
        """Simulate trade entry"""
        from config.settings import ATM_OFFSET_MIN, SPREAD_WIDTH

        if trend == TREND_UPTREND:
            # Bull Put Spread
            option_type = "PE"
            sell_strike = spot_price - ATM_OFFSET_MIN
            buy_strike = sell_strike - SPREAD_WIDTH
        else:
            # Bear Call Spread
            option_type = "CE"
            sell_strike = spot_price + ATM_OFFSET_MIN
            buy_strike = sell_strike + SPREAD_WIDTH

        # Simulate premiums (7 days to expiry assumed)
        sell_premium = self.simulate_option_pricing(spot_price, sell_strike, option_type, 7)
        buy_premium = self.simulate_option_pricing(spot_price, buy_strike, option_type, 7)
        net_premium = sell_premium - buy_premium

        return {
            "symbol": symbol,
            "trend": trend,
            "entry_price": spot_price,
            "sell_strike": sell_strike,
            "buy_strike": buy_strike,
            "option_type": option_type,
            "entry_premium": net_premium,
            "stop_loss": net_premium * 1.5,
            "target": net_premium * 0.55,
        }

    def _check_exit_conditions(
        self, position: Dict, current_price: float, current_date: datetime, entry_date: datetime
    ) -> tuple:
        """Check if exit conditions are met"""
        # Simulate current premium
        days_held = (current_date - entry_date).days

        current_sell_premium = self.simulate_option_pricing(
            current_price,
            position["sell_strike"],
            position["option_type"],
            max(1, 7 - days_held),
        )

        # Calculate P&L
        pnl = (position["entry_premium"] - current_sell_premium) * POSITION_SIZE.get(position["symbol"], 2) * 25

        # Check profit target
        if current_sell_premium <= position["target"]:
            return True, pnl

        # Check stop loss
        if current_sell_premium >= position["stop_loss"]:
            return True, pnl

        # Check time exit (assume exit after 1 day)
        if days_held >= 1:
            return True, pnl

        return False, 0

    def _calculate_results(self) -> Dict:
        """Calculate backtest statistics"""
        if not self.trades:
            return {"error": "No trades executed"}

        pnls = [t["pnl"] for t in self.trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        total_trades = len(self.trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        results = {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": (win_count / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": sum(pnls),
            "avg_win": np.mean(winning_trades) if winning_trades else 0,
            "avg_loss": np.mean(losing_trades) if losing_trades else 0,
            "largest_win": max(pnls) if pnls else 0,
            "largest_loss": min(pnls) if pnls else 0,
            "sharpe_ratio": self._calculate_sharpe_ratio(pnls),
            "max_drawdown": self._calculate_max_drawdown(),
        }

        return results

    def _calculate_sharpe_ratio(self, pnls: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not pnls or len(pnls) < 2:
            return 0

        returns = np.array(pnls) / self.capital
        return np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if not self.daily_pnl:
            return 0

        cumulative = 0
        peak = 0
        max_dd = 0

        for pnl in self.daily_pnl.values():
            cumulative += pnl
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            max_dd = max(max_dd, drawdown)

        return max_dd

    def print_results(self, results: Dict):
        """Print backtest results"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Total Trades: {results.get('total_trades', 0)}")
        print(f"Winning Trades: {results.get('winning_trades', 0)}")
        print(f"Losing Trades: {results.get('losing_trades', 0)}")
        print(f"Win Rate: {results.get('win_rate', 0):.2f}%")
        print(f"\nTotal P&L: ₹{results.get('total_pnl', 0):.2f}")
        print(f"Average Win: ₹{results.get('avg_win', 0):.2f}")
        print(f"Average Loss: ₹{results.get('avg_loss', 0):.2f}")
        print(f"Largest Win: ₹{results.get('largest_win', 0):.2f}")
        print(f"Largest Loss: ₹{results.get('largest_loss', 0):.2f}")
        print(f"\nSharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        print(f"Max Drawdown: ₹{results.get('max_drawdown', 0):.2f}")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Example usage
    engine = BacktestEngine()
    results = engine.backtest("NIFTY", "2023-01-01", "2023-12-31")
    engine.print_results(results)
