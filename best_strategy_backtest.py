import pandas as pd
import numpy as np

def run_best_strategy_backtest():
    # -----------------------------------------------------------------------
    # 1. BTCUSD: 5-Minute Breakout (Research Winner)
    # -----------------------------------------------------------------------
    print("\n--- ANALYZING BTCUSD: 5-MIN BREAKOUT ---")
    df_btc = pd.read_parquet('btcusd_30d_m1.parquet')
    
    trades_btc = []
    in_pos = False
    pos_type = 0
    entry_p, sl = 0, 0
    sl_pts, tr_pts = 15.0, 5.0
    
    for i in range(15, len(df_btc)):
        row = df_btc.iloc[i]
        if not in_pos:
            # 5-min Range
            hh = df_btc['high'].iloc[i-6:i-1].max()
            ll = df_btc['low'].iloc[i-6:i-1].min()
            
            if row['close'] > hh:
                in_pos, pos_type, entry_p = True, 1, row['close']
                sl = entry_p - sl_pts
            elif row['close'] < ll:
                in_pos, pos_type, entry_p = True, -1, row['close']
                sl = entry_p + sl_pts
        else:
            # Ghost Trail
            if pos_type == 1:
                new_sl = row['close'] - tr_pts
                if new_sl > sl: sl = new_sl
                if row['low'] <= sl: trades_btc.append(sl - entry_p); in_pos = False
            else:
                new_sl = row['close'] + tr_pts
                if sl == 0 or new_sl < sl: sl = new_sl
                if row['high'] >= sl: trades_btc.append(entry_p - sl); in_pos = False
                
    wr_btc = len([t for t in trades_btc if t > 0]) / len(trades_btc)
    print(f"Win Rate: {wr_btc:.1%} | Total Trades: {len(trades_btc)} | Profit: {sum(trades_btc):.2f}")

    # -----------------------------------------------------------------------
    # 2. XAUUSD: EMA Pullback (Institutional Gold Specialist)
    # -----------------------------------------------------------------------
    print("\n--- ANALYZING XAUUSD: EMA PULLBACK ---")
    df_gold = pd.read_parquet('xauusd_30d_m1.parquet')
    
    # Gold Specific Indicators
    df_gold['ema9'] = df_gold['close'].ewm(span=9, adjust=False).mean()
    df_gold['ema21'] = df_gold['close'].ewm(span=21, adjust=False).mean()
    
    trades_gold = []
    in_pos = False
    pos_type = 0
    entry_p, sl = 0, 0
    sl_pts, tr_pts = 0.50, 0.20 # Gold points (0.01 = 1pt)
    
    for i in range(25, len(df_gold)):
        row = df_gold.iloc[i]
        if not in_pos:
            # Pullback Logic: Trend is strong + Touch EMA
            bullish_trend = row['ema9'] > row['ema21']
            bearish_trend = row['ema9'] < row['ema21']
            
            if bullish_trend and row['low'] <= row['ema9'] and row['close'] > row['ema9']:
                in_pos, pos_type, entry_p = True, 1, row['close']
                sl = entry_p - sl_pts
            elif bearish_trend and row['high'] >= row['ema9'] and row['close'] < row['ema9']:
                in_pos, pos_type, entry_p = True, -1, row['close']
                sl = entry_p + sl_pts
        else:
            # Ghost Trail
            if pos_type == 1:
                new_sl = row['close'] - tr_pts
                if new_sl > sl: sl = new_sl
                if row['low'] <= sl: trades_gold.append(sl - entry_p); in_pos = False
            else:
                new_sl = row['close'] + tr_pts
                if sl == 0 or new_sl < sl: sl = new_sl
                if row['high'] >= sl: trades_gold.append(entry_p - sl); in_pos = False
                
    wr_gold = len([t for t in trades_gold if t > 0]) / len(trades_gold)
    print(f"Win Rate: {wr_gold:.1%} | Total Trades: {len(trades_gold)} | Profit: {sum(trades_gold):.2f}")

if __name__ == "__main__":
    run_best_strategy_backtest()
