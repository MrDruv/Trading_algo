import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from train import superb_momentum_logic
from datetime import datetime

# Configuration
TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOLS = ["XAUUSD+", "BTCUSD"]
BARS_TO_FETCH = 2000 # ~33 hours of M1 data

def analyze_win_rate(symbol):
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"Failed to initialize MT5 at {TERMINAL_PATH}")
        return

    print(f"\n--- Analyzing Win Rate for {symbol} ---")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, BARS_TO_FETCH)
    if rates is None:
        print(f"Could not fetch data for {symbol}")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Matching your exact logic from live_execution.py
    risk_pts = 50.0 if "BTC" in symbol.upper() else 2.0
    
    trades = []
    in_pos = False
    entry_p = 0
    sl = 0
    tp = 0
    pos_type = 0 # 1 for Buy, -1 for Sell

    for i in range(20, len(df)):
        row = df.iloc[i]
        
        if not in_pos:
            # Check for signal using your logic
            signal = superb_momentum_logic(df, None, i, {})
            if signal != 0:
                in_pos = True
                pos_type = signal
                entry_p = row['close']
                sl = entry_p - risk_pts if signal == 1 else entry_p + risk_pts
                tp = entry_p + risk_pts if signal == 1 else entry_p - risk_pts
        else:
            # Check for TP/SL/Trailing
            p_cur = row['close']
            p_high = row['high']
            p_low = row['low']
            p_profit = (p_cur - entry_p) if pos_type == 1 else (entry_p - p_cur)
            
            # --- 90% Trailing Logic ---
            target_dist = risk_pts
            if p_profit >= (target_dist * 0.9):
                lock_profit = target_dist * 0.25
                trail_level = entry_p + lock_profit if pos_type == 1 else entry_p - lock_profit
                if pos_type == 1:
                    if trail_level > sl: sl = trail_level
                else:
                    if sl == 0 or trail_level < sl: sl = trail_level

            # Exit Conditions
            if pos_type == 1:
                if p_low <= sl: # Hit SL
                    trades.append(sl - entry_p)
                    in_pos = False
                elif p_high >= tp: # Hit TP
                    trades.append(tp - entry_p)
                    in_pos = False
            else:
                if p_high >= sl: # Hit SL
                    trades.append(entry_p - sl)
                    in_pos = False
                elif p_low <= tp: # Hit TP
                    trades.append(entry_p - tp)
                    in_pos = False

    if not trades:
        print("No trades triggered in this period.")
        return

    wins = [t for t in trades if t > 0]
    wr = len(wins) / len(trades) * 100
    total_pnl = sum(trades)
    
    print(f"Total Trades: {len(trades)}")
    print(f"Wins: {len(wins)} | Losses: {len(trades) - len(wins)}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Net Points: {total_pnl:.2f}")

if __name__ == "__main__":
    for s in SYMBOLS:
        analyze_win_rate(s)
    mt5.shutdown()
