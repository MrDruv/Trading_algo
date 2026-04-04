# BTCUSD Institutional Momentum Scalper

An autonomous high-frequency scalping bot for Bitcoin (BTCUSD) using the MetaTrader 5 Python API. This bot implements an elite momentum strategy with institutional Fair Value Gap (FVG) detection and hyper-aggressive trailing stop management.

## 🚀 Features

- **Institutional Entry Logic**: Combines EMA 9/21 crossovers, Fair Value Gaps (FVG), and 15-minute price breakouts.
- **Unlimited Profit Potential**: No fixed Take Profit (TP) targets; uses a trailing stop to ride trends indefinitely.
- **Hyper-Aggressive Trailing**:
  - **Trigger**: Starts trailing as soon as price moves $10 in profit.
  - **Distance**: Maintains a tight $2.00 distance from the current price.
  - **Precision**: Checks and updates Stop Loss every 1 second.
- **Dynamic Risk Management**: Automatically handles lot sizes and provides real-time broker execution diagnostics.

## 🛠 Setup

### Prerequisites
- Windows OS
- [MetaTrader 5 Terminal](https://www.metatrader5.com/en/download)
- Python 3.10+
- [uv](https://github.com/astral.sh/uv) (Recommended package manager)

### Installation
1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd gemini-safe
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```

## 📈 Current Strategy: "Unlimited Superb"

The bot is currently configured with the **Unlimited Superb** parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Symbol** | BTCUSD | Target Asset |
| **Timeframe** | M1 (1-min) | Execution timeframe |
| **Lot Size** | 0.50 | Standard trade volume |
| **Initial SL**| $40.00 | Initial risk buffer |
| **Trailing Start**| $10.00 | Profit required to start trailing |
| **Trailing Dist** | $2.00 | Distance of SL from live price |

## 🖥 Usage

1. Open your MT5 Terminal and log in to your account (e.g., Exness or FundedNext).
2. Enable **Algo Trading** (Make sure the button is GREEN).
3. Run the bot:
   ```bash
   uv run live_execution.py
   ```

## 📂 Project Structure

- `live_execution.py`: The main execution loop and position manager.
- `train.py`: Core strategy logic (`active_momentum_scalp`).
- `prepare.py`: MT5 connection and data utility functions.
- `results.tsv`: Log of experimental performance.

## ⚠️ Disclaimer

Trading cryptocurrencies involves significant risk. This bot is provided for educational and experimental purposes. Always test on a demo/test account before using real capital.
