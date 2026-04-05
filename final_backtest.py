import pandas as pd
import numpy as np

def run_hierarchical_backtest(m5_file, m15_file, symbol_name):
    print(f"\n--- Hierarchical Backtest: {symbol_name} ---")
    df_m5 = pd.read_parquet(m5_file)
    df_m15 = pd.read_parquet(m15_file)
    
    # 1. PRE-CALCULATIONS
    # M15 Bias (EMA 200)
    df_m15['ema200_bias'] = df_m15['close'].ewm(span=200, adjust=False).mean()
    df_m15['bullish_bias'] = df_m15['close'] > df_m15['ema200_bias']
    df_m15['bearish_bias'] = df_m15['close'] < df_m15['ema200_bias']
    
    # M5 Indicators
    df_m5['ema8'] = df_m5['close'].ewm(span=8, adjust=False).mean()
    df_m5['ema21'] = df_m5['close'].ewm(span=21, adjust=False).mean()
    df_m5['ema50'] = df_m5['close'].ewm(span=50, adjust=False).mean()
    
    delta = df_m5['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
    df_m5['rsi7'] = 100 - (100 / (1 + (gain/loss)))
    
    df_m5['tr'] = np.maximum(df_m5['high'] - df_m5['low'], np.maximum(abs(df_m5['high'] - df_m5['close'].shift(1)), abs(df_m5['low'] - df_m5['close'].shift(1))))
    df_m5['atr14'] = df_m5['tr'].rolling(14).mean()
    df_m5['vol_ma20'] = df_m5['tick_volume'].rolling(20).mean()
    
    df_m5['tp_p'] = (df_m5['high'] + df_m5['low'] + df_m5['close']) / 3
    df_m5['vwap'] = (df_m5['tp_p'] * df_m5['tick_volume']).cumsum() / df_m5['tick_volume'].cumsum()

    # Pattern Detectors
    def is_bull_pattern(i):
        curr, prev = df_m5.iloc[i], df_m5.iloc[i-1]
        engulfing = (prev.close < prev.open) and (curr.close > curr.open) and (curr.close > prev.open)
        pinbar = (abs(curr.close - curr.open) < 0.3 * (curr.high - curr.low)) and ((min(curr.open, curr.close) - curr.low) > 0.6 * (curr.high - curr.low))
        return engulfing or pinbar

    def is_bear_pattern(i):
        curr, prev = df_m5.iloc[i], df_m5.iloc[i-1]
        engulfing = (prev.close > prev.open) and (curr.close < curr.open) and (curr.close < prev.open)
        pinbar = (abs(curr.close - curr.open) < 0.3 * (curr.high - curr.low)) and ((curr.high - max(curr.open, curr.close)) > 0.6 * (curr.high - curr.low))
        return engulfing or pinbar

    # 2. SYNC M15 BIAS TO M5
    df_m5['time_dt'] = pd.to_datetime(df_m5['time'], unit='s')
    df_m15['time_dt'] = pd.to_datetime(df_m15['time'], unit='s')
    df = pd.merge_asof(df_m5.sort_values('time_dt'), 
                       df_m15[['time_dt', 'bullish_bias', 'bearish_bias']].sort_values('time_dt'), 
                       on='time_dt', direction='backward')

    # 3. BACKTEST LOOP
    balance = 10000.0
    trades = []
    in_pos = False
    pos_type = 0
    entry_p, sl, tp, lots = 0, 0, 0, 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        
        if not in_pos:
            # HIERARCHICAL FLOW
            # 1. M15 bias clear?
            bias_bull = row['bullish_bias']
            bias_bear = row['bearish_bias']
            
            # 2. EMA Stack? (8 > 21 > 50)
            stack_bull = row.ema8 > row.ema21 > row.ema50
            stack_bear = row.ema8 < row.ema21 < row.ema50
            
            # 3. Price touched EMA 21?
            touched_21 = row.low <= row.ema21 <= row.high
            
            signal = 0
            if bias_bull and stack_bull and touched_21:
                # 4. Remaining Conditions
                if is_bull_pattern(i) and 40 <= row.rsi7 <= 60 and row.tick_volume > (row.vol_ma20 * 1.3) and row.close > row.vwap:
                    signal = 1
            elif bias_bear and stack_bear and touched_21:
                if is_bear_pattern(i) and 40 <= row.rsi7 <= 60 and row.tick_volume > (row.vol_ma20 * 1.3) and row.close < row.vwap:
                    signal = -1

            if signal != 0:
                in_pos, pos_type, entry_p = True, signal, row.close
                sl_dist = row.atr14
                if sl_dist <= 0: in_pos = False; continue
                
                lots = (balance * 0.01) / sl_dist
                lots = min(lots, 0.5)
                
                sl = entry_p - (pos_type * sl_dist)
                tp = entry_p + (pos_type * sl_dist * 1.5)
        else:
            # Trailing & Exit
            atr = row.atr14
            p_pts = (row.close - entry_p) if pos_type == 1 else (entry_p - row.close)
            if p_pts >= atr * 0.8:
                new_sl = row.close - (pos_type * atr * 0.4)
                if (pos_type == 1 and new_sl > sl) or (pos_type == -1 and new_sl < sl): sl = new_sl
            
            pnl = 0
            if (pos_type == 1 and row.low <= sl) or (pos_type == -1 and row.high >= sl): pnl = (sl - entry_p) * pos_type * lots; in_pos = False
            elif (pos_type == 1 and row.high >= tp) or (pos_type == -1 and row.low <= tp): pnl = (tp - entry_p) * pos_type * lots; in_pos = False
            
            if not in_pos:
                balance += pnl
                trades.append(pnl)

    if trades:
        trades = np.array(trades)
        wr = len(trades[trades > 0]) / len(trades)
        pf = trades[trades > 0].sum() / abs(trades[trades < 0].sum()) if any(t < 0 for t in trades) else 99
        print(f"Trades: {len(trades)} | Win Rate: {wr:.1%} | PF: {pf:.2f} | Final Balance: ${balance:.2f}")
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    run_hierarchical_backtest('btcusd_m5_large.parquet', 'btcusd_m15_large.parquet', 'BTCUSD')
    run_hierarchical_backtest('ethusd_m5_large.parquet', 'ethusd_m15_large.parquet', 'ETHUSD')
