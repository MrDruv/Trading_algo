import time
import json
import os
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# V7.1 DIAMOND PRECISION - HARD-WIRED TRAILS (NO DASHBOARD LAG)
# ---------------------------------------------------------------------------

MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"
DEFAULT_TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

def get_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {"active": False, "connected": False, "symbol": "BTCUSD", "terminal_path": DEFAULT_TERMINAL_PATH, "lots": 0.50, "sl_points": 15, "history": [], "total_pnl": 0.0, "account": {}}

def sync_account_info(symbol):
    state = get_state()
    acc = mt5.account_info()
    if acc:
        new_acc_info = { "id": acc.login, "broker": acc.company, "balance": acc.balance, "leverage": acc.leverage }
        state["account"] = new_acc_info
        from_date = datetime.now() - timedelta(days=2); to_date = datetime.now() + timedelta(days=1)
        history = mt5.history_deals_get(from_date, to_date)
        if history:
            pos_map = {}
            for deal in history:
                if deal.symbol in ["BTCUSD", "XAUUSD", "XAUUSD+"]:
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
    print("Diamond Engine V7.1 - Precision Locked.")
    if not mt5.initialize(path=DEFAULT_TERMINAL_PATH):
        print(f"FAILED: {mt5.last_error()}"); time.sleep(5)

    last_time = None
    while True:
        try:
            state = get_state()
            is_connected = mt5.terminal_info().connected if mt5.terminal_info() else False
            if not is_connected: mt5.initialize(path=DEFAULT_TERMINAL_PATH); time.sleep(2); continue

            symbol = state["symbol"]
            if symbol == "XAUUSD": symbol = "XAUUSD+"
            
            if int(time.time()) % 10 == 0: sync_account_info(symbol)
            if not state["active"]: 
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol} | STANDBY", end="", flush=True)
                time.sleep(1); continue

            # PRECISION PARAMS (HARD-WIRED FOR VALID STOPS)
            s_info = mt5.symbol_info(symbol)
            if not s_info: continue
            
            is_btc = "BTC" in symbol
            # Hard-wired trail distances for maximum safety
            tr_dist = 3.0 if is_btc else 0.10
            sl_mult = 1.0 if is_btc else 0.01
            digits = s_info.digits
            sl_pts = state.get("sl_points", 15.0) # Still from dashboard
            lots = state.get("lots", 0.10)

            # 1. RAPID-LOCK TRAILING ENGINE (V7.6)
            positions = mt5.positions_get(symbol=symbol, magic=MAGIC_NUMBER)
            if positions:
                for pos in positions:
                    p_cur, p_open, p_sl = pos.price_current, pos.price_open, pos.sl
                    is_buy = (pos.type == mt5.POSITION_TYPE_BUY)
                    p_profit = (p_cur - p_open) if is_buy else (p_open - p_cur)
                    m = 1.0 if "BTC" in symbol.upper() else 0.01
                    
                    # LOGIC: Lock Break-even at $10, then follow at $5 distance
                    new_sl = 0
                    if p_profit >= (10.0 * m):
                        # Use $5 trail distance as requested
                        trail_gap = 5.0 * m
                        calculated_sl = p_cur - trail_gap if is_buy else p_cur + trail_gap
                        
                        # Ensure we at least lock in Break-even (plus $1 for safety)
                        be_level = p_open + (1.0 * m) if is_buy else p_open - (1.0 * m)
                        new_sl = max(calculated_sl, be_level) if is_buy else min(calculated_sl, be_level)
                    
                    if new_sl != 0:
                        # Only update if target is better than current SL
                        should_update = (new_sl > p_sl + (s_info.point * 2)) if is_buy else (p_sl == 0 or new_sl < p_sl - (s_info.point * 2))
                        
                        if should_update:
                            res = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "symbol": symbol, "sl": round(new_sl, digits), "tp": pos.tp, "magic": MAGIC_NUMBER})
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"\n[RAPID-LOCK] {symbol} SL -> {round(new_sl, digits)} (Profit: ${p_profit:.2f})")

            # 2. SIGNAL SCAN
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s')
                tick = mt5.symbol_info_tick(symbol)
                if not tick: continue
                
                if not positions:
                    hh = df['high'].iloc[-6:-1].max(); ll = df['low'].iloc[-6:-1].min()
                    print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${tick.bid:.2f} | Range: ${ll:.2f}-${hh:.2f}", end="", flush=True)

                if last_time is None or df.iloc[-1]['time'] > last_time:
                    signal = superb_momentum_logic(df, None, len(df)-1, {})
                    if signal != 0 and not positions:
                        price = tick.ask if signal == 1 else tick.bid
                        risk_pts = sl_pts + ( (tick.ask-tick.bid) if (tick.ask-tick.bid) >= 5.0 else 0)
                        sl_val = price - (risk_pts * sl_mult) if signal == 1 else price + (risk_pts * sl_mult)
                        
                        f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                        res = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lots, "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL, "price": price, "sl": round(sl_val, digits), "magic": MAGIC_NUMBER, "comment": "V7.1_PREC", "type_filling": f_mode})
                        if res.retcode == mt5.TRADE_RETCODE_DONE:
                            print(f"\n[SUCCESS] Breakout Trade {res.order} Executed at {price}")
                            last_time = df.iloc[-1]['time'] # LOCK THE MINUTE INSTANTLY
                        else:
                            print(f"\n[ERROR] {res.comment}")
                    # Remove the old last_time update from here to prevent loops
            time.sleep(0.1)
        except Exception: time.sleep(1)

if __name__ == "__main__":
    run_bot()
