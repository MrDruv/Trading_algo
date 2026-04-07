import pandas as pd
import numpy as np
import os

def run_momentum_research():
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading")
    DATA_FILE = os.path.join(CACHE_DIR, "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE): return
    
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing Gold M1: 'High Movement' Momentum Spike Filter...")
    
    # Levels & Indicators
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)
    df['range'] = df['high'] - df['low']
    df['avg_range'] = df['range'].rolling(10).mean().shift(1)
    
    # ADX
    df['up'] = df['high'].diff().clip(lower=0)
    df['down'] = (-df['low'].diff()).clip(lower=0)
    df['atr'] = df['range'].rolling(14).mean()
    df['di_up'] = 100 * (df['up'].rolling(14).mean() / df['atr'])
    df['di_down'] = 100 * (df['down'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * ((df['di_up'] - df['di_down']).abs() / (df['di_up'] + df['di_down']))
    df['adx'] = df['dx'].rolling(14).mean()

    def test_logic(df, mom_mult=1.0):
        trades = []
        in_pos = False
        pos_type = 0
        sl, tp = 0, 0
        entry_p = 0
        risk, rr, trail = 1.0, 3.0, 0.20
        spread = 0.15
        
        for i in range(50, len(df)):
            row = df.iloc[i]
            if not in_pos:
                # BREAKOUT + ADX + MOMENTUM SPIKE
                # mom_mult 1.5 means candle must be 50% larger than average
                is_mom_spike = row['range'] > (row['avg_range'] * mom_mult)
                
                bull = row['high'] > row['hh'] and row['adx'] > 25 and is_mom_spike
                bear = row['low'] < row['ll'] and row['adx'] > 25 and is_mom_spike
                
                if bull:
                    in_pos, pos_type, entry_p = True, 1, row['hh'] + spread
                    sl, tp = entry_p - risk, entry_p + (risk * rr)
                elif bear:
                    in_pos, pos_type, entry_p = True, -1, row['ll'] - spread
                    sl, tp = entry_p + risk, entry_p - (risk * rr)
            else:
                price = row['close']
                if pos_type == 1:
                    new_sl = price - trail
                    if new_sl > sl: sl = new_sl
                    if row['low'] <= sl: trades.append(sl - entry_p); in_pos = False
                    elif row['high'] >= tp: trades.append(tp - entry_p); in_pos = False
                else:
                    new_sl = price + trail
                    if new_sl < sl: sl = new_sl
                    if row['high'] >= sl: trades.append(entry_p - sl); in_pos = False
                    elif row['low'] <= tp: trades.append(entry_p - tp); in_pos = False
                    
        if not trades: return 0, 0, 0
        return sum(trades)*10, len([t for t in trades if t > 0])/len(trades), len(trades)

    print(f"{'MOM MULT':10} | {'PnL':10} | {'WR':10} | {'TRADES':10}")
    for m in [1.0, 1.2, 1.5, 2.0]:
        pnl, wr, n = test_logic(df, mom_mult=m)
        print(f"{m:10.1f}x | ${pnl:8.2f} | {wr:8.2%} | {n:10}")

if __name__ == '__main__':
    run_momentum_research()
