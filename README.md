# Diamond Engine | Institutional Scalping Command Center (V11.5)

An elite, autonomous high-frequency scalping system for Bitcoin (BTCUSD) and Gold (XAUUSD) powered by the MetaTrader 5 Python API and a professional Flask-based web dashboard.

## 🚀 Key Features (V11.5 - Pure Momentum)

- **1.5x Momentum Spike Filter**: Only enters trades during high candle movement. Requires the breakout candle to be 50% larger than the 10-minute average.
- **ADX Trend Confirmation**: Uses the Average Directional Index (ADX > 25) to ensure entries only occur during strong, confirmed trends.
- **15-Minute Structural Breakouts**: Precision entry points based on the high/low of the last 15 bars.
- **Strict 1:3 Risk-to-Reward**: Research-optimized targets designed to capitalize on aggressive momentum bursts.
- **Constant Trailing Stop**: Instant profit protection that follows the price from the moment of entry.
- **Professional Command Center**: A Flask-based web dashboard ([http://localhost:5000](http://localhost:5000)) for real-time control, account sync, and performance monitoring.

## 📉 Trading Strategy: Momentum Spike Breakout

| Component | Bitcoin (BTCUSD) | Gold (XAUUSD) |
|-----------|-----------------|---------------|
| **Primary Logic** | 15-min Breakout | 15-min Breakout |
| **Momentum Filter**| 1.5x Avg Range | 1.5x Avg Range |
| **Trend Filter** | ADX > 25 | ADX > 25 |
| **Risk/Reward** | 1:3 | 1:3 |

## 🛠 Setup & Installation

### Prerequisites
- Windows OS
- [MetaTrader 5 Terminal](https://www.metatrader5.com/en/download)
- Python 3.10+

### Quick Start
1. **Clone and Install**:
   ```bash
   git clone https://github.com/MrDruv/Trading_algo.git
   cd Trading_algo
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Launch Dashboard**:
   ```bash
   python dashboard.py
   ```
3. **Launch Engine**:
   ```bash
   python live_execution.py
   ```
4. **Connect**: Open [http://localhost:5000](http://localhost:5000), initialize your terminal path, and activate the system.

## 📂 Project Structure

- `live_execution.py`: Core V11.5 execution engine with Momentum & ADX filters.
- `dashboard.py`: Flask web interface for real-time monitoring.
- `bot_state.json`: Atomic state persistence between engine and UI.
- `train.py`: Historical logic container.

## ⚠️ Disclaimer

Trading involves significant risk. This system is designed for high-frequency scalping and requires low-latency execution and tight spreads. Always test on a demo account before live deployment.
