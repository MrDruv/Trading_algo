import pandas as pd
import numpy as np
import math
import os

def run_close_above_research():
    DATA_FILE = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading", "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found at {DATA_FILE}")
        return
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing {len(df)} bars of Gold M1 data: Touch vs Close Entry...")
    
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

    def test_logic(df, params, entry_type='touch'):
        trades = []
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl, tp = 0, 0
        risk = params['risk']
        rr = params['rr']
        trail = params['trail']
        
        last_trade_time = None

        for i in range(50, len(df)):
            row = df.iloc[i]
            
            if last_trade_time is not None and row['time'] == last_trade_time:
                continue

            if not in_pos:
                # ENTRY SIGNALS
                if entry_type == 'touch':
                    # Current: Trigger on High/Low touch
                    bull_signal = row['high'] > row['hh'] and row['adx'] > 25
                    bear_signal = row['low'] < row['ll'] and row['adx'] > 25
                    entry_p = row['hh'] + 0.10 if bull_signal else (row['ll'] - 0.10)
                else:
                    # New: Trigger only on Candle Close
                    bull_signal = row['close'] > row['hh'] and row['adx'] > 25
                    bear_signal = row['close'] < row['ll'] and row['adx'] > 25
                    entry_p = row['close'] # Enter at the close price

                if bull_signal:
                    in_pos, pos_type, entry_price = True, 1, entry_p
                    sl, tp = entry_price - risk, entry_price + (risk * rr)
                    last_trade_time = row['time']
                elif bear_signal:
                    in_pos, pos_type, entry_price = True, -1, entry_p
                    sl, tp = entry_price + risk, entry_price - (risk * rr)
                    last_trade_time = row['time']
            else:
                # Trailing
                if trail > 0:
                    if pos_type == 1:
                        new_sl = row['close'] - trail
                        if new_sl > sl: sl = new_sl
                    else:
                        new_sl = row['close'] + trail
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

    print("\n--- PERFORMANCE COMPARISON (GOLD 0.1 LOT) ---")
    
    # Current Touch Entry
    pnl1, wr1, n1 = test_logic(df, {'risk': 1.0, 'rr': 3.0, 'trail': 0.20}, entry_type='touch')
    print(f"TOUCH ENTRY (Current): PnL: ${pnl1:,.2f} | WR: {wr1:.2%} | Trades: {n1}")
    
    # New Close Entry
    pnl2, wr2, n2 = test_logic(df, {'risk': 1.0, 'rr': 3.0, 'trail': 0.20}, entry_type='close')
    print(f"CLOSE ENTRY (New):     PnL: ${pnl2:,.2f} | WR: {wr2:.2%} | Trades: {n2}")
    
    wr_diff = wr2 - wr1
    print(f"\nWin Rate Change: {wr_diff:+.2f}%")

if __name__ == '__main__':
    run_close_above_research()
