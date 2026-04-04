import pandas as pd
import numpy as np

def run_gold_comparison():
    df = pd.read_parquet('gold_research.parquet')
    print(f"Analyzing {len(df)} bars of Gold M1 data...")
    
    # 1. PRE-CALCULATE INDICATORS
    # EMA
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain/loss)))
    
    # Range
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)

    def backtest(logic_func):
        trades = []
        # Simple backtest: SL 50 pts ($0.50), No TP, 20 pt trail
        sl_pts = 0.50
        tr_pts = 0.20
        
        in_pos = False
        pos_type = 0
        entry_price = 0
        sl = 0
        
        for i in range(200, len(df)):
            row = df.iloc[i]
            if not in_pos:
                sig = logic_func(df, i)
                if sig != 0:
                    in_pos, pos_type, entry_price = True, sig, row['open']
                    sl = entry_price - sl_pts if sig == 1 else entry_price + sl_pts
            else:
                # Trailing
                if pos_type == 1:
                    if row['close'] - entry_price >= tr_pts:
                        new_sl = row['close'] - tr_pts
                        if new_sl > sl: sl = new_sl
                    if row['low'] <= sl: 
                        trades.append(sl - entry_price)
                        in_pos = False
                else:
                    if entry_price - row['close'] >= tr_pts:
                        new_sl = row['close'] + tr_pts
                        if sl == 0 or new_sl < sl: sl = new_sl
                    if row['high'] >= sl:
                        trades.append(entry_price - sl)
                        in_pos = False
        
        if not trades: return 0, 0, 0
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        profit_factor = sum([t for t in trades if t > 0]) / abs(sum([t for t in trades if t < 0])) if any(t < 0 for t in trades) else 99
        return win_rate, profit_factor, len(trades)

    # LOGIC A: EMA 9/21 + 15m Breakout (Current)
    def logic_a(d, i):
        r = d.iloc[i]
        if d.ema9.iloc[i] > d.ema21.iloc[i] and r.close > r.hh: return 1
        if d.ema9.iloc[i] < d.ema21.iloc[i] and r.close < r.ll: return -1
        return 0

    # LOGIC B: MACD Cross + EMA 200 (Trend Following)
    def logic_b(d, i):
        curr = d.iloc[i]; prev = d.iloc[i-1]
        if curr.close > curr.ema200 and prev.macd < prev.signal and curr.macd > curr.signal: return 1
        if curr.close < curr.ema200 and prev.macd > prev.signal and curr.macd < curr.signal: return -1
        return 0

    # LOGIC C: RSI Extreme Reversal (Scalping Pullbacks)
    def logic_c(d, i):
        r = d.iloc[i]
        if r.ema9 > r.ema21 and r.rsi < 35: return 1 # Dip buy in uptrend
        if r.ema9 < r.ema21 and r.rsi > 65: return -1 # Peak sell in downtrend
        return 0

    print("\n--- RESULTS ---")
    for name, logic in [("Momentum (Current)", logic_a), ("MACD Trend", logic_b), ("RSI Dip/Peak", logic_c)]:
        wr, pf, n = backtest(logic)
        print(f"{name}: Win Rate: {wr:.1%}, Profit Factor: {pf:.2f}, Trades: {n}")

if __name__ == "__main__":
    run_gold_comparison()
