import pandas as pd
import numpy as np

def run_session_research():
    print("Analyzing 1:1 RR Strategy during London & NY Sessions (08:00-21:00 UTC)...")
    
    def analyze(filename, is_btc):
        df = pd.read_parquet(filename)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Risk settings
        sl_pts = 50.0 if is_btc else 2.0
        
        trades = []
        # Filter for London + NY Session (08:00 to 21:00 UTC)
        df_session = df[(df['time'].dt.hour >= 8) & (df['time'].dt.hour < 21)]
        
        # Find signals in the session
        for i in range(15, len(df_session), 5):
            row = df_session.iloc[i]
            # 5-min Breakout
            hh = df_session['high'].iloc[i-6:i-1].max()
            ll = df_session['low'].iloc[i-6:i-1].min()
            
            sig = 0
            if row['close'] > hh: sig = 1
            elif row['close'] < ll: sig = -1
            
            if sig != 0:
                # 1:1 Simulation
                target = row['close'] + (sig * sl_pts)
                stop = row['close'] - (sig * sl_pts)
                
                # Check outcome in next 120 mins
                future = df_session['close'].iloc[i+1 : i+121]
                if len(future) < 10: continue
                
                win = False
                for p in future:
                    if sig == 1:
                        if p >= target: win = True; break
                        if p <= stop: break
                    else:
                        if p <= target: win = True; break
                        if p >= stop: break
                trades.append(1 if win else -1)
        
        if not trades: return 0, 0
        wr = len([t for t in trades if t > 0]) / len(trades)
        return wr, len(trades)

    btc_wr, btc_count = analyze('btcusd_30d_m1.parquet', True)
    gold_wr, gold_count = analyze('xauusd_30d_m1.parquet', False)
    
    print(f"\n--- SESSION RESULTS (08:00-21:00 UTC) ---")
    print(f"BTCUSD: Win Rate: {btc_wr:.1%} | Total Trades: {btc_count}")
    print(f"XAUUSD: Win Rate: {gold_wr:.1%} | Total Trades: {gold_count}")

if __name__ == "__main__":
    run_session_research()
