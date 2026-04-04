import pandas as pd
import numpy as np

def superb_momentum_logic(df, i, params):
    if i < 30: return 0

    # 1. FASTER EMA Momentum (5/13) for quicker reaction
    ema_fast = df['close'].ewm(span=5, adjust=False).mean()
    ema_slow = df['close'].ewm(span=13, adjust=False).mean()

    # 2. FVG Detection (3 candle imbalance)
    fvg_bullish = df['low'].iloc[i-2] > df['high'].iloc[i]
    fvg_bearish = df['high'].iloc[i-2] < df['low'].iloc[i]

    # 3. 15-min Breakout Levels (Strong barrier)
    hh = df['high'].iloc[i-16:i-1].max()
    ll = df['low'].iloc[i-16:i-1].min()

    price = df['close'].iloc[i]

    # LOGIC:
    # BUY if trend is UP (EMA 5 > 13) AND (Strong Breakout OR FVG)
    if ema_fast.iloc[i] > ema_slow.iloc[i]:
        if price > hh or fvg_bullish:
            return 1

    # SELL if trend is DOWN (EMA 5 < 13) AND (Strong Breakout OR FVG)
    if ema_fast.iloc[i] < ema_slow.iloc[i]:
        if price < ll or fvg_bearish:
            return -1

    return 0
