import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from train import superb_momentum_logic
from datetime import datetime, timedelta

# Configuration
TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOLS = ["XAUUSD+", "BTCUSD"]
DAYS_TO_ANALYZE = 30

def analyze_win_rate(symbol):
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"Failed to initialize MT5 at {TERMINAL_PATH}")
        return

    print(f"\n--- Analyzing {symbol} (Last {DAYS_TO_ANALYZE} Days) ---")
    
    # Calculate dates
    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=DAYS_TO_ANALYZE)
    
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_to)
    if rates is None or len(rates) == 0:
        print(f"Could not fetch data for {symbol}. Check if history is available.")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # 1. ATR VOLATILITY FILTER (Exact match to live_execution.py)
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                     abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(20).mean()
    
    # Logic Params
    risk_pts = 50.0 if "BTC" in symbol.upper() else 2.0
    
    trades = []
    in_pos = False
    entry_p = 0
    sl = 0
    tp = 0
    pos_type = 0 

    # Start after ATR calculation period
    for i in range(40, len(df)):
        row = df.iloc[i]
        
        if not in_pos:
            # --- APPLY ATR VOLATILITY PAUSE ---
            is_too_quiet = df['atr'].iloc[i] < df['atr_ma'].iloc[i]
            if is_too_quiet:
                continue 

            # Check for Signal
            signal = superb_momentum_logic(df, None, i, {})
            if signal != 0:
                in_pos = True
                pos_type = signal
                entry_p = row['close']
                sl = entry_p - risk_pts if signal == 1 else entry_p + risk_pts
                tp = entry_p + risk_pts if signal == 1 else entry_p - risk_pts
        else:
            # Position Management
            p_cur = row['close']
            p_high = row['high']
            p_low = row['low']
            p_profit = (p_cur - entry_p) if pos_type == 1 else (entry_p - p_cur)
            
            # --- 90% Trailing Logic ---
            target_dist = risk_pts
            if p_profit >= (target_dist * 0.9):
                lock_profit = target_dist * 0.25
                trail_level = entry_p + lock_profit if pos_type == 1 else entry_p - lock_profit
                if pos_type == 1:
                    if trail_level > sl: sl = trail_level
                else:
                    if sl == 0 or trail_level < sl: sl = trail_level

            # Exit Conditions (Conservative check)
            if pos_type == 1:
                if p_low <= sl: # Hit SL or Trail
                    trades.append(sl - entry_p)
                    in_pos = False
                elif p_high >= tp: # Hit TP
                    trades.append(tp - entry_p)
                    in_pos = False
            else:
                if p_high >= sl: 
                    trades.append(entry_p - sl)
                    in_pos = False
                elif p_low <= tp: 
                    trades.append(entry_p - tp)
                    in_pos = False

    if not trades:
        print("No trades triggered in this period.")
        return

    wins = [t for t in trades if t > 0]
    wr = (len(wins) / len(trades)) * 100
    total_pnl = sum(trades)
    
    print(f"Total Trades: {len(trades)}")
    print(f"Wins: {len(wins)} | Losses: {len(trades) - len(wins)}")
    print(f"Win Rate: {wr:.2f}%")
    print(f"Total PnL (Points): {total_pnl:.2f}")

if __name__ == "__main__":
    for s in SYMBOLS:
        analyze_win_rate(s)
    mt5.shutdown()
