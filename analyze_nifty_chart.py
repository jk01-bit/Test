#!/usr/bin/env python3
"""
NIFTY Live Chart Analysis Script
Fetches live NIFTY data and performs comprehensive technical pattern analysis
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import warnings
warnings.filterwarnings('ignore')

# Import project modules
from src.brokers.zerodha_broker import ZerodhaBroker
from src.data.market_data import MarketDataHandler
from src.data.indicators import IndicatorEngine
from src.database.db_manager import DatabaseManager
from src.utils.logger import setup_logger

logger = setup_logger('chart_analysis')


class ChartAnalyzer:
    """Comprehensive chart analysis with pattern detection"""

    def __init__(self, market_data_handler, indicator_engine):
        self.market_data = market_data_handler
        self.indicators = indicator_engine

    def fetch_data(self, symbol="NIFTY", num_candles=200, interval="15minute"):
        """Fetch historical candle data"""
        logger.info(f"Fetching {num_candles} candles for {symbol} ({interval})")
        df = self.market_data.get_latest_candles(symbol, num_candles, interval)

        if df is None or df.empty:
            logger.error("Failed to fetch candle data")
            return None

        logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        return df

    def calculate_indicators(self, df):
        """Calculate all technical indicators"""
        logger.info("Calculating technical indicators...")

        # Calculate EMAs (from existing engine)
        df = self.indicators.calculate_all_indicators(df)

        # Add RSI
        df = self._calculate_rsi(df, period=14)

        # Add MACD
        df = self._calculate_macd(df)

        # Add Bollinger Bands
        df = self._calculate_bollinger_bands(df, period=20)

        # Add Volume MA
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()

        # Add ATR for volatility
        df = self._calculate_atr(df, period=14)

        return df

    def _calculate_rsi(self, df, period=14):
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def _calculate_macd(self, df, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df

    def _calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        bb_std = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * std_dev)
        df['bb_lower'] = df['bb_middle'] - (bb_std * std_dev)
        return df

    def _calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(period).mean()
        return df

    def detect_support_resistance(self, df, window=10, threshold=0.002):
        """Detect support and resistance levels"""
        logger.info("Detecting support and resistance levels...")

        levels = []

        # Find local peaks (resistance) and troughs (support)
        for i in range(window, len(df) - window):
            # Check for resistance (local high)
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                levels.append({
                    'price': df['high'].iloc[i],
                    'type': 'resistance',
                    'timestamp': df.index[i],
                    'touches': 1
                })

            # Check for support (local low)
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                levels.append({
                    'price': df['low'].iloc[i],
                    'type': 'support',
                    'timestamp': df.index[i],
                    'touches': 1
                })

        # Cluster nearby levels
        clustered_levels = []
        levels_sorted = sorted(levels, key=lambda x: x['price'])

        for level in levels_sorted:
            if not clustered_levels:
                clustered_levels.append(level)
            else:
                # Check if close to existing level
                merged = False
                for existing in clustered_levels:
                    price_diff = abs(level['price'] - existing['price']) / existing['price']
                    if price_diff < threshold:
                        # Merge levels
                        existing['touches'] += 1
                        existing['price'] = (existing['price'] + level['price']) / 2
                        merged = True
                        break

                if not merged:
                    clustered_levels.append(level)

        # Sort by number of touches (strongest levels first)
        clustered_levels = sorted(clustered_levels, key=lambda x: x['touches'], reverse=True)

        return clustered_levels[:10]  # Return top 10 levels

    def detect_patterns(self, df):
        """Detect chart patterns"""
        logger.info("Analyzing chart patterns...")

        patterns = []
        latest = df.iloc[-1]

        # 1. Trend Analysis (EMA-based)
        trend_info = self.indicators.get_latest_trend(df)
        patterns.append({
            'type': 'Trend',
            'pattern': trend_info['trend'],
            'description': f"Price: {trend_info['price']:.2f}, EMA20: {trend_info['ema_20']:.2f}, EMA50: {trend_info['ema_50']:.2f}"
        })

        # 2. RSI Conditions
        if 'rsi' in df.columns:
            rsi = latest['rsi']
            if rsi > 70:
                patterns.append({
                    'type': 'Momentum',
                    'pattern': 'Overbought',
                    'description': f"RSI at {rsi:.2f} indicates overbought conditions"
                })
            elif rsi < 30:
                patterns.append({
                    'type': 'Momentum',
                    'pattern': 'Oversold',
                    'description': f"RSI at {rsi:.2f} indicates oversold conditions"
                })

        # 3. Bollinger Bands Position
        if 'bb_upper' in df.columns:
            if latest['close'] > latest['bb_upper']:
                patterns.append({
                    'type': 'Volatility',
                    'pattern': 'Above Upper Band',
                    'description': 'Price breaking above Bollinger upper band - potential continuation or reversal'
                })
            elif latest['close'] < latest['bb_lower']:
                patterns.append({
                    'type': 'Volatility',
                    'pattern': 'Below Lower Band',
                    'description': 'Price breaking below Bollinger lower band - potential bounce or further decline'
                })

            # Bollinger Squeeze
            bandwidth = (latest['bb_upper'] - latest['bb_lower']) / latest['bb_middle']
            avg_bandwidth = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']).tail(20).mean()
            if bandwidth < avg_bandwidth * 0.7:
                patterns.append({
                    'type': 'Volatility',
                    'pattern': 'Bollinger Squeeze',
                    'description': 'Low volatility squeeze - potential breakout coming'
                })

        # 4. MACD Signals
        if 'macd' in df.columns:
            macd_cross = self._detect_macd_crossover(df)
            if macd_cross:
                patterns.append({
                    'type': 'Momentum',
                    'pattern': macd_cross['type'],
                    'description': macd_cross['description']
                })

        # 5. Volume Analysis
        if 'volume' in df.columns and 'volume_ma' in df.columns:
            if latest['volume'] > latest['volume_ma'] * 1.5:
                patterns.append({
                    'type': 'Volume',
                    'pattern': 'High Volume',
                    'description': f"Volume at {latest['volume']:.0f} is {(latest['volume']/latest['volume_ma']):.1f}x average"
                })

        # 6. Candlestick Patterns
        candle_pattern = self._detect_candlestick_pattern(df)
        if candle_pattern:
            patterns.append(candle_pattern)

        return patterns

    def _detect_macd_crossover(self, df):
        """Detect MACD crossovers"""
        if len(df) < 2:
            return None

        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Bullish crossover
        if previous['macd'] < previous['macd_signal'] and current['macd'] > current['macd_signal']:
            return {
                'type': 'MACD Bullish Cross',
                'description': 'MACD crossed above signal line - bullish signal'
            }

        # Bearish crossover
        if previous['macd'] > previous['macd_signal'] and current['macd'] < current['macd_signal']:
            return {
                'type': 'MACD Bearish Cross',
                'description': 'MACD crossed below signal line - bearish signal'
            }

        return None

    def _detect_candlestick_pattern(self, df):
        """Detect basic candlestick patterns"""
        if len(df) < 3:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        body = abs(latest['close'] - latest['open'])
        upper_shadow = latest['high'] - max(latest['close'], latest['open'])
        lower_shadow = min(latest['close'], latest['open']) - latest['low']
        range_size = latest['high'] - latest['low']

        # Doji
        if body < range_size * 0.1:
            return {
                'type': 'Candlestick',
                'pattern': 'Doji',
                'description': 'Indecision candle - potential reversal or continuation'
            }

        # Hammer (bullish reversal)
        if lower_shadow > body * 2 and upper_shadow < body * 0.3 and latest['close'] > latest['open']:
            return {
                'type': 'Candlestick',
                'pattern': 'Hammer',
                'description': 'Bullish reversal pattern at support'
            }

        # Shooting Star (bearish reversal)
        if upper_shadow > body * 2 and lower_shadow < body * 0.3 and latest['close'] < latest['open']:
            return {
                'type': 'Candlestick',
                'pattern': 'Shooting Star',
                'description': 'Bearish reversal pattern at resistance'
            }

        # Engulfing patterns
        if latest['close'] > latest['open'] and prev['close'] < prev['open']:
            if latest['open'] <= prev['close'] and latest['close'] >= prev['open']:
                return {
                    'type': 'Candlestick',
                    'pattern': 'Bullish Engulfing',
                    'description': 'Strong bullish reversal pattern'
                }

        if latest['close'] < latest['open'] and prev['close'] > prev['open']:
            if latest['open'] >= prev['close'] and latest['close'] <= prev['open']:
                return {
                    'type': 'Candlestick',
                    'pattern': 'Bearish Engulfing',
                    'description': 'Strong bearish reversal pattern'
                }

        return None

    def generate_report(self, df, patterns, support_resistance):
        """Generate text analysis report"""
        latest = df.iloc[-1]

        report = []
        report.append("=" * 80)
        report.append("NIFTY LIVE CHART ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Data Range: {df.index[0].strftime('%Y-%m-%d %H:%M')} to {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
        report.append(f"Total Candles: {len(df)}")
        report.append("")

        # Current Price
        report.append("CURRENT PRICE")
        report.append("-" * 80)
        report.append(f"Close: {latest['close']:.2f}")
        report.append(f"Open: {latest['open']:.2f}")
        report.append(f"High: {latest['high']:.2f}")
        report.append(f"Low: {latest['low']:.2f}")
        change = latest['close'] - latest['open']
        change_pct = (change / latest['open']) * 100
        report.append(f"Change: {change:+.2f} ({change_pct:+.2f}%)")
        if 'volume' in df.columns:
            report.append(f"Volume: {latest['volume']:.0f}")
        report.append("")

        # Detected Patterns
        report.append("DETECTED PATTERNS")
        report.append("-" * 80)
        if patterns:
            for i, pattern in enumerate(patterns, 1):
                report.append(f"{i}. [{pattern['type']}] {pattern['pattern']}")
                report.append(f"   {pattern['description']}")
                report.append("")
        else:
            report.append("No significant patterns detected")
            report.append("")

        # Support & Resistance
        report.append("KEY SUPPORT & RESISTANCE LEVELS")
        report.append("-" * 80)
        if support_resistance:
            resistance_levels = [l for l in support_resistance if l['type'] == 'resistance']
            support_levels = [l for l in support_resistance if l['type'] == 'support']

            if resistance_levels:
                report.append("Resistance Levels:")
                for level in resistance_levels[:5]:
                    report.append(f"  {level['price']:.2f} (Touches: {level['touches']})")
                report.append("")

            if support_levels:
                report.append("Support Levels:")
                for level in support_levels[:5]:
                    report.append(f"  {level['price']:.2f} (Touches: {level['touches']})")
                report.append("")
        else:
            report.append("No clear support/resistance levels detected")
            report.append("")

        # Technical Indicators
        report.append("TECHNICAL INDICATORS")
        report.append("-" * 80)
        if 'ema_20' in df.columns:
            report.append(f"EMA 20: {latest['ema_20']:.2f}")
            report.append(f"EMA 50: {latest['ema_50']:.2f}")
        if 'rsi' in df.columns:
            report.append(f"RSI (14): {latest['rsi']:.2f}")
        if 'macd' in df.columns:
            report.append(f"MACD: {latest['macd']:.4f}")
            report.append(f"MACD Signal: {latest['macd_signal']:.4f}")
            report.append(f"MACD Histogram: {latest['macd_histogram']:.4f}")
        if 'bb_upper' in df.columns:
            report.append(f"Bollinger Upper: {latest['bb_upper']:.2f}")
            report.append(f"Bollinger Middle: {latest['bb_middle']:.2f}")
            report.append(f"Bollinger Lower: {latest['bb_lower']:.2f}")
        if 'atr' in df.columns:
            report.append(f"ATR (14): {latest['atr']:.2f}")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def plot_chart(self, df, patterns, support_resistance, save_path="nifty_chart_analysis.png"):
        """Create comprehensive chart visualization"""
        logger.info("Creating chart visualization...")

        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(5, 1, height_ratios=[3, 1, 1, 1, 1], hspace=0.3)

        # 1. Main Price Chart with EMAs and Bollinger Bands
        ax1 = fig.add_subplot(gs[0])

        # Candlestick chart
        for idx in range(len(df)):
            row = df.iloc[idx]
            color = 'green' if row['close'] >= row['open'] else 'red'

            # Draw candle body
            ax1.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=0.5)
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            rect = Rectangle((idx - 0.4, bottom), 0.8, height, facecolor=color, edgecolor=color)
            ax1.add_patch(rect)

        # EMAs
        if 'ema_20' in df.columns:
            ax1.plot(range(len(df)), df['ema_20'], label='EMA 20', color='blue', linewidth=1.5)
            ax1.plot(range(len(df)), df['ema_50'], label='EMA 50', color='orange', linewidth=1.5)

        # Bollinger Bands
        if 'bb_upper' in df.columns:
            ax1.plot(range(len(df)), df['bb_upper'], label='BB Upper', color='gray', linestyle='--', linewidth=1, alpha=0.7)
            ax1.plot(range(len(df)), df['bb_middle'], label='BB Middle', color='gray', linestyle='--', linewidth=1, alpha=0.7)
            ax1.plot(range(len(df)), df['bb_lower'], label='BB Lower', color='gray', linestyle='--', linewidth=1, alpha=0.7)
            ax1.fill_between(range(len(df)), df['bb_upper'], df['bb_lower'], alpha=0.1, color='gray')

        # Support & Resistance Lines
        if support_resistance:
            current_price = df['close'].iloc[-1]
            for level in support_resistance[:5]:  # Top 5 levels
                color = 'red' if level['type'] == 'resistance' else 'green'
                linestyle = '-' if level['touches'] >= 3 else '--'
                ax1.axhline(y=level['price'], color=color, linestyle=linestyle, linewidth=1, alpha=0.6)

        ax1.set_title(f"NIFTY 50 - Live Chart Analysis\nLast Updated: {df.index[-1].strftime('%Y-%m-%d %H:%M')}", fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. Volume
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        if 'volume' in df.columns:
            colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red' for i in range(len(df))]
            ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.6)
            if 'volume_ma' in df.columns:
                ax2.plot(range(len(df)), df['volume_ma'], label='Volume MA', color='blue', linewidth=1.5)
            ax2.set_ylabel('Volume', fontsize=10)
            ax2.legend(loc='upper left', fontsize=8)
            ax2.grid(True, alpha=0.3)

        # 3. RSI
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        if 'rsi' in df.columns:
            ax3.plot(range(len(df)), df['rsi'], label='RSI (14)', color='purple', linewidth=1.5)
            ax3.axhline(y=70, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
            ax3.axhline(y=30, color='green', linestyle='--', linewidth=0.8, alpha=0.7)
            ax3.axhline(y=50, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
            ax3.fill_between(range(len(df)), 70, 100, alpha=0.1, color='red')
            ax3.fill_between(range(len(df)), 0, 30, alpha=0.1, color='green')
            ax3.set_ylabel('RSI', fontsize=10)
            ax3.set_ylim(0, 100)
            ax3.legend(loc='upper left', fontsize=8)
            ax3.grid(True, alpha=0.3)

        # 4. MACD
        ax4 = fig.add_subplot(gs[3], sharex=ax1)
        if 'macd' in df.columns:
            ax4.plot(range(len(df)), df['macd'], label='MACD', color='blue', linewidth=1.5)
            ax4.plot(range(len(df)), df['macd_signal'], label='Signal', color='red', linewidth=1.5)
            colors = ['green' if h >= 0 else 'red' for h in df['macd_histogram']]
            ax4.bar(range(len(df)), df['macd_histogram'], label='Histogram', color=colors, alpha=0.4)
            ax4.axhline(y=0, color='black', linewidth=0.8)
            ax4.set_ylabel('MACD', fontsize=10)
            ax4.legend(loc='upper left', fontsize=8)
            ax4.grid(True, alpha=0.3)

        # 5. ATR (Volatility)
        ax5 = fig.add_subplot(gs[4], sharex=ax1)
        if 'atr' in df.columns:
            ax5.plot(range(len(df)), df['atr'], label='ATR (14)', color='orange', linewidth=1.5)
            ax5.fill_between(range(len(df)), df['atr'], alpha=0.3, color='orange')
            ax5.set_ylabel('ATR', fontsize=10)
            ax5.set_xlabel('Candles', fontsize=10)
            ax5.legend(loc='upper left', fontsize=8)
            ax5.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Chart saved to {save_path}")

        return save_path


def main():
    """Main execution function"""
    print("=" * 80)
    print("NIFTY LIVE CHART ANALYSIS")
    print("=" * 80)
    print()

    # Initialize components
    try:
        print("Initializing broker and database...")
        broker = ZerodhaBroker()
        db = DatabaseManager()
        market_data = MarketDataHandler(broker, db)
        indicator_engine = IndicatorEngine()

        # Check if broker is connected
        if not broker.kite:
            print("\nERROR: Broker not connected!")
            print("Please ensure you have authenticated with Zerodha.")
            print("Run the main trading bot first to authenticate, or set up credentials.")
            return 1

        print("✓ Broker connected")
        print()

        # Initialize analyzer
        analyzer = ChartAnalyzer(market_data, indicator_engine)

        # Fetch data
        print("Fetching NIFTY market data...")
        df = analyzer.fetch_data(symbol="NIFTY", num_candles=200, interval="15minute")

        if df is None or df.empty:
            print("ERROR: Failed to fetch market data")
            return 1

        print(f"✓ Fetched {len(df)} candles")
        print()

        # Calculate indicators
        print("Calculating technical indicators...")
        df = analyzer.calculate_indicators(df)
        print("✓ Indicators calculated")
        print()

        # Detect patterns
        print("Analyzing chart patterns...")
        patterns = analyzer.detect_patterns(df)
        print(f"✓ Detected {len(patterns)} patterns")
        print()

        # Detect support/resistance
        print("Detecting support and resistance levels...")
        support_resistance = analyzer.detect_support_resistance(df)
        print(f"✓ Found {len(support_resistance)} key levels")
        print()

        # Generate report
        print("Generating analysis report...")
        report = analyzer.generate_report(df, patterns, support_resistance)
        print(report)
        print()

        # Save report to file
        report_file = "nifty_analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"✓ Report saved to {report_file}")
        print()

        # Create chart
        print("Creating chart visualization...")
        chart_file = analyzer.plot_chart(df, patterns, support_resistance)
        print(f"✓ Chart saved to {chart_file}")
        print()

        print("=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
