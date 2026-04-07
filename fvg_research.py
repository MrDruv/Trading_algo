import pandas as pd
import numpy as np
import math
import os

def run_fvg_research():
    DATA_FILE = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading", "XAUUSD+_m1_scalping_data.parquet")
    if not os.path.exists(DATA_FILE):
        print(f"Data file not found at {DATA_FILE}")
        return
    df = pd.read_parquet(DATA_FILE)
    print(f"Analyzing {len(df)} bars of Gold M1 data with FVG Confluence...")
    
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
    
    # FVG Detection
    # Bullish FVG: Low of candle[i] > High of candle[i-2]
    df['fvg_bull'] = (df['low'] > df['high'].shift(2))
    # Bearish FVG: High of candle[i] < Low of candle[i-2]
    df['fvg_bear'] = (df['high'] < df['low'].shift(2))

    def test_logic(df, params):
        trades = []
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl, tp = 0, 0
        risk = params['risk']
        rr = params['rr']
        trail = params['trail']
        use_fvg = params['use_fvg']
        
        last_trade_time = None

        for i in range(50, len(df)):
            row = df.iloc[i]
            
            # 1-trade-per-candle / minute cooldown logic
            if last_trade_time is not None and row['time'] == last_trade_time:
                continue

            if not in_pos:
                # Basic Breakout + ADX
                bull_break = row['close'] > row['hh'] and row['adx'] > 25
                bear_break = row['close'] < row['ll'] and row['adx'] > 25
                
                # FVG Confluence (Look back 3 candles for a gap)
                fvg_ok_bull = any(df['fvg_bull'].iloc[i-2:i+1]) if use_fvg else True
                fvg_ok_bear = any(df['fvg_bear'].iloc[i-2:i+1]) if use_fvg else True

                if bull_break and fvg_ok_bull:
                    in_pos, pos_type, entry_price = True, 1, row['open'] + 0.10
                    sl, tp = entry_price - risk, entry_price + (risk * rr)
                    last_trade_time = row['time']
                elif bear_break and fvg_ok_bear:
                    in_pos, pos_type, entry_price = True, -1, row['open'] - 0.10
                    sl, tp = entry_price + risk, entry_price - (risk * rr)
                    last_trade_time = row['time']
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
        pnl = sum(trades) * 10 # 0.1 lot scaling ($10 per dollar move)
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        return pnl, win_rate, len(trades)

    print("\n--- PERFORMANCE COMPARISON (GOLD 0.1 LOT) ---")
    
    # Current Strategy
    pnl1, wr1, n1 = test_logic(df, {'risk': 1.0, 'rr': 3.0, 'trail': 0.20, 'use_fvg': False})
    print(f"CURRENT (No FVG): PnL: ${pnl1:,.2f} | WR: {wr1:.2%} | Trades: {n1}")
    
    # FVG Enhanced Strategy
    pnl2, wr2, n2 = test_logic(df, {'risk': 1.0, 'rr': 3.0, 'trail': 0.20, 'use_fvg': True})
    print(f"ENHANCED (With FVG): PnL: ${pnl2:,.2f} | WR: {wr2:.2%} | Trades: {n2}")
    
    improvement = ((wr2 - wr1) / wr1) * 100 if wr1 > 0 else 0
    print(f"\nWin Rate Improvement: {improvement:+.2f}%")

if __name__ == '__main__':
    run_fvg_research()
