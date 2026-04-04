import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timezone

TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOL = "BTCUSD"

def analyze_elite_scalp():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("MT5 Init Failed")
        return

    # 1. HTF Dealing Range (1H) - Last 24-48 hours
    rates_1h = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 48)
    df_1h = pd.DataFrame(rates_1h)
    swing_high = df_1h['high'].max()
    swing_low = df_1h['low'].min()
    equilibrium = (swing_high + swing_low) / 2
    
    current_price = df_1h['close'].iloc[-1]
    htf_bias = "PREMIUM (Short Only)" if current_price > equilibrium else "DISCOUNT (Long Only)"

    # 2. Liquidity Points (15M)
    rates_15m = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 100)
    df_15m = pd.DataFrame(rates_15m)
    pdh = df_1h['high'].iloc[-24:].max() # Prev Day High approx
    pdl = df_1h['low'].iloc[-24:].min() # Prev Day Low approx
    
    # 3. Session Check (UTC)
    # London Open: 07:00-10:00 | NY Open: 13:00-16:00
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    is_killzone = (7 <= hour < 10) or (13 <= hour < 16)
    session_str = "NY Afternoon (Low Prob)"
    if 7 <= hour < 10: session_str = "London Killzone"
    if 13 <= hour < 16: session_str = "NY Killzone"

    # 4. LTF Execution (1M) - Looking for Sweep + BOS + FVG
    rates_1m = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 60)
    df_1m = pd.DataFrame(rates_1m)
    
    # Check for recent sweep (last 15 mins)
    recent_high = df_1m['high'].iloc[-15:-1].max()
    recent_low = df_1m['low'].iloc[-15:-1].min()
    
    sweep_high = df_1m['high'].iloc[-1] > recent_high
    sweep_low = df_1m['low'].iloc[-1] < recent_low
    
    # Check for FVG (3 candle pattern)
    # Bearish FVG: Candle 1 Low > Candle 3 High
    fvg_bearish = df_1m['low'].iloc[-3] > df_1m['high'].iloc[-1]
    # Bullish FVG: Candle 1 High < Candle 3 Low
    fvg_bullish = df_1m['high'].iloc[-3] < df_1m['low'].iloc[-1]

    # Displacement Check (Body size > 2x average body of last 10)
    df_1m['body'] = (df_1m['close'] - df_1m['open']).abs()
    avg_body = df_1m['body'].iloc[-11:-1].mean()
    displacement = df_1m['body'].iloc[-1] > (avg_body * 1.5)

    print(f"--- ELITE LIQUIDITY ANALYSIS ---")
    print(f"Time (UTC): {now_utc.strftime('%H:%M:%S')} | Session: {session_str}")
    print(f"HTF Range: {swing_low:.2f} - {swing_high:.2f} | Eq: {equilibrium:.2f}")
    print(f"Current Price: {current_price:.2f} | Bias: {htf_bias}")
    print(f"Recent Sweep: High={sweep_high}, Low={sweep_low}")
    print(f"Displacement: {displacement} | FVG: Bull={fvg_bullish}, Bear={fvg_bearish}")

    # FINAL MODEL EXECUTION
    if not is_killzone:
        print("\nRESULT: NO TRADE (no edge present - outside Killzone)")
    else:
        # SHORT SETUP
        if htf_bias == "PREMIUM (Short Only)" and sweep_high and displacement and fvg_bearish:
            sl = df_1m['high'].iloc[-1] + 5.0
            entry = df_1m['low'].iloc[-3] # Entry at FVG top
            tp1 = current_price - 50.0
            print(f"\nRESULT: SHORT | Confidence: High")
            print(f"Setup: Liquidity sweep + Displacement + FVG Entry")
            print(f"Entry: {entry:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f}")
        
        # LONG SETUP
        elif htf_bias == "DISCOUNT (Long Only)" and sweep_low and displacement and fvg_bullish:
            sl = df_1m['low'].iloc[-1] - 5.0
            entry = df_1m['high'].iloc[-3] # Entry at FVG bottom
            tp1 = current_price + 50.0
            print(f"\nRESULT: LONG | Confidence: High")
            print(f"Setup: Liquidity sweep + Displacement + FVG Entry")
            print(f"Entry: {entry:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f}")
        
        else:
            print("\nRESULT: NO TRADE (no edge present)")

    mt5.shutdown()

if __name__ == "__main__":
    analyze_elite_scalp()
