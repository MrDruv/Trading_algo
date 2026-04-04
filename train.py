import pandas as pd
import numpy as np

def superb_momentum_logic(df, i, params):
    if i < 30: return 0
    
    # 1. Indicators
    ema9 = df['close'].ewm(span=9, adjust=False).mean()
    ema21 = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain/loss))) if loss.iloc[i] != 0 else 100
    
    hh = df['high'].iloc[i-16:i-1].max()
    ll = df['low'].iloc[i-16:i-1].min()
    price = df['close'].iloc[i]
    
    # --- ASSET SWITCHING LOGIC ---
    # We detect the asset by the price level (BTC > 10000, Gold < 5000)
    is_gold = price < 5000
    
    if is_gold:
        # GOLD STRATEGY: EMA Pullback (Higher Win Rate)
        # Long: Price pulls back to EMA 9/21 in uptrend
        if ema9.iloc[i] > ema21.iloc[i]:
            if price <= ema9.iloc[i] and rsi.iloc[i] > 40: return 1
        # Short: Price pulls back to EMA 9/21 in downtrend
        if ema9.iloc[i] < ema21.iloc[i]:
            if price >= ema9.iloc[i] and rsi.iloc[i] < 60: return -1
    else:
        # BTC STRATEGY: Momentum Breakout (Superb Version)
        if ema9.iloc[i] > ema21.iloc[i] and price > hh: return 1
        if ema9.iloc[i] < ema21.iloc[i] and price < ll: return -1
            
    return 0
