import pandas as pd
import numpy as np

def run_pdarray_research():
    print("Loading 30 days of BTC M1 data for PD-Array Research...")
    df = pd.read_parquet('btcusd_30d_m1.parquet')
    
    trades = []
    in_pos = False
    pos_type = 0
    entry_p, sl = 0, 0
    
    # Risk settings for larger moves
    sl_pts, tr_pts = 25.0, 10.0
    
    for i in range(65, len(df)):
        row = df.iloc[i]
        
        if not in_pos:
            # 1. Dealing Range (60 mins)
            r_hi = df['high'].iloc[i-60:i-1].max()
            r_lo = df['low'].iloc[i-60:i-1].min()
            eq = (r_hi + r_lo) / 2
            
            # 2. PD Arrays (FVG)
            fvg_bull = df['low'].iloc[i] > df['high'].iloc[i-2]
            fvg_bear = df['high'].iloc[i] < df['low'].iloc[i-2]
            
            # Entry Logic
            if row['close'] < eq and fvg_bull:
                in_pos, pos_type, entry_p = True, 1, row['close']
                sl = entry_p - sl_pts
            elif row['close'] > eq and fvg_bear:
                in_pos, pos_type, entry_p = True, -1, row['close']
                sl = entry_p + sl_pts
        else:
            # Ghost Trail
            if pos_type == 1:
                new_sl = row['close'] - tr_pts
                if new_sl > sl: sl = new_sl
                if row['low'] <= sl: trades.append(sl - entry_p); in_pos = False
            else:
                new_sl = row['close'] + tr_pts
                if sl == 0 or new_sl < sl: sl = new_sl
                if row['high'] >= sl: trades.append(entry_p - sl); in_pos = False
                
    if not trades:
        print("No trades triggered.")
        return
        
    wr = len([t for t in trades if t > 0]) / len(trades)
    print("\n--- PD-ARRAY RESEARCH RESULTS (30 DAYS) ---")
    print(f"Win Rate: {wr:.1%}")
    print(f"Total Trades: {len(trades)}")
    print(f"Total Points Profit: {sum(trades):.2f}")
    print(f"Avg Points per Trade: {sum(trades)/len(trades):.2f}")

if __name__ == "__main__":
    run_pdarray_research()
