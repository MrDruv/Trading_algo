import os
import time
import math
import pandas as pd
import torch
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

SYMBOL = "XAUUSD+"
TIMEFRAME = mt5.TIMEFRAME_M1
TIME_BUDGET = 300        
TRAIN_BARS = 30000       
VAL_BARS = 10000          
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading")
DATA_FILE = os.path.join(CACHE_DIR, f"{SYMBOL}_m1_scalping_data.parquet")
TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

# ---------------------------------------------------------------------------
# Data Preparation
# ---------------------------------------------------------------------------

def fetch_data(num_bars):
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not mt5.initialize(path=TERMINAL_PATH):
        print("MT5 initialize failed", mt5.last_error())
        return None
        
    print(f"Fetching {num_bars} bars for {SYMBOL}...")
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, num_bars)
    mt5.shutdown()
    
    if rates is None:
        return None
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    
    df.to_parquet(DATA_FILE)
    print(f"BTCUSD Data saved to {DATA_FILE}")
    return df

def load_data():
    if not os.path.exists(DATA_FILE):
        return fetch_data(TRAIN_BARS + VAL_BARS + 100)
    return pd.read_parquet(DATA_FILE)

# ---------------------------------------------------------------------------
# Evaluation (Scalping-focused)
# ---------------------------------------------------------------------------

def backtest_strategy(df, strategy_func, params):
    trades = []
    in_position = False
    entry_price = 0
    pos_type = 0 
    sl = 0
    tp = 0
    
    spread = 1.0 # BTCUSD Typical spread in points ($1)
    trailing_dist = params.get('trailing_dist', 0.0)

    for i in range(1, len(df)):
        row = df.iloc[i]
        
        if not in_position:
            signal = strategy_func(df, i, params)
            if signal != 0:
                in_position = True
                pos_type = signal
                entry_price = row['open'] + (spread if pos_type == 1 else -spread)
                
                risk_points = params.get('risk_points', 5.0) # $5 BTC move
                rr = params.get('rr', 2.0)
                
                if pos_type == 1:
                    sl = entry_price - risk_points
                    tp = entry_price + (risk_points * rr)
                else:
                    sl = entry_price + risk_points
                    tp = entry_price - (risk_points * rr)
        else:
            if trailing_dist > 0:
                if pos_type == 1:
                    new_sl = row['close'] - trailing_dist
                    if new_sl > sl: sl = new_sl
                else:
                    new_sl = row['close'] + trailing_dist
                    if new_sl < sl: sl = new_sl

            if pos_type == 1:
                if row['low'] <= sl: 
                    trades.append((sl - entry_price))
                    in_position = False
                elif row['high'] >= tp: 
                    trades.append((tp - entry_price))
                    in_position = False
            else:
                if row['high'] >= sl:
                    trades.append((entry_price - sl))
                    in_position = False
                elif row['low'] <= tp:
                    trades.append((entry_price - tp))
                    in_position = False
                    
    if not trades: return 0.0
    returns = pd.Series(trades)
    if returns.std() == 0: return 0.0
    
    return (returns.mean() / returns.std()) * math.sqrt(len(trades))

if __name__ == "__main__":
    fetch_data(TRAIN_BARS + VAL_BARS + 100)
