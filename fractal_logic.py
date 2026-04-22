import pandas as pd
import numpy as np

def identify_fractals(df):
    df = df.copy()
    df['fractal_h'] = np.nan
    df['fractal_l'] = np.nan
    highs = df['high'].values
    lows = df['low'].values
    for i in range(2, len(df) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            df.loc[df.index[i], 'fractal_h'] = highs[i]
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            df.loc[df.index[i], 'fractal_l'] = lows[i]
    df['last_f_h'] = df['fractal_h'].ffill()
    df['last_f_l'] = df['fractal_l'].ffill()
    return df

def calculate_indicators(df_1m):
    df_1m = identify_fractals(df_1m)
    df_1m['ema_50'] = df_1m['close'].ewm(span=50, adjust=False).mean()
    return df_1m

def check_fractal_signal(df_1m):
    if len(df_1m) < 10: return 0, 0, 0, 0
    curr = df_1m.iloc[-1]
    
    # MACHINE GUN AGGRESSIVE: If price is BEYOND the level and trend is ALIGNED -> FIRE
    # No "fresh cross" needed, the bot's own 'if positions' check will prevent double trading.
    
    # LONG: Above Fractal High + Above EMA 50
    if curr['close'] > curr['last_f_h'] and curr['close'] > curr['ema_50']:
        entry = curr['close']
        sl = curr['last_f_l']
        risk = entry - sl
        if 0.2 < risk < 10.0: # Even wider risk tolerance
            tp = entry + (risk * 1.5)
            return 1, entry, sl, tp

    # SHORT: Below Fractal Low + Below EMA 50
    elif curr['close'] < curr['last_f_l'] and curr['close'] < curr['ema_50']:
        entry = curr['close']
        sl = curr['last_f_h']
        risk = sl - entry
        if 0.2 < risk < 10.0:
            tp = entry - (risk * 1.5)
            return -1, entry, sl, tp

    return 0, 0, 0, 0
