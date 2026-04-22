import MetaTrader5 as mt5
import pandas as pd
import time
import json
import os
from datetime import datetime, timedelta
import fractal_logic as fl

SYMBOL = "XAUUSD+"
LOTS = 0.10 
MAGIC = 404040
STATE_FILE = "bot_state.json"
TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"

def get_state():
    for _ in range(10):
        try:
            if not os.path.exists(STATE_FILE): 
                return {"active": False, "connected": False, "symbol": SYMBOL, "lots": LOTS, "history": [], "total_pnl": 0}
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError):
            time.sleep(0.05)
    return {"active": False, "connected": False, "symbol": SYMBOL, "lots": LOTS, "history": [], "total_pnl": 0}

def save_state(state):
    import secrets
    temp_file = f"bot_state_{secrets.token_hex(4)}.tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(state, f)
        os.replace(temp_file, STATE_FILE)
    except Exception:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def sync_mt5_history(state):
    try:
        from_date = datetime.now() - timedelta(days=3)
        history = mt5.history_deals_get(from_date, datetime.now() + timedelta(days=1))
        if history:
            pos_map = {}
            for deal in history:
                if any(s in deal.symbol.upper() for s in ["XAU", "GOLD"]):
                    pid = deal.position_id
                    if pid not in pos_map:
                        pos_map[pid] = {"time": "", "symbol": deal.symbol, "type": "", "price": 0.0, "profit": 0.0}
                    if deal.entry == mt5.DEAL_ENTRY_IN:
                        pos_map[pid].update({
                            "time": datetime.fromtimestamp(deal.time).strftime('%H:%M:%S'),
                            "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                            "price": deal.price
                        })
                    pos_map[pid]["profit"] += deal.profit
            state["history"] = [v for v in pos_map.values() if v["time"]]
            state["total_pnl"] = sum(t["profit"] for t in state["history"])
    except Exception as e:
        print(f"\n[SYNC ERROR] {e}")
    return state

def sync_account():
    acc = mt5.account_info()
    if not acc: return
    state = get_state()
    state["account"] = {"id": acc.login, "broker": acc.company, "balance": acc.balance}
    state = sync_mt5_history(state)
    state["connected"] = True
    save_state(state)

def manage_positions(positions):
    """
    Strict Management:
    1. At 0.5R Profit -> Take 30% Partial Profit + Move SL to BE.
    2. At 90% TP Move -> Move SL to 50% Profit.
    """
    for pos in positions:
        entry = pos.price_open
        sl = pos.sl
        tp = pos.tp
        curr = pos.price_current
        is_buy = pos.type == mt5.POSITION_TYPE_BUY
        
        # Distance from entry to initial TP (1.5R)
        target_dist = abs(tp - entry)
        if target_dist == 0: continue
        
        profit_points = (curr - entry) if is_buy else (entry - curr)
        
        # Rule A: 90% Milestone (Move SL to 50% Profit)
        if profit_points >= (0.9 * target_dist):
            new_sl = round(entry + (0.5 * target_dist) if is_buy else entry - (0.5 * target_dist), 2)
            if (is_buy and new_sl > sl) or (not is_buy and new_sl < sl):
                mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": new_sl, "tp": tp})
                print(f"\n[MANAGEMENT] 90% Milestone! SL moved to 50% Profit for {pos.ticket}")

        # Rule B: 0.5R Milestone (Bank 30% + Move SL to BE)
        # Derived Initial Risk = target_dist / 1.5
        initial_risk = target_dist / 1.5
        is_secured = (is_buy and sl >= entry) or (not is_buy and sl <= entry)
        
        if profit_points >= (initial_risk * 0.5) and not is_secured:
            # 1. Move SL to Breakeven
            mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket, "sl": entry, "tp": tp})
            
            # 2. Take 30% Partial Profit
            partial_vol = round(pos.volume * 0.3, 2)
            if partial_vol < 0.01: partial_vol = 0.01
            
            tick = mt5.symbol_info_tick(SYMBOL)
            mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": partial_vol,
                "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
                "position": pos.ticket,
                "price": tick.bid if is_buy else tick.ask,
                "comment": "30% Banked",
                "type_filling": mt5.ORDER_FILLING_IOC
            })
            print(f"\n[MANAGEMENT] 0.5R Reached! Banked 30% & Secured BE for {pos.ticket}")

def run_fractal_bot():
    print("=" * 58)
    print("  FRACTAL MACHINE GUN V3.1 — ULTRA AGGRESSIVE")
    print("=" * 58)
    
    # Initial path from file, but we will check state in loop
    current_path = TERMINAL_PATH
    mt5.initialize(path=current_path)

    while True:
        try:
            state = get_state()
            
            # Handle Disconnect: If dashboard says NOT connected AND no intent to connect
            if not state.get("connected") and not state.get("connect_intent"):
                mt5.shutdown()
                print("\r[OFFLINE] MT5 Disconnected from Dashboard.   ", end="", flush=True)
                time.sleep(2); continue

            # Update path if changed in dashboard
            new_path = state.get("terminal_path", current_path)
            if new_path != current_path:
                print(f"\n[PATH CHANGE] Switching to {new_path}")
                mt5.shutdown()
                if mt5.initialize(path=new_path):
                    current_path = new_path
            
            # Ensure MT5 is initialized if we ARE supposed to be connected
            if state.get("connected") or state.get("connect_intent"):
                if not mt5.terminal_info(): # Check if actually initialized
                    mt5.initialize(path=current_path)
            
            sync_account() # Updates 'connected' and 'account' in bot_state.json

            if not state.get("active"):
                print("\r[STANDBY] Waiting for 'START BOT'...   ", end="", flush=True)
                time.sleep(2); continue
            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 500)
            if rates is None: continue
            df = pd.DataFrame(rates)
            df = fl.calculate_indicators(df)
            curr = df.iloc[-1]
            
            all_pos = mt5.positions_get(symbol=SYMBOL, magic=MAGIC)
            if all_pos:
                manage_positions(all_pos)
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] IN TRADE | PnL: ${sum(p.profit for p in all_pos):.2f}    ", end="", flush=True)
                time.sleep(1); continue

            sig, entry, sl, tp = fl.check_fractal_signal(df)
            if sig != 0:
                tick = mt5.symbol_info_tick(SYMBOL)
                price = tick.ask if sig == 1 else tick.bid
                
                # Use standard IOC filling mode for high frequency
                filling = mt5.ORDER_FILLING_IOC
                
                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": SYMBOL,
                    "volume": float(state.get("lots", LOTS)),
                    "type": mt5.ORDER_TYPE_BUY if sig == 1 else mt5.ORDER_TYPE_SELL,
                    "price": price,
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "magic": MAGIC,
                    "comment": "FRACTAL FIRE",
                    "type_filling": filling,
                }
                
                print(f"\n[FIRE] Attempting {'BUY' if sig==1 else 'SELL'} @ {price}")
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[BANG] Trade SUCCESS: {res.order}")
                else:
                    print(f"[JAM] Failed: {res.retcode if res else 'Unknown'}")

            # Status Radar
            trend = "BULL" if curr['close'] > curr['ema_50'] else "BEAR"
            target_h, target_l = round(curr['last_f_h'], 2), round(curr['last_f_l'], 2)
            bid = mt5.symbol_info_tick(SYMBOL).bid
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] {trend} | BUY@{target_h} | SELL@{target_l} | Bid:{bid:.2f}    ", end="", flush=True)
            time.sleep(1)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_fractal_bot()
