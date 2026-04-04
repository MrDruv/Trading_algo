# Quantum Scalper | Institutional BTCUSD Command Center (V4.2.1)

An elite, autonomous high-frequency scalping system for Bitcoin (BTCUSD) powered by the MetaTrader 5 Python API and a professional Flask-based web dashboard.

## 🚀 Key Features

- **V4.2.1 "Superb" Logic**: Combines ultra-fast EMA 5/13 crossovers with institutional Fair Value Gap (FVG) detection and 15-minute structural breakouts.
- **Professional Command Center**: A high-end web dashboard ([http://localhost:5000](http://localhost:5000)) for real-time control and monitoring.
- **Dynamic Risk Management**: 
  - **Tight SL**: $15.00 initial protection.
  - **Hyper-Aggressive Trailing**: Starts at $10.00 profit with a precise $5.00 trailing distance.
  - **Unlimited Upside**: No fixed targets; rides trends indefinitely until the trail triggers.
- **Live Account Sync**: Real-time tracking of Balance, Equity, and Broker details (Optimized for Vantage/Exness/FundedNext).
- **Session Analysis**: Automated Win Rate calculation and consolidated trade history (one row per position).

## 🛠 Setup & Installation

### Prerequisites
- Windows OS
- [MetaTrader 5 Terminal](https://www.metatrader5.com/en/download)
- Python 3.10+
- [uv](https://github.com/astral.sh/uv) (Recommended package manager)

### Quick Start
1. **Clone and Install**:
   ```bash
   git clone https://github.com/MrDruv/Trading_algo.git
   cd Trading_algo
   uv sync
   ```
2. **Launch Dashboard**:
   ```bash
   uv run dashboard.py
   ```
3. **Launch Engine**:
   ```bash
   uv run live_execution.py
   ```
4. **Connect**: Open [http://localhost:5000](http://localhost:5000), enter your `terminal64.exe` path, click **Initialize Link**, and then **Activate System**.

## 📉 Trading Strategy: Institutional Fast-Momentum

| Component | Logic |
|-----------|-------|
| **Trend Filter** | Fast EMA (5) vs Slow EMA (13) |
| **Triggers** | 15-min High/Low Breakout OR Fair Value Gap (FVG) |
| **Initial SL** | $15.00 (Fixed) |
| **Trailing Stop**| Starts @ +$10.00 \| Distance: $5.00 |
| **Take Profit** | None (Ride the momentum) |
| **Lot Size** | Configurable via Dashboard (Default: 0.50) |

## 📂 Project Structure

- `live_execution.py`: Multi-account sync engine and position manager.
- `dashboard.py`: Professional Flask-based web interface.
- `train.py`: Core strategy logic (`superb_momentum_logic`).
- `bot_state.json`: Real-time state persistence between engine and UI.

## ⚠️ Disclaimer

Trading involves significant risk. This system is designed for high-frequency scalping and requires low-latency execution and tight spreads. Always test on a demo account before live deployment.
