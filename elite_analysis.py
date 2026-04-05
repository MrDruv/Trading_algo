import pandas as pd
import numpy as np

def run_elite_analysis(filename, symbol_name):
    print(f"\n--- ANALYZING ELITE STRATEGY: {symbol_name} ---")
    df = pd.read_parquet(filename)
    
    # 1. Indicator Calculations
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
    df['rsi7'] = 100 - (100 / (1 + (gain/loss)))
    
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr14'] = df['tr'].rolling(14).mean()
    df['vol_ma20'] = df['tick_volume'].rolling(20).mean()
    
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_up'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_low'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    df['tp_p'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (df['tp_p'] * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()
    df['ema_slope'] = df['ema50'].diff(5).abs()

    # Pattern Detectors
    def is_bull_pattern(i):
        curr, prev = df.iloc[i], df.iloc[i-1]
        engulfing = (prev.close < prev.open) and (curr.close > curr.open) and (curr.close > prev.open) and (curr.open < prev.close)
        pinbar = (abs(curr.close - curr.open) < 0.3 * (curr.high - curr.low)) and ((min(curr.open, curr.close) - curr.low) > 0.6 * (curr.high - curr.low))
        return engulfing or pinbar

    def is_bear_pattern(i):
        curr, prev = df.iloc[i], df.iloc[i-1]
        engulfing = (prev.close > prev.open) and (curr.close < curr.open) and (curr.close < prev.open) and (curr.open > prev.close)
        pinbar = (abs(curr.close - curr.open) < 0.3 * (curr.high - curr.low)) and ((curr.high - max(curr.open, curr.close)) > 0.6 * (curr.high - curr.low))
        return engulfing or pinbar

    # 2. Backtest engine
    trades = []
    in_pos = False
    pos_type = 0
    entry_p, sl, tp = 0, 0, 0
    balance = 10000.0
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        if not in_pos:
            # TRENDING FILTER
            uptrend = row.ema21 > row.ema50 > row.ema200
            downtrend = row.ema21 < row.ema50 < row.ema200
            ranging = row.ema_slope < (row.close * 0.0003)
            
            sig = 0
            # Strategy A: Pullback
            if uptrend and row.low <= row.ema21 and row.close > row.ema21:
                if is_bull_pattern(i) and 40 <= row.rsi7 <= 60 and row.tick_volume > (row.vol_ma20 * 1.3) and row.close > row.vwap:
                    sig, sl_d = 1, abs(row.close - (row.ema50 - row.atr14 * 0.3))
            elif downtrend and row.high >= row.ema21 and row.close < row.ema21:
                if is_bear_pattern(i) and 40 <= row.rsi7 <= 60 and row.tick_volume > (row.vol_ma20 * 1.3) and row.close < row.vwap:
                    sig, sl_d = -1, abs(row.close - (row.ema50 + row.atr14 * 0.3))
            
            # Strategy B: Mean Reversion
            elif ranging:
                if row.low <= row.bb_low and row.rsi7 < 30 and row.close > row.open and row.tick_volume > (row.vol_ma20 * 1.2):
                    sig, sl_d = 1, row.atr14
                elif row.high >= row.bb_up and row.rsi7 > 70 and row.close < row.open and row.tick_volume > (row.vol_ma20 * 1.2):
                    sig, sl_d = -1, row.atr14

            if sig != 0:
                in_pos, pos_type, entry_p = True, sig, row.close
                # 1% risk lot sizing
                lots = (balance * 0.01) / sl_d if sl_d > 0 else 0
                lots = min(lots, 0.5)
                sl = entry_p - (pos_type * sl_d)
                tp = entry_p + (pos_type * sl_d * 1.2) if not ranging else row.bb_mid

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
        res = pd.Series(trades)
        wr = len(res[res > 0]) / len(res)
        pf = res[res > 0].sum() / abs(res[res < 0].sum()) if len(res[res < 0]) > 0 else 99
        print(f"Win Rate: {wr:.1%}")
        print(f"Profit Factor: {pf:.2f}")
        print(f"Total Trades: {len(trades)}")
        print(f"Final Balance: ${balance:.2f}")
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    run_elite_analysis('btcusd_m5_large.parquet', 'BTCUSD')
    run_elite_analysis('ethusd_m5_large.parquet', 'ETHUSD')
