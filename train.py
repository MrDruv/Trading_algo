import pandas as pd
import numpy as np

def superb_momentum_logic(df_m1, df_m5, i, params):
    """
    V7.2 UNIFIED ENGINE: 5-min Structural Breakout for all assets.
    The research-backed champion for both BTC and Gold.
    """
    if i < 15: return 0
    
    price = df_m1['close'].iloc[i]
    
    # 1. Unified 5-min Structural Range
    # (Checking the High/Low of the previous 5 M1 candles)
    hh = df_m1['high'].iloc[i-6:i-1].max()
    ll = df_m1['low'].iloc[i-6:i-1].min()
    
    # 2. Breakout Execution
    if price > hh:
        return 1 # Bullish Breakout
    if price < ll:
        return -1 # Bearish Breakout
            
    return 0
