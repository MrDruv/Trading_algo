import pandas as pd
import MetaTrader5 as mt5

TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

def analyze_volatility():
    if not mt5.initialize(path=TERMINAL_PATH): return
    rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M1, 0, 500)
    df = pd.DataFrame(rates)
    
    # Calculate ATR (Approximate)
    df['range'] = df['high'] - df['low']
    atr = df['range'].rolling(14).mean().iloc[-1]
    
    # Calculate Trend (200 EMA)
    ema200 = df['close'].ewm(span=200).mean().iloc[-1]
    price = df['close'].iloc[-1]
    
    print(f"Current BTC Price: {price}")
    print(f"1-Min ATR (Volatility): ${atr:.2f}")
    print(f"Trend (Price vs EMA200): {'BULLISH' if price > ema200 else 'BEARISH'}")
    mt5.shutdown()

if __name__ == "__main__":
    analyze_volatility()
