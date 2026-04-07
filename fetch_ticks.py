import MetaTrader5 as mt5
import pandas as pd
import os

TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD+"

def fetch_tick_data():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("MT5 initialize failed")
        return
    
    print(f"Fetching 100,000 ticks for {SYMBOL}...")
    ticks = mt5.copy_ticks_from(SYMBOL, pd.Timestamp.now() - pd.Timedelta(days=3), 100000, mt5.COPY_TICKS_ALL)
    mt5.shutdown()
    
    if ticks is None or len(ticks) == 0:
        print("Failed to fetch ticks")
        return
        
    df = pd.DataFrame(ticks)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autoresearch_trading")
    os.makedirs(CACHE_DIR, exist_ok=True)
    FILE_PATH = os.path.join(CACHE_DIR, "gold_ticks.parquet")
    df.to_parquet(FILE_PATH)
    print(f"Saved {len(df)} ticks to {FILE_PATH}")

if __name__ == "__main__":
    fetch_tick_data()
