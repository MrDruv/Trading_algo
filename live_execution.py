import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# BTCUSD & XAUUSD DYNAMIC ASSET ENGINE (V4.5.1)
# ---------------------------------------------------------------------------

MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"

def get_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {"active": False, "connected": False, "symbol": "BTCUSD", "terminal_path": "", "lots": 0.50, "sl_points": 15, "trail_points": 5, "history": [], "total_pnl": 0.0, "account": {}}

def update_state(connected=None, active=None, history=None, total_pnl=None, account=None):
    state = get_state()
    if connected is not None: state["connected"] = connected
    if active is not None: state["active"] = active
    if history is not None: state["history"] = history
    if total_pnl is not None: state["total_pnl"] = total_pnl
    if account is not None: state["account"] = account
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

def sync_account_info(current_symbol):
    state = get_state()
    acc = mt5.account_info()
    if acc:
        new_acc_info = { "id": acc.login, "broker": acc.company, "balance": acc.balance, "leverage": acc.leverage }
        if state.get("account", {}).get("id") != acc.login:
            state["history"] = []; state["total_pnl"] = 0.0
        state["account"] = new_acc_info
        
        # Sync history for BOTH symbols to keep dashboard accurate
        from_date = datetime.now() - timedelta(days=2)
        to_date = datetime.now() + timedelta(days=1)
        history = mt5.history_deals_get(from_date, to_date)
        if history:
            pos_map = {}
            for deal in history:
                if deal.symbol in ["BTCUSD", "XAUUSD"]:
                    p_id = deal.position_id
                    if p_id not in pos_map: pos_map[p_id] = {"time": "", "symbol": deal.symbol, "type": "", "price": 0.0, "profit": 0.0}
                    if deal.entry == mt5.DEAL_ENTRY_IN:
                        pos_map[p_id].update({"time": datetime.fromtimestamp(deal.time).strftime('%H:%M:%S'), "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL", "price": deal.price})
                    pos_map[p_id]["profit"] += deal.profit
            new_history = [v for k, v in sorted(pos_map.items()) if v["time"]]
            state["history"] = new_history
            state["total_pnl"] = sum(t["profit"] for t in new_history)
        
        state["connected"] = True
        with open(STATE_FILE, 'w') as f: json.dump(state, f)

def run_bot():
    print("Quantum Multi-Asset Engine V4.5.1 Active.")
    last_time = None
    
    while True:
        try:
            state = get_state()
            is_connected = mt5.terminal_info().connected if mt5.terminal_info() else False
            
            if state.get("connect_intent") and not is_connected:
                path = state.get("terminal_path")
                if path and mt5.initialize(path=path):
                    update_state(connected=True)
                else: time.sleep(2); continue

            if not is_connected: time.sleep(1); continue

            # Dynamic Asset Selection
            symbol = state.get("symbol", "BTCUSD")
            
            if int(time.time()) % 5 == 0:
                sync_account_info(symbol)

            if not state["active"]: time.sleep(1); continue

            # Dynamic Risk Params
            s_info = mt5.symbol_info(symbol)
            if not s_info: time.sleep(5); continue
                
            point = s_info.point
            sl_pts = state.get("sl_points", 15.0)
            tr_pts = state.get("trail_points", 5.0)
            lots = state.get("lots", 0.10)

            # Ghost Trailing
            positions = mt5.positions_get(symbol=symbol, magic=MAGIC_NUMBER)
            if positions:
                for pos in positions:
                    p_cur, current_sl = pos.price_current, pos.sl
                    if pos.type == mt5.POSITION_TYPE_BUY:
                        new_sl = p_cur - (tr_pts * point)
                        if new_sl > current_sl + (point * 2):
                            mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": round(new_sl, 2), "tp": pos.tp})
                    else:
                        new_sl = p_cur + (tr_pts * point)
                        if current_sl == 0 or new_sl < current_sl - (point * 2):
                            mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": round(new_sl, 2), "tp": pos.tp})

            # Signal Scan
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s')
                cur_time = df.iloc[-1]['time']
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${df.close.iloc[-1]:.2f} | Engine Active", end="", flush=True)

                if last_time is None or cur_time > last_time:
                    signal = superb_momentum_logic(df, len(df)-1, {})
                    if signal != 0 and not positions:
                        tick = mt5.symbol_info_tick(symbol)
                        spread = tick.ask - tick.bid
                        price = tick.ask if signal == 1 else tick.bid
                        actual_sl = price - ((sl_pts * point) + spread) if signal == 1 else price + ((sl_pts * point) + spread)
                        f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                        mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lots, "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL, "price": price, "sl": round(actual_sl, 2), "magic": MAGIC_NUMBER, "comment": "V4.5.1", "type_filling": f_mode})
                    last_time = cur_time
            
            time.sleep(0.1)
        except Exception: time.sleep(1)

if __name__ == "__main__":
    run_bot()
