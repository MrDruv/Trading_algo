import time
import json
import os
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from train import superb_momentum_logic

# ---------------------------------------------------------------------------
# V11.3 - PRECISION PRO (Fixed Cooldown + Strict 1:3 RR)
# ---------------------------------------------------------------------------

MAGIC_NUMBER = 111999
STATE_FILE = "bot_state.json"
DEFAULT_TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

def get_state():
    for _ in range(5):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            time.sleep(0.05)
    return {"active": False, "connected": False, "symbol": "BTCUSD", "terminal_path": DEFAULT_TERMINAL_PATH, "lots": 0.50, "history": [], "total_pnl": 0.0, "account": {}}

def save_state(state):
    temp_file = STATE_FILE + ".tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(state, f)
        os.replace(temp_file, STATE_FILE)
    except Exception as e:
        print(f"Error saving state: {e}")

_last_sync_time = 0
def sync_account_info(symbol):
    global _last_sync_time
    if time.time() - _last_sync_time < 2:
        return
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
        save_state(state)
        _last_sync_time = time.time()

def calculate_indicators(df):
    # ADX Calculation (14-period)
    df['up'] = df['high'].diff().clip(lower=0)
    df['down'] = (-df['low'].diff()).clip(lower=0)
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr_calc'] = df['tr'].rolling(14).mean()
    df['di_up'] = 100 * (df['up'].rolling(14).mean() / df['atr_calc'])
    df['di_down'] = 100 * (df['down'].rolling(14).mean() / df['atr_calc'])
    df['dx'] = 100 * ((df['di_up'] - df['di_down']).abs() / (df['di_up'] + df['di_down']))
    df['adx'] = df['dx'].rolling(14).mean()
    
    # 15-min Breakout Levels
    df['hh'] = df['high'].rolling(15).max().shift(1)
    df['ll'] = df['low'].rolling(15).min().shift(1)
    return df

def run_bot():
    print("Diamond Engine V11.3 - Precision Pro (Fixed Cooldown + 1:3 RR).")
    mt5.initialize(path=DEFAULT_TERMINAL_PATH)
    
    last_entry_time = None
    last_trade_finish_time = 0
    had_position = False

    while True:
        try:
            state = get_state()
            t_info = mt5.terminal_info()
            if not (t_info and t_info.connected):
                mt5.initialize(path=DEFAULT_TERMINAL_PATH); time.sleep(2); continue

            symbol = state["symbol"]
            if symbol == "XAUUSD": symbol = "XAUUSD+"
            
            sync_account_info(symbol)
            s_info = mt5.symbol_info(symbol)
            if not s_info: time.sleep(2); continue
            
            all_pos = mt5.positions_get()
            current_pos_count = len([p for p in all_pos if symbol[:6].upper() in p.symbol.upper()]) if all_pos else 0

            # --- 1. OPTIMIZED TRAILING ENGINE ---
            if all_pos:
                for pos in all_pos:
                    if symbol[:6].upper() not in pos.symbol.upper(): continue
                    
                    p_cur, p_open, p_sl, p_tp = pos.price_current, pos.price_open, pos.sl, pos.tp
                    is_buy = (pos.type == mt5.POSITION_TYPE_BUY)
                    is_btc = "BTC" in pos.symbol.upper()
                    
                    trail_dist = 20.0 if is_btc else 0.20
                    new_sl = p_cur - trail_dist if is_buy else p_cur + trail_dist
                    
                    should_update = (new_sl > p_sl + 0.01) if is_buy else (p_sl == 0 or new_sl < p_sl - 0.01)
                    
                    if should_update:
                        digits = mt5.symbol_info(pos.symbol).digits
                        min_gap = max(s_info.trade_stops_level * s_info.point, s_info.point * 10)
                        if abs(p_cur - new_sl) >= min_gap:
                            mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "symbol": pos.symbol, "sl": round(new_sl, digits), "tp": p_tp, "magic": pos.magic})

            # --- COOLDOWN TRACKER ---
            if current_pos_count > 0:
                had_position = True
            elif had_position and current_pos_count == 0:
                last_trade_finish_time = time.time()
                had_position = False

            if not state["active"]: 
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol} | STANDBY", end="", flush=True)
                time.sleep(1); continue

            # --- 2. OPTIMIZED SIGNAL SCAN (With Fixed Cooldown) ---
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
            if rates is not None:
                df = calculate_indicators(pd.DataFrame(rates))
                cur_min = pd.to_datetime(df['time'].iloc[-1], unit='s')
                row = df.iloc[-1]
                tick = mt5.symbol_info_tick(symbol)
                
                cooldown_remaining = max(0, 60 - (time.time() - last_trade_finish_time))
                
                if current_pos_count == 0:
                    if last_entry_time is None or cur_min > last_entry_time:
                        
                        adx_val = row['adx']
                        adx_ok = adx_val > 25
                        
                        status = "READY"
                        if not adx_ok: status = "WAIT (ADX)"
                        if cooldown_remaining > 0: status = f"REST ({int(cooldown_remaining)}s)"
                        
                        intent = "BUY" if tick.ask > row['hh'] else ("SELL" if tick.bid < row['ll'] else "WAITING")
                        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${tick.bid:.2f} | {status} | {intent}", end="", flush=True)

                        if not adx_ok or cooldown_remaining > 0:
                            time.sleep(0.1); continue

                        signal = 1 if tick.ask > row['hh'] else (-1 if tick.bid < row['ll'] else 0)
                        
                        if signal != 0:
                            is_btc = "BTC" in symbol.upper()
                            sl_pts = 50.0 if is_btc else 1.0
                            tp_pts = (sl_pts * 3.0) # STRICT 1:3 RR FOR BOTH
                            
                            price = tick.ask if signal == 1 else tick.bid
                            sl_price = price - sl_pts if signal == 1 else price + sl_pts
                            tp_price = price + tp_pts if signal == 1 else price - tp_pts
                            
                            f_mode = mt5.ORDER_FILLING_FOK if s_info.filling_mode & 1 else (mt5.ORDER_FILLING_IOC if s_info.filling_mode & 2 else mt5.ORDER_FILLING_RETURN)
                            res = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": state.get("lots", 0.50), "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL, "price": price, "sl": round(sl_price, s_info.digits), "tp": round(tp_price, s_info.digits), "magic": MAGIC_NUMBER, "comment": "V11.3_STRICT", "type_filling": f_mode})
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"\n[SUCCESS] Trade Placed. Next available candle locked.")
                                last_entry_time = cur_min
                                had_position = True
            time.sleep(0.1)
        except Exception as outer_err: 
            print(f"\nOuter Error: {outer_err}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot()
