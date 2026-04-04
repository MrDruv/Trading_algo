import pandas as pd
import numpy as np
import math

def run_deep_research():
    df = pd.read_parquet('btc_30d.parquet')
    print(f"Analyzing {len(df)} bars of BTCUSD M1 data...")
    
    # -----------------------------------------------------------------------
    # Logic 1: Trend Breakout (High/Low of last 15 min + ADX)
    # -----------------------------------------------------------------------
    
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)
    
    # Simple ADX (to filter chop)
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
                # Logic 1: Breakout
                if logic_type == 'Breakout':
                    if row['close'] > row['hh'] and row['adx'] > 25:
                        in_pos, pos_type, entry_price = True, 1, row['open'] + 2.0
                        sl, tp = entry_price - risk, entry_price + (risk * rr)
                    elif row['close'] < row['ll'] and row['adx'] > 25:
                        in_pos, pos_type, entry_price = True, -1, row['open'] - 2.0
                        sl, tp = entry_price + risk, entry_price - (risk * rr)
                # Logic 2: Mean Reversion (Z-Score)
                elif logic_type == 'MeanRev':
                    z = (row['close'] - df['close'].iloc[i-100:i].mean()) / df['close'].iloc[i-100:i].std()
                    if z < -2.0:
                        in_pos, pos_type, entry_price = True, 1, row['open'] + 2.0
                        sl, tp = entry_price - risk, entry_price + (risk * rr)
                    elif z > 2.0:
                        in_pos, pos_type, entry_price = True, -1, row['open'] - 2.0
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
        pnl = sum(trades) * 0.06
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        return pnl, win_rate, len(trades)

    # Search
    best_pnl = -9999
    best_info = ""
    
    for logic in ['Breakout', 'MeanRev']:
        for rsk in [50.0, 100.0, 150.0]:
            for r in [1.5, 2.0]:
                for trl in [20.0, 50.0]:
                    pnl, wr, n = test_logic(df, logic, {'risk': rsk, 'rr': r, 'trail': trl})
                    if pnl > best_pnl:
                        best_pnl = pnl
                        best_info = f"LOGIC: {logic} | PARAMS: risk={rsk}, rr={r}, trail={trl} | PnL: ${pnl:.2f} | WR: {wr:.2%} | Trades: {n}"
                        print(f"New Best found: {best_info}")
    
    print("---")
    print("FINAL BEST SCALPING RESEARCH RESULT:")
    print(best_info)

if __name__ == '__main__':
    run_deep_research()
