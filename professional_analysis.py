import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime

TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOL = "BTCUSD"

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_vwap(df):
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()

def analyze_scalp():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("MT5 Init Failed")
        return

    # 1. Fetch 5-Minute Data (Trend)
    rates_5m = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 100)
    df_5m = pd.DataFrame(rates_5m)
    df_5m['ema21'] = df_5m['close'].ewm(span=21, adjust=False).mean()
    
    current_price = df_5m['close'].iloc[-1]
    ema21_5m = df_5m['ema21'].iloc[-1]
    trend_5m = "BULLISH" if current_price > ema21_5m else "BEARISH"

    # 2. Fetch 1-Minute Data (Entry)
    rates_1m = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 200)
    df_1m = pd.DataFrame(rates_1m)
    df_1m['ema9'] = df_1m['close'].ewm(span=9, adjust=False).mean()
    df_1m['ema21'] = df_1m['close'].ewm(span=21, adjust=False).mean()
    df_1m['rsi'] = calculate_rsi(df_1m['close'])
    df_1m['vwap'] = calculate_vwap(df_1m)

    # Current 1m values
    c_1m = df_1m.iloc[-1]
    p_1m = df_1m.iloc[-2] # Previous candle for confirmation
    
    ema9 = c_1m['ema9']
    ema21 = c_1m['ema21']
    rsi = c_1m['rsi']
    vwap = c_1m['vwap']
    
    # Confirmation Candle Logic
    bullish_confirm = c_1m['close'] > c_1m['open']
    bearish_confirm = c_1m['close'] < c_1m['open']
    
    # Volume check (Current volume > Avg of last 20)
    avg_vol = df_1m['tick_volume'].tail(20).mean()
    vol_ok = c_1m['tick_volume'] > avg_vol * 0.8 # Sufficient volume

    print(f"--- Professional BTC Scalper Analysis ---")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"5m Trend: {trend_5m} (Price: {current_price:.2f} | EMA21: {ema21_5m:.2f})")
    print(f"1m RSI: {rsi:.2f} | EMA9: {ema9:.2f} | EMA21: {ema21:.2f} | VWAP: {vwap:.2f}")
    
    setup = "No trade setup."
    
    # LONG Check
    if trend_5m == "BULLISH":
        if ema9 > ema21:
            # Pullback to EMA9 or VWAP (within $20 range)
            pullback = abs(current_price - ema9) < 20 or abs(current_price - vwap) < 20
            if pullback and 40 <= rsi <= 60 and bullish_confirm and vol_ok:
                sl = current_price * 0.9975 # 0.25% SL
                tp = current_price * 1.0040 # 0.4% TP
                setup = f"LONG | Confidence: High | Reason: Pullback to EMA9/VWAP in Bullish Trend | Entry: {current_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"
    
    # SHORT Check
    elif trend_5m == "BEARISH":
        if ema9 < ema21:
            # Pullback to EMA9 or VWAP
            pullback = abs(current_price - ema9) < 20 or abs(current_price - vwap) < 20
            if pullback and 40 <= rsi <= 60 and bearish_confirm and vol_ok:
                sl = current_price * 1.0025 # 0.25% SL
                tp = current_price * 0.9960 # 0.4% TP
                setup = f"SHORT | Confidence: High | Reason: Pullback to EMA9/VWAP in Bearish Trend | Entry: {current_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"

    print(f"\nRESULT: {setup}")
    mt5.shutdown()

if __name__ == "__main__":
    analyze_scalp()
