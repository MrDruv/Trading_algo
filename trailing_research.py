import pandas as pd
import numpy as np
import math
import os

def run_trailing_research():
    DATA_FILE = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading", "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found at {DATA_FILE}")
        return
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing Gold M1: Finding the best Trailing Stop for Live Spread ($0.15)...")
    
    # Pre-calculate Indicators
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)
    
    # ADX
    df['up'] = df['high'].diff().clip(lower=0)
    df['down'] = (-df['low'].diff()).clip(lower=0)
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['di_up'] = 100 * (df['up'].rolling(14).mean() / df['atr'])
    df['di_down'] = 100 * (df['down'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * ((df['di_up'] - df['di_down']).abs() / (df['di_up'] + df['di_down']))
    df['adx'] = df['dx'].rolling(14).mean()

    def test_logic(df, trail_dist):
        trades = []
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl, tp = 0, 0
        risk = 1.0
        rr = 3.0
        spread = 0.15 # Realistic live spread for Gold
        
        last_trade_time = None

        for i in range(50, len(df)):
            row = df.iloc[i]
            
            if last_trade_time is not None and row['time'] == last_trade_time:
                continue

            if not in_pos:
                # Trigger on Touch
                bull_signal = row['high'] > row['hh'] and row['adx'] > 25
                bear_signal = row['low'] < row['ll'] and row['adx'] > 25
                
                if bull_signal:
                    in_pos, pos_type, entry_price = True, 1, row['hh'] + spread
                    sl, tp = entry_price - risk, entry_price + (risk * rr)
                    last_trade_time = row['time']
                elif bear_signal:
                    in_pos, pos_type, entry_price = True, -1, row['ll'] - spread
                    sl, tp = entry_price + risk, entry_price - (risk * rr)
                    last_trade_time = row['time']
            else:
                # Trailing
                if pos_type == 1:
                    new_sl = row['close'] - trail_dist
                    if new_sl > sl: sl = new_sl
                else:
                    new_sl = row['close'] + trail_dist
                    if new_sl < sl: sl = new_sl
                
                # Exit
                if pos_type == 1:
                    if row['low'] <= sl: trades.append(sl - entry_price); in_pos = False
                    elif row['high'] >= tp: trades.append(tp - entry_price); in_pos = False
                else:
                    if row['high'] >= sl: trades.append(entry_price - sl); in_pos = False
                    elif row['low'] <= tp: trades.append(entry_price - tp); in_pos = False
        
        if not trades: return 0, 0, 0
        pnl = sum(trades) * 10
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        return pnl, win_rate, len(trades)

    print("\n--- TRAILING STOP SENSITIVITY (WITH 0.15 SPREAD) ---")
    
    for t in [0.20, 0.30, 0.50, 0.75, 1.00]:
        pnl, wr, n = test_logic(df, t)
        print(f"Trail: ${t:.2f} | PnL: ${pnl:,.2f} | WR: {wr:.2%} | Trades: {n}")

if __name__ == '__main__':
    run_trailing_research()
