import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# V8.7 UNIFIED PROFIT ENGINE - TARGETS + RAPID TRAILING
# ---------------------------------------------------------------------------

MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"
DEFAULT_TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

def get_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {"active": False, "connected": False, "symbol": "BTCUSD", "terminal_path": DEFAULT_TERMINAL_PATH, "lots": 0.50, "history": [], "total_pnl": 0.0, "account": {}}

def sync_account_info(symbol):
    state = get_state()
    acc = mt5.account_info()
    if acc:
        new_acc_info = { "id": acc.login, "broker": acc.company, "balance": acc.balance, "leverage": acc.leverage, "margin_free": acc.margin_free }
        state["account"] = new_acc_info
        from_date = datetime.now() - timedelta(days=2); to_date = datetime.now() + timedelta(days=1)
        history = mt5.history_deals_get(from_date, to_date)
        if history:
            pos_map = {}
            for deal in history:
                if any(s in deal.symbol.upper() for s in ["BTC", "XAU"]):
                    p_id = deal.position_id
                    if p_id not in pos_map: pos_map[p_id] = {"time": "", "symbol": deal.symbol, "type": "", "price": 0.0, "profit": 0.0}
                    if deal.entry == mt5.DEAL_ENTRY_IN:
                        pos_map[p_id].update({"time": datetime.fromtimestamp(deal.time).strftime('%H:%M:%S'), "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL", "price": deal.price})
                    pos_map[p_id]["profit"] += deal.profit
            state["history"] = [v for k, v in sorted(pos_map.items()) if v["time"]]
            state["total_pnl"] = sum(t["profit"] for t in state["history"])
        state["connected"] = True
        with open(STATE_FILE, 'w') as f: json.dump(state, f)

def run_bot():
    print("Diamond Engine V8.7 - Unified Profit Engine Active.")
    mt5.initialize(path=DEFAULT_TERMINAL_PATH)

    last_time = None
    while True:
        try:
            state = get_state()
            if not mt5.terminal_info().connected: 
                mt5.initialize(path=DEFAULT_TERMINAL_PATH); time.sleep(2); continue

            symbol = state["symbol"]
            if symbol == "XAUUSD": symbol = "XAUUSD+"
            
            sync_account_info(symbol)
            s_info = mt5.symbol_info(symbol)
            if not s_info: time.sleep(2); continue
            
            # FIXED: Define all_pos here so it is available for the rest of the loop
            all_pos = mt5.positions_get()

            # --- V8.8 STRICT 1:1 ENGINE (NO TRAILING) ---
            # Trailing logic removed as requested. 
            # Trades will only exit via Hard TP or Hard SL.
            try:
                pass 
            except Exception as e: pass

            # 2. SIGNAL SCAN
            if not state["active"]: 
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol} | STANDBY", end="", flush=True)
                time.sleep(1); continue

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s')
                tick = mt5.symbol_info_tick(symbol)
                if not all_pos or not any(symbol[:6].upper() in p.symbol.upper() for p in all_pos):
                    hh = df['high'].iloc[-6:-1].max(); ll = df['low'].iloc[-6:-1].min()
                    print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${tick.bid:.2f} | Range: ${ll:.2f}-${hh:.2f}", end="", flush=True)

                    if last_time is None or df.iloc[-1]['time'] > last_time:
                        signal = superb_momentum_logic(df, None, len(df)-1, {})
                        if signal != 0:
                            price = tick.ask if signal == 1 else tick.bid
                            # Risk Params (Strict 1:1)
                            is_btc = "BTC" in symbol.upper()
                            sl_dist = 50.0 if is_btc else 2.0 
                            tp_dist = sl_dist # 1:1 RATIO
                            
                            sl_price = price - (sl_dist + (tick.ask-tick.bid)) if signal == 1 else price + (sl_dist + (tick.ask-tick.bid))
                            tp_price = price + tp_dist if signal == 1 else price - tp_dist
                            
                            f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                            res = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": state.get("lots", 0.10), "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL, "price": price, "sl": round(sl_price, s_info.digits), "tp": round(tp_price, s_info.digits), "magic": MAGIC_NUMBER, "comment": "V8.7_PROFIT", "type_filling": f_mode})
                            if res.retcode == mt5.TRADE_RETCODE_DONE: 
                                print(f"\n[SUCCESS] Trade Placed at {price} | TP: {round(tp_price, s_info.digits)}")
                                last_time = df.iloc[-1]['time']
            time.sleep(0.1)
        except Exception as outer_err: print(f"\nOuter Error: {outer_err}"); time.sleep(1)

if __name__ == "__main__":
    run_bot()
