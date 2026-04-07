import pandas as pd
import numpy as np
import os

def run_time_research():
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
    
    print(f"Analyzing {len(ticks)} ticks against M1 levels...")

    def test_logic(ticks, m1, hold_seconds=0):
        trades = []
        in_pos = False
        pos_type = 0
        sl, tp = 0, 0
        trail_dist = 0.20
        risk = 1.0
        rr = 3.0
        spread = 0.15
        
        # Merge levels into ticks based on time (approximate to nearest minute)
        m1_lookup = m1.set_index('time')[['hh', 'll']].to_dict('index')
        
        hold_start_time = None
        
        for i in range(100, len(ticks)):
            tick = ticks.iloc[i]
            # Get levels for the current minute
            t_key = tick['time'].replace(second=0, microsecond=0)
            if t_key not in m1_lookup: continue
            
            hh = m1_lookup[t_key]['hh']
            ll = m1_lookup[t_key]['ll']
            
            if not in_pos:
                # Signal Detection
                is_above = tick['ask'] > hh
                is_below = tick['bid'] < ll
                
                if is_above or is_below:
                    if hold_seconds == 0:
                        # Immediate Entry
                        in_pos = True
                        pos_type = 1 if is_above else -1
                        entry_p = tick['ask'] if is_above else tick['bid']
                        sl = entry_p - risk if is_above else entry_p + risk
                        tp = entry_p + (risk * rr) if is_above else entry_p - (risk * rr)
                    else:
                        # Time Hold logic
                        if hold_start_time is None:
                            hold_start_time = tick['time']
                        else:
                            duration = (tick['time'] - hold_start_time).total_seconds()
                            if duration >= hold_seconds:
                                in_pos = True
                                pos_type = 1 if is_above else -1
                                entry_p = tick['ask'] if is_above else tick['bid']
                                sl = entry_p - risk if is_above else entry_p + risk
                                tp = entry_p + (risk * rr) if is_above else entry_p - (risk * rr)
                                hold_start_time = None
                else:
                    hold_start_time = None # Reset if price dips back inside
            else:
                # Trailing and Exit (Tick precision)
                price = tick['bid'] if pos_type == 1 else tick['ask']
                
                # Trail
                if pos_type == 1:
                    new_sl = price - trail_dist
                    if new_sl > sl: sl = new_sl
                else:
                    new_sl = price + trail_dist
                    if new_sl < sl: sl = new_sl
                
                # Check Exit
                if pos_type == 1:
                    if tick['bid'] <= sl: trades.append(sl - entry_p); in_pos = False
                    elif tick['bid'] >= tp: trades.append(tp - entry_p); in_pos = False
                else:
                    if tick['ask'] >= sl: trades.append(entry_p - sl); in_pos = False
                    elif tick['ask'] <= tp: trades.append(entry_p - tp); in_pos = False
                    
        if not trades: return 0, 0, 0
        return sum(trades)*10, len([t for t in trades if t > 0])/len(trades), len(trades)

    print("\n--- TIME CONFIRMATION RESEARCH (TICK DATA) ---")
    
    for hold in [0, 5, 10, 15, 30]:
        pnl, wr, n = test_logic(ticks, m1, hold_seconds=hold)
        desc = "IMMEDIATE" if hold == 0 else f"{hold}s HOLD"
        print(f"{desc:10} | PnL: ${pnl:,.2f} | WR: {wr:.2%} | Trades: {n}")

if __name__ == '__main__':
    run_time_research()
