import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# V9.0 BULLETPROOF ENGINE - SINGLE ENTRY LOCK + RESTORED TRAILING
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
    print("Diamond Engine V9.0 - Bulletproof Multi-Trade Fix Active.")
    mt5.initialize(path=DEFAULT_TERMINAL_PATH)

    last_entry_time = None
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
            
            # --- CRITICAL: ALL POSITIONS DEFINED AT TOP ---
            all_pos = mt5.positions_get()

            # --- 1. ASSET-SPECIFIC TRAILING ENGINE ---
            if all_pos:
                for pos in all_pos:
                    if symbol[:6].upper() not in pos.symbol.upper(): continue
                    
                    p_cur, p_open, p_sl, p_tp = pos.price_current, pos.price_open, pos.sl, pos.tp
                    is_buy = (pos.type == mt5.POSITION_TYPE_BUY)
                    p_profit = (p_cur - p_open) if is_buy else (p_open - p_cur)
                    is_btc_pos = "BTC" in pos.symbol.upper()
                    
                    new_sl = 0
                    if is_btc_pos:
                        # BTC LOGIC (STAYS SAME): Lock Break-even at $10, then $5 trail
                        if p_profit >= 10.0:
                            calc_sl = p_cur - 5.0 if is_buy else p_cur + 5.0
                            be_level = p_open + 1.0 if is_buy else p_open - 1.0
                            new_sl = max(calc_sl, be_level) if is_buy else min(calc_sl, be_level)
                    else:
                        # GOLD LOGIC (RISK-HALVER): If profit hits $1 (50% of target), move SL to half risk
                        if p_profit >= 1.0: # 50% of $2 target
                            # Set SL to -$1.00 risk from entry (Half of initial $2 risk)
                            new_sl = p_open - 1.0 if is_buy else p_open + 1.0
                    
                    if new_sl != 0:
                        digits = mt5.symbol_info(pos.symbol).digits
                        should_update = (new_sl > p_sl + 0.01) if is_buy else (p_sl == 0 or new_sl < p_sl - 0.01)
                        if should_update:
                            min_gap = max(s_info.trade_stops_level * s_info.point, s_info.point * 10)
                            if abs(p_cur - new_sl) >= min_gap:
                                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "symbol": pos.symbol, "sl": round(new_sl, digits), "tp": p_tp, "magic": pos.magic})
                                if not is_btc_pos: print(f"\n[GOLD-HALVER] Risk reduced to $1.00 (Profit: ${p_profit:.2f})")

            # --- 2. SIGNAL SCAN (WITH SINGLE-ENTRY LOCK) ---
            if not state["active"]: 
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol} | STANDBY", end="", flush=True)
                time.sleep(1); continue

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s')
                cur_min = df.iloc[-1]['time']
                tick = mt5.symbol_info_tick(symbol)
                
                # Double Check: Only trade if no active position AND new minute
                if not all_pos or not any(symbol[:6].upper() in p.symbol.upper() for p in all_pos):
                    if last_entry_time is None or cur_min > last_entry_time:
                        hh = df['high'].iloc[-6:-1].max(); ll = df['low'].iloc[-6:-1].min()
                        intent = "READY BUY" if tick.ask > hh else ("READY SELL" if tick.bid < ll else "WAITING")
                        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${tick.bid:.2f} | {intent}", end="", flush=True)

                        signal = superb_momentum_logic(df, None, len(df)-1, {})
                        if signal != 0:
                            price = tick.ask if signal == 1 else tick.bid
                            risk_pts = 50.0 if "BTC" in symbol.upper() else 2.0
                            sl_price = price - risk_pts if signal == 1 else price + risk_pts
                            tp_price = price + risk_pts if signal == 1 else price - risk_pts
                            
                            f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                            res = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": state.get("lots", 0.10), "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL, "price": price, "sl": round(sl_price, s_info.digits), "tp": round(tp_price, s_info.digits), "magic": MAGIC_NUMBER, "comment": "V9.0_FIX", "type_filling": f_mode})
                            if res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"\n[SUCCESS] Trade Placed. Locking Minute: {cur_min}")
                                last_entry_time = cur_min # LOCK THE MINUTE
            time.sleep(0.1)
        except Exception as outer_err: 
            print(f"\nOuter Error: {outer_err}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()
