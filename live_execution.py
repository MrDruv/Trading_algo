import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# BTCUSD V4.1 ROBUST ENGINE
# ---------------------------------------------------------------------------

SYMBOL = "BTCUSD"
MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"

PARAMS = {
    'risk_dollars': 40.0, 'trail_start': 10.0, 'trail_dist': 5.0,  
    'max_spread': 5.0, 'slippage': 10
}

def get_state():
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except: return {"active": False, "connected": False, "terminal_path": "", "history": [], "total_pnl": 0.0}

def update_state(connected=None, active=None):
    state = get_state()
    if connected is not None: state["connected"] = connected
    if active is not None: state["active"] = active
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

def sync_mt5_history():
    state = get_state()
    from_date = datetime.now() - timedelta(hours=4)
    history = mt5.history_deals_get(from_date, datetime.now())
    if history:
        new_history = []
        total_pnl = 0.0
        for deal in history:
            if deal.symbol == SYMBOL:
                new_history.append({
                    "time": datetime.fromtimestamp(deal.time).strftime('%H:%M:%S'),
                    "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "price": deal.price, "profit": deal.profit
                })
                total_pnl += deal.profit
        state["history"] = new_history
        state["total_pnl"] = total_pnl
    # Verify live connection status
    state["connected"] = mt5.terminal_info().connected if mt5.terminal_info() else False
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

def run_bot():
    print("Bot Engine V4.1 Active.")
    last_time = None
    
    while True:
        try:
            state = get_state()
            info = mt5.terminal_info()
            is_connected = info.connected if info else False
            
            # A. Intent is CONNECTED but MT5 is NOT
            if state.get("connected") and not is_connected:
                path = state.get("terminal_path")
                if path:
                    print(f"Connecting to MT5: {path}...")
                    if mt5.initialize(path=path):
                        print("SUCCESS: MT5 Connected.")
                        update_state(connected=True)
                    else:
                        err = mt5.last_error()
                        print(f"FAILED to connect: {err}")
                        update_state(connected=False)
                        time.sleep(5)
                else:
                    time.sleep(2)
                continue

            # B. Intent is DISCONNECTED but MT5 IS
            if not state.get("connected") and is_connected:
                print("Disconnecting MT5 as requested...")
                mt5.shutdown()
                continue

            if not is_connected:
                time.sleep(2)
                continue

            # C. Operational Logic
            sync_mt5_history()
            if not state["active"]:
                time.sleep(2)
                continue

            # Trailing & Strategy...
            positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
            if positions:
                for pos in positions:
                    ticket, sl, tp, p_cur, p_open = pos.ticket, pos.sl, pos.tp, pos.price_current, pos.price_open
                    if pos.type == mt5.POSITION_TYPE_BUY:
                        if (p_cur - p_open) >= PARAMS['trail_start']:
                            new_sl = max(p_cur - PARAMS['trail_dist'], p_open + 2.0)
                            if new_sl > sl + 0.1: mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": tp})
                    else:
                        if (p_open - p_cur) >= PARAMS['trail_start']:
                            new_sl = min(p_cur + PARAMS['trail_dist'], p_open - 2.0)
                            if sl == 0: sl = p_open + 1000
                            if new_sl < sl - 0.1: mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": tp})

            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                cur_time = df.iloc[-1]['time']
                if last_time is None or cur_time > last_time:
                    signal = superb_momentum_logic(df, len(df)-1, PARAMS)
                    if signal != 0 and len(mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)) == 0:
                        tick = mt5.symbol_info_tick(SYMBOL)
                        if (tick.ask - tick.bid) <= PARAMS['max_spread']:
                            order_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
                            price = tick.ask if signal == 1 else tick.bid
                            sl_val = price - PARAMS['risk_dollars'] if signal == 1 else price + PARAMS['risk_dollars']
                            # Filling mode bitmask detection
                            s_info = mt5.symbol_info(SYMBOL)
                            f_mode = mt5.ORDER_FILLING_RETURN
                            if s_info.filling_mode & 1: f_mode = mt5.ORDER_FILLING_FOK
                            elif s_info.filling_mode & 2: f_mode = mt5.ORDER_FILLING_IOC
                            mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": 0.50, "type": order_type, "price": price, "sl": sl_val, "magic": MAGIC_NUMBER, "comment": "V4.1_SYNC", "type_filling": f_mode})
                    last_time = cur_time
            
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
