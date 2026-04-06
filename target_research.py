import pandas as pd
import numpy as np

def run_target_research():
    print("Analyzing 30 days of data to find the Optimal Take Profit...")
    
    def analyze_asset(filename, is_btc):
        df = pd.read_parquet(filename)
        sl_pts = 25.0 if is_btc else 0.50
        
        results = []
        for tp_mult in [1.0, 1.5, 2.0, 2.5, 3.0]:
            total_profit = 0
            wins = 0
            count = 0
            
            # Simple simulation of breakout + target
            for i in range(15, len(df), 10):
                hh = df['high'].iloc[i-6:i-1].max()
                if df['close'].iloc[i] > hh:
                    count += 1
                    # Look ahead 60 mins
                    future = df['close'].iloc[i+1 : i+61]
                    if len(future) < 10: continue
                    
                    target = df['close'].iloc[i] + (sl_pts * tp_mult)
                    stop = df['close'].iloc[i] - sl_pts
                    
                    # Did it hit target or stop first?
                    hit_tp = False
                    for p in future:
                        if p >= target: hit_tp = True; break
                        if p <= stop: break
                    
                    if hit_tp:
                        total_profit += (sl_pts * tp_mult)
                        wins += 1
                    else:
                        total_profit -= sl_pts
            
            results.append({'mult': tp_mult, 'pnl': total_profit, 'wr': wins/count if count > 0 else 0})
            
        best = max(results, key=lambda x: x['pnl'])
        print(f"\n--- BEST TARGET FOR {'BTCUSD' if is_btc else 'XAUUSD'} ---")
        print(f"Optimal TP: {best['mult']}x SL")
        print(f"Win Rate: {best['wr']:.1%}")
        return best

    btc_best = analyze_asset('btcusd_30d_m1.parquet', True)
    gold_best = analyze_asset('xauusd_30d_m1.parquet', False)

if __name__ == "__main__":
    run_target_research()
