# NIFTY Live Chart Analysis Tool

This script performs comprehensive technical analysis on live NIFTY chart data fetched from Zerodha.

## Features

- **Live Data Fetching**: Retrieves real-time NIFTY candle data via Zerodha API
- **Technical Indicators**:
  - EMA (20 & 50)
  - RSI (14)
  - MACD
  - Bollinger Bands
  - ATR (Average True Range)
  - Volume Moving Average

- **Pattern Detection**:
  - Trend identification (uptrend/downtrend/sideways)
  - Support and resistance levels
  - Candlestick patterns (Doji, Hammer, Shooting Star, Engulfing)
  - Overbought/oversold conditions
  - MACD crossovers
  - Bollinger Band squeezes
  - Volume spikes

- **Visual Output**: Generates a comprehensive multi-panel chart with:
  - Price action with candlesticks
  - EMAs and Bollinger Bands
  - Support/resistance levels
  - Volume
  - RSI
  - MACD
  - ATR

## Prerequisites

1. **Zerodha Authentication**: You must be authenticated with Zerodha first
2. **Market Hours**: Best results during market hours (9:15 AM - 3:30 PM IST)
3. **Dependencies**: All required packages are in `requirements.txt`

## Usage

### Quick Run

```bash
python analyze_nifty_chart.py
```

### What It Does

1. Connects to your Zerodha account
2. Fetches last 200 candles of 15-minute NIFTY data
3. Calculates all technical indicators
4. Detects chart patterns and key levels
5. Generates two outputs:
   - `nifty_analysis_report.txt` - Text report with all findings
   - `nifty_chart_analysis.png` - Visual chart with indicators

### Output Files

**nifty_analysis_report.txt** - Contains:
- Current price and change
- Detected patterns with descriptions
- Support and resistance levels
- All technical indicator values

**nifty_chart_analysis.png** - Multi-panel chart showing:
- Price with EMAs, Bollinger Bands, and S/R levels
- Volume with moving average
- RSI with overbought/oversold zones
- MACD with signal line and histogram
- ATR for volatility measurement

## Example Output

```
================================================================================
NIFTY LIVE CHART ANALYSIS REPORT
================================================================================
Generated: 2025-11-20 14:30:45
Data Range: 2025-11-19 09:15 to 2025-11-20 14:30
Total Candles: 200

CURRENT PRICE
--------------------------------------------------------------------------------
Close: 24350.75
Open: 24280.50
High: 24385.25
Low: 24265.80
Change: +70.25 (+0.29%)
Volume: 1250000

DETECTED PATTERNS
--------------------------------------------------------------------------------
1. [Trend] UPTREND
   Price: 24350.75, EMA20: 24298.30, EMA50: 24215.60

2. [Momentum] Neutral
   RSI at 58.45 indicates neutral momentum

3. [Momentum] MACD Bullish Cross
   MACD crossed above signal line - bullish signal

KEY SUPPORT & RESISTANCE LEVELS
--------------------------------------------------------------------------------
Resistance Levels:
  24385.25 (Touches: 4)
  24420.80 (Touches: 3)
  24455.60 (Touches: 2)

Support Levels:
  24265.80 (Touches: 5)
  24190.50 (Touches: 3)
  24150.75 (Touches: 2)

TECHNICAL INDICATORS
--------------------------------------------------------------------------------
EMA 20: 24298.30
EMA 50: 24215.60
RSI (14): 58.45
MACD: 12.5500
MACD Signal: 10.2300
MACD Histogram: 2.3200
Bollinger Upper: 24420.80
Bollinger Middle: 24298.50
Bollinger Lower: 24176.20
ATR (14): 85.40
```

## Customization

You can modify the script to:
- Change timeframe (5minute, 15minute, 30minute, 60minute, day)
- Adjust number of candles (default: 200)
- Modify indicator periods
- Add more pattern detection rules
- Change chart styling

### Example Modifications

```python
# Fetch 5-minute candles instead
df = analyzer.fetch_data(symbol="NIFTY", num_candles=300, interval="5minute")

# Analyze BANKNIFTY instead
df = analyzer.fetch_data(symbol="BANKNIFTY", num_candles=200, interval="15minute")
```

## Troubleshooting

### "ERROR: Broker not connected"
- Ensure you've authenticated with Zerodha
- Run the main trading bot first: `python main.py`
- Check your API credentials in `config/credentials.py`

### "Failed to fetch market data"
- Check if markets are open
- Verify your Zerodha session is active
- Check internet connectivity

### Empty or incomplete charts
- Ensure sufficient historical data is available
- Try reducing the number of candles requested
- Check if the symbol name is correct

## Technical Details

- **Data Source**: Zerodha Kite API
- **Default Timeframe**: 15-minute candles
- **Lookback Period**: 200 candles (50 hours of trading)
- **Chart Format**: PNG, 1600x1200 pixels, 150 DPI

## Integration

This script can be:
- Run manually for quick analysis
- Scheduled with cron for periodic reports
- Integrated into the main trading bot
- Modified to analyze other instruments

## Notes

- Analysis is based on historical data and indicators
- No guarantee of prediction accuracy
- Use for educational and analytical purposes
- Always verify signals with your own analysis
- Past performance doesn't indicate future results

## Support

For issues or questions:
1. Check the logs in the console output
2. Review the `logs/` directory for detailed error messages
3. Ensure all dependencies are installed
4. Verify Zerodha API credentials are correct
