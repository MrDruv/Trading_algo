import time
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
from train import active_momentum_scalp

# ---------------------------------------------------------------------------
# BTCUSD UNLIMITED SUPERB SCALPER (NO TP, DOLLAR-BASED)
# ---------------------------------------------------------------------------

SYMBOL = "BTCUSD"
TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
LOTS = 0.50 
MAGIC_NUMBER = 111999

# Back to Dollar-Based Params
PARAMS = {
    'risk_dollars': 40.0,   # Initial SL
    'trail_start': 10.0,    # Start trailing at $10 profit
    'trail_dist': 2.0,      # Trail at $2 distance
    'max_spread': 10.0
}

def manage_trailing_stops():
    positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
    if not positions: return
    for pos in positions:
        ticket, current_sl, pos_type, price_cur, price_open = pos.ticket, pos.sl, pos.type, pos.price_current, pos.price_open
        
        if pos_type == mt5.POSITION_TYPE_BUY:
            profit = price_cur - price_open
            if profit >= PARAMS['trail_start']:
                new_sl = max(price_cur - PARAMS['trail_dist'], price_open + 5.0)
                if new_sl > current_sl + 0.1:
                    mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl})
                    
        elif pos_type == mt5.POSITION_TYPE_SELL:
            profit = price_open - price_cur
            if profit >= PARAMS['trail_start']:
                new_sl = min(price_cur + PARAMS['trail_dist'], price_open - 5.0)
                if current_sl == 0: current_sl = price_open + 1000
                if new_sl < current_sl - 0.1:
                    mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl})

def run_live():
    if not mt5.initialize(path=TERMINAL_PATH): return
    print(f"[{datetime.now().strftime('%H:%M')}] MT5 Connected. Unlimited Superb strategy active.")
    last_time = None
    
    while True:
        try:
            manage_trailing_stops()
            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 100)
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            cur_time = df.iloc[-1]['time']
            if last_time is None or cur_time > last_time:
                signal = active_momentum_scalp(df, len(df)-1, PARAMS)
                
                if signal != 0 and len(mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)) == 0:
                    tick = mt5.symbol_info_tick(SYMBOL)
                    order_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
                    price = tick.ask if signal == 1 else tick.bid
                    sl = price - PARAMS['risk_dollars'] if signal == 1 else price + PARAMS['risk_dollars']
                        
                    res = mt5.order_send({
                        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": LOTS,
                        "type": order_type, "price": price, "sl": sl,
                        "magic": MAGIC_NUMBER, "comment": "SUPERB_UNLIMITED",
                        "type_filling": mt5.ORDER_FILLING_IOC
                    })
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"[{datetime.now().strftime('%H:%M')}] SUCCESS: EXEC {SYMBOL} (No TP)")
                
                last_time = cur_time
            time.sleep(1)
        except Exception: time.sleep(5)

if __name__ == "__main__":
    run_live()
