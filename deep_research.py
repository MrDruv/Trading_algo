import pandas as pd
import numpy as np
import math

def run_deep_research():
    import os
    DATA_FILE = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading", "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found at {DATA_FILE}")
        return
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing {len(df)} bars of XAUUSD+ (Gold) M1 data...")
    
    # Pre-calculate Indicators
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)
    df['up'] = df['high'].diff().clip(lower=0)
    df['down'] = (-df['low'].diff()).clip(lower=0)
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['di_up'] = 100 * (df['up'].rolling(14).mean() / df['atr'])
    df['di_down'] = 100 * (df['down'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * ((df['di_up'] - df['di_down']).abs() / (df['di_up'] + df['di_down']))
    df['adx'] = df['dx'].rolling(14).mean()
    
    def test_logic(df, logic_type, params):
        trades = []
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl, tp = 0, 0
        risk = params['risk']
        rr = params['rr']
        trail = params['trail']
        
        for i in range(50, len(df)):
            row = df.iloc[i]
            if not in_pos:
                if logic_type == 'Breakout':
                    if row['close'] > row['hh'] and row['adx'] > 25:
                        in_pos, pos_type, entry_price = True, 1, row['open'] + 0.10
                        sl, tp = entry_price - risk, entry_price + (risk * rr)
                    elif row['close'] < row['ll'] and row['adx'] > 25:
                        in_pos, pos_type, entry_price = True, -1, row['open'] - 0.10
                        sl, tp = entry_price + risk, entry_price - (risk * rr)
            else:
                if trail > 0:
                    if pos_type == 1:
                        new_sl = row['close'] - trail
                        if new_sl > sl: sl = new_sl
                    else:
                        new_sl = row['close'] + trail
                        if new_sl < sl: sl = new_sl
                if pos_type == 1:
                    if row['low'] <= sl: trades.append(sl - entry_price); in_pos = False
                    elif row['high'] >= tp: trades.append(tp - entry_price); in_pos = False
                else:
                    if row['high'] >= sl: trades.append(entry_price - sl); in_pos = False
                    elif row['low'] <= tp: trades.append(entry_price - tp); in_pos = False
        
        if not trades: return 0, 0, 0
        pnl = sum(trades) * 50 # Standard gold lot (0.50 lot = $50 per full dollar move)
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        return pnl, win_rate, len(trades)

    # Search
    best_pnl = -9999
    best_info = ""
    for logic in ['Breakout']:
        for rsk in [1.0, 2.0, 3.0, 5.0]:
            for r in [1.5, 2.0, 3.0]:
                for trl in [0.20, 0.50, 1.0]:
                    pnl, wr, n = test_logic(df, logic, {'risk': rsk, 'rr': r, 'trail': trl})
                    if pnl > best_pnl:
                        best_pnl = pnl
                        best_info = f"GOLD BEST found: risk=${rsk:.2f}, rr={r}, trail=${trl:.2f} | PnL: ${pnl:.2f} | WR: {wr:.2%} | Trades: {n}"
                        print(best_info)
    
    print("---")
    print("FINAL GOLD RESEARCH RESULT:")
    print(best_info)

if __name__ == '__main__':
    run_deep_research()
