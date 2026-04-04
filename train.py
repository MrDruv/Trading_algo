import pandas as pd
import numpy as np

def superb_momentum_logic(df, i, params):
    if i < 30: return 0
    
    # 1. EMA Momentum
    ema9 = df['close'].ewm(span=9, adjust=False).mean()
    ema21 = df['close'].ewm(span=21, adjust=False).mean()
    
    # 2. FVG Detection (3 candle imbalance)
    fvg_bullish = df['low'].iloc[i-2] > df['high'].iloc[i]
    fvg_bearish = df['high'].iloc[i-2] < df['low'].iloc[i]
    
    # 3. 15-min Breakout Levels
    hh = df['high'].iloc[i-16:i-1].max()
    ll = df['low'].iloc[i-16:i-1].min()
    
    price = df['close'].iloc[i]
    
    # EXACT logic that was working superbly:
    # Long: Trend up (EMA) + (FVG or Breakout)
    if ema9.iloc[i] > ema21.iloc[i]:
        if fvg_bullish or price > hh:
            return 1
            
    # Short: Trend down (EMA) + (FVG or Breakout)
    if ema9.iloc[i] < ema21.iloc[i]:
        if fvg_bearish or price < ll:
            return -1
            
    return 0
