import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# BTCUSD V4.2.2 ROBUST SYNC ENGINE
# ---------------------------------------------------------------------------

SYMBOL = "BTCUSD"
MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"

PARAMS = {
    'risk_dollars': 15.0, 'trail_start': 10.0, 'trail_dist': 5.0,  
    'max_spread': 5.0, 'slippage': 10
}

def get_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {"active": False, "connected": False, "connect_intent": False, "terminal_path": "", "lots": 0.50, "history": [], "total_pnl": 0.0, "account": {}}

def update_state(connected=None, active=None, history=None, total_pnl=None, account=None):
    state = get_state()
    if connected is not None: state["connected"] = connected
    if active is not None: state["active"] = active
    if history is not None: state["history"] = history
    if total_pnl is not None: state["total_pnl"] = total_pnl
    if account is not None: state["account"] = account
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def sync_account_info():
    state = get_state()
    acc = mt5.account_info()
    if acc:
        new_acc_info = { "id": acc.login, "broker": acc.company, "balance": acc.balance, "leverage": acc.leverage }
        
        prev_acc_id = state.get("account", {}).get("id")
        if prev_acc_id and prev_acc_id != acc.login:
            state["history"] = []; state["total_pnl"] = 0.0
            
        state["account"] = new_acc_info
        
        from_date = datetime.now() - timedelta(days=2)
        to_date = datetime.now() + timedelta(days=1)
        history = mt5.history_deals_get(from_date, to_date)
        
        if history:
            pos_map = {}
            for deal in history:
                if deal.symbol == SYMBOL:
                    p_id = deal.position_id
                    if p_id not in pos_map: pos_map[p_id] = {"time": "", "type": "", "price": 0.0, "profit": 0.0}
                    if deal.entry == mt5.DEAL_ENTRY_IN:
                        pos_map[p_id].update({"time": datetime.fromtimestamp(deal.time).strftime('%H:%M:%S'), "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL", "price": deal.price})
                    pos_map[p_id]["profit"] += deal.profit
            new_history = [v for k, v in sorted(pos_map.items()) if v["time"]]
            state["history"] = new_history
            state["total_pnl"] = sum(t["profit"] for t in new_history)
            
        state["connected"] = True
        with open(STATE_FILE, 'w') as f: json.dump(state, f)

def run_bot():
    print("Quantum Engine V4.2.2 Active.")
    last_time = None
    
    while True:
        try:
            state = get_state()
            is_connected = mt5.terminal_info().connected if mt5.terminal_info() else False
            
            # A. CONNECTION LOGIC (BASED ON INTENT)
            if state.get("connect_intent") and not is_connected:
                path = state.get("terminal_path")
                if path and os.path.exists(path):
                    print(f"Attempting to connect to: {path}")
                    if mt5.initialize(path=path):
                        print("MT5 Connected.")
                        update_state(connected=True)
                    else:
                        print(f"MT5 Init Failed: {mt5.last_error()}")
                        update_state(connected=False)
                        time.sleep(5)
                else:
                    time.sleep(2)
                continue

            if not state.get("connect_intent") and is_connected:
                print("Disconnecting MT5...")
                mt5.shutdown()
                update_state(connected=False)
                continue

            if not is_connected:
                time.sleep(2)
                continue

            # B. ACTIVE LOGIC
            sync_account_info()
            if not state.get("active"):
                time.sleep(2); continue

            # Trailing Stops...
            positions = mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)
            if positions:
                for pos in positions:
                    if pos.type == mt5.POSITION_TYPE_BUY:
                        if (pos.price_current - pos.price_open) >= PARAMS['trail_start']:
                            new_sl = max(pos.price_current - PARAMS['trail_dist'], pos.price_open + 2.0)
                            if new_sl > pos.sl + 0.1: mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})
                    else:
                        if (pos.price_open - pos.price_current) >= PARAMS['trail_start']:
                            new_sl = min(pos.price_current + PARAMS['trail_dist'], pos.price_open - 2.0)
                            if pos.sl == 0: sl_p = pos.price_open + 1000
                            else: sl_p = pos.sl
                            if new_sl < sl_p - 0.1: mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": pos.tp})

            # Signal Logic...
            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s')
                cur_time = df.iloc[-1]['time']
                if last_time is None or cur_time > last_time:
                    signal = superb_momentum_logic(df, len(df)-1, PARAMS)
                    if signal != 0 and len(mt5.positions_get(symbol=SYMBOL, magic=MAGIC_NUMBER)) == 0:
                        tick = mt5.symbol_info_tick(SYMBOL)
                        if (tick.ask - tick.bid) <= PARAMS['max_spread']:
                            order_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
                            price = tick.ask if signal == 1 else tick.bid
                            sl_val = price - PARAMS['risk_dollars'] if signal == 1 else price + PARAMS['risk_dollars']
                            s_info = mt5.symbol_info(SYMBOL)
                            f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                            mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": state.get("lots", 0.50), "type": order_type, "price": price, "sl": sl_val, "magic": MAGIC_NUMBER, "comment": "V4.2.2", "type_filling": f_mode})
                    last_time = cur_time
            time.sleep(1)
        except Exception: time.sleep(5)

if __name__ == "__main__":
    run_bot()
