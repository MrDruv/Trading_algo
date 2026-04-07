import pandas as pd
import numpy as np
import math
import os

def run_fvg_retrace_research():
    DATA_FILE = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading", "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found at {DATA_FILE}")
        return
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing {len(df)} bars of Gold M1 data with 50% FVG Retracement Entry...")
    
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

    def test_logic(df, params):
        trades = []
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl, tp = 0, 0
        risk = params['risk']
        rr = params['rr']
        trail = params['trail']
        
        pending_fvg = None # (Midpoint, SL, TP, expiry_time, type)
        last_trade_time = None

        for i in range(50, len(df)):
            row = df.iloc[i]
            
            if last_trade_time is not None and row['time'] == last_trade_time:
                continue

            if not in_pos:
                # 1. SCAN FOR NEW FVG AFTER BREAKOUT
                bull_break = row['close'] > row['hh'] and row['adx'] > 25
                bear_break = row['close'] < row['ll'] and row['adx'] > 25
                
                # FVG Detection (Current candle i is the 3rd candle)
                # Bullish FVG: Low[i] > High[i-2]
                if bull_break and row['low'] > df['high'].iloc[i-2]:
                    fvg_top = row['low']
                    fvg_bot = df['high'].iloc[i-2]
                    midpoint = (fvg_top + fvg_bot) / 2
                    pending_fvg = {'price': midpoint, 'sl': midpoint - risk, 'tp': midpoint + (risk * rr), 'type': 1, 'expiry': i + 10}
                
                # Bearish FVG: High[i] < Low[i-2]
                elif bear_break and row['high'] < df['low'].iloc[i-2]:
                    fvg_top = df['low'].iloc[i-2]
                    fvg_bot = row['high']
                    midpoint = (fvg_top + fvg_bot) / 2
                    pending_fvg = {'price': midpoint, 'sl': midpoint + risk, 'tp': midpoint - (risk * rr), 'type': -1, 'expiry': i + 10}

                # 2. CHECK FOR RETRACEMENT ENTRY
                if pending_fvg:
                    if pending_fvg['type'] == 1 and row['low'] <= pending_fvg['price']:
                        in_pos, pos_type, entry_price = True, 1, pending_fvg['price']
                        sl, tp = pending_fvg['sl'], pending_fvg['tp']
                        pending_fvg = None
                        last_trade_time = row['time']
                    elif pending_fvg['type'] == -1 and row['high'] >= pending_fvg['price']:
                        in_pos, pos_type, entry_price = True, -1, pending_fvg['price']
                        sl, tp = pending_fvg['sl'], pending_fvg['tp']
                        pending_fvg = None
                        last_trade_time = row['time']
                    elif i > pending_fvg['expiry']:
                        pending_fvg = None
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
    
    # 50% FVG Retrace Strategy
    pnl, wr, n = test_logic(df, {'risk': 1.0, 'rr': 3.0, 'trail': 0.20})
    print(f"50% FVG RETRACE: PnL: ${pnl:,.2f} | WR: {wr:.2%} | Trades: {n}")

if __name__ == '__main__':
    run_fvg_retrace_research()
