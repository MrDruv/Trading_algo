import pandas as pd
import numpy as np
import os

def run_buffer_research():
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading")
    TICK_FILE = os.path.join(CACHE_DIR, "gold_ticks.parquet")
    M1_FILE = os.path.join(CACHE_DIR, "XAUUSD+_m1_scalping_data.parquet")
    
    if not os.path.exists(TICK_FILE) or not os.path.exists(M1_FILE):
        print("Required data files not found.")
        return

    ticks = pd.read_parquet(TICK_FILE)
    m1 = pd.read_parquet(M1_FILE)
    
    # Calculate 15-min levels on M1 data
    m1['hh'] = m1['high'].rolling(15).max().shift(1)
    m1['ll'] = m1['low'].rolling(15).min().shift(1)
    
    print(f"Analyzing {len(ticks)} ticks for Price Buffer Entry Optimization...")

    def test_logic(ticks, m1, buffer_dist=0):
        trades = []
        in_pos = False
        pos_type = 0
        sl, tp = 0, 0
        trail_dist = 0.20
        risk = 1.0
        rr = 3.0
        spread = 0.15 # Realistic spread
        
        m1_lookup = m1.set_index('time')[['hh', 'll']].to_dict('index')
        
        for i in range(100, len(ticks)):
            tick = ticks.iloc[i]
            t_key = tick['time'].replace(second=0, microsecond=0)
            if t_key not in m1_lookup: continue
            
            hh = m1_lookup[t_key]['hh']
            ll = m1_lookup[t_key]['ll']
            
            if not in_pos:
                # ENTRY Logic with Buffer
                # Only enter if Price > HH + Buffer (Buy) OR Price < LL - Buffer (Sell)
                is_above = tick['ask'] > (hh + buffer_dist)
                is_below = tick['bid'] < (ll - buffer_dist)
                
                if is_above:
                    in_pos, pos_type, entry_p = True, 1, tick['ask']
                    sl, tp = entry_p - risk, entry_p + (risk * rr)
                elif is_below:
                    in_pos, pos_type, entry_p = True, -1, tick['bid']
                    sl, tp = entry_p + risk, entry_p - (risk * rr)
            else:
                # Trailing and Exit
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

    print("\n--- PRICE BUFFER ENTRY RESEARCH (TICK DATA) ---")
    print(f"{'BUFFER':10} | {'PnL':10} | {'WR':10} | {'TRADES':10}")
    
    for buf in [0.00, 0.05, 0.10, 0.15, 0.20, 0.30]:
        pnl, wr, n = test_logic(ticks, m1, buffer_dist=buf)
        desc = "NO BUFFER" if buf == 0 else f"${buf:.2f} BUF"
        print(f"{desc:10} | ${pnl:8.2f} | {wr:8.2%} | {n:10}")

if __name__ == '__main__':
    run_buffer_research()
