import pandas as pd
import numpy as np
import os

def run_ema_research():
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading")
    TICK_FILE = os.path.join(CACHE_DIR, "gold_ticks.parquet")
    M1_FILE = os.path.join(CACHE_DIR, "XAUUSD+_m1_scalping_data.parquet")
    
    if not os.path.exists(TICK_FILE) or not os.path.exists(M1_FILE):
        print("Required data files not found.")
        return

    ticks = pd.read_parquet(TICK_FILE)
    m1 = pd.read_parquet(M1_FILE)
    
    # Calculate Indicators on M1
    m1['hh'] = m1['high'].rolling(15).max().shift(1)
    m1['ll'] = m1['low'].rolling(15).min().shift(1)
    m1['ema200'] = m1['close'].ewm(span=200, adjust=False).mean()
    
    # ADX
    df = m1
    df['up'] = df['high'].diff().clip(lower=0)
    df['down'] = (-df['low'].diff()).clip(lower=0)
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['di_up'] = 100 * (df['up'].rolling(14).mean() / df['atr'])
    df['di_down'] = 100 * (df['down'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * ((df['di_up'] - df['di_down']).abs() / (df['di_up'] + df['di_down']))
    df['adx'] = df['dx'].rolling(14).mean()
    
    print(f"Analyzing {len(ticks)} ticks with EMA 200 Trend Filter...")

    def test_logic(ticks, m1, use_ema=False):
        trades = []
        in_pos = False
        pos_type = 0
        sl, tp = 0, 0
        trail_dist = 0.20
        risk = 1.0
        rr = 3.0
        spread = 0.15
        
        m1_lookup = m1.set_index('time')[['hh', 'll', 'adx', 'ema200']].to_dict('index')
        
        for i in range(100, len(ticks)):
            tick = ticks.iloc[i]
            t_key = tick['time'].replace(second=0, microsecond=0)
            if t_key not in m1_lookup: continue
            
            row = m1_lookup[t_key]
            
            if not in_pos:
                # Basic Signal
                bull_break = tick['ask'] > row['hh'] and row['adx'] > 25
                bear_break = tick['bid'] < row['ll'] and row['adx'] > 25
                
                # EMA Filter
                if use_ema:
                    if bull_break and tick['ask'] < row['ema200']: bull_break = False # Don't buy below EMA
                    if bear_break and tick['bid'] > row['ema200']: bear_break = False # Don't sell above EMA

                if bull_break:
                    in_pos, pos_type, entry_p = True, 1, tick['ask']
                    sl, tp = entry_p - risk, entry_p + (risk * rr)
                elif bear_break:
                    in_pos, pos_type, entry_p = True, -1, tick['bid']
                    sl, tp = entry_p + risk, entry_p - (risk * rr)
            else:
                price = tick['bid'] if pos_type == 1 else tick['ask']
                if pos_type == 1:
                    new_sl = price - trail_dist
                    if new_sl > sl: sl = new_sl
                    if tick['bid'] <= sl: trades.append(sl - entry_p); in_pos = False
                    elif tick['bid'] >= tp: trades.append(tp - entry_p); in_pos = False
                else:
                    new_sl = price + trail_dist
                    if new_sl < sl: sl = new_sl
                    if tick['ask'] >= sl: trades.append(entry_p - sl); in_pos = False
                    elif tick['ask'] <= tp: trades.append(entry_p - tp); in_pos = False
                    
        if not trades: return 0, 0, 0
        return sum(trades)*10, len([t for t in trades if t > 0])/len(trades), len(trades)

    print("\n--- EMA 200 FILTER RESEARCH (TICK DATA) ---")
    
    pnl1, wr1, n1 = test_logic(ticks, m1, use_ema=False)
    print(f"NO EMA FILTER:  PnL: ${pnl1:8.2f} | WR: {wr1:8.2%} | Trades: {n1}")
    
    pnl2, wr2, n2 = test_logic(ticks, m1, use_ema=True)
    print(f"WITH EMA 200:   PnL: ${pnl2:8.2f} | WR: {wr2:8.2%} | Trades: {n2}")
    
    improvement = ((wr2 - wr1) / wr1) * 100 if wr1 > 0 else 0
    print(f"\nWin Rate Improvement: {improvement:+.2f}%")

if __name__ == '__main__':
    run_ema_research()
