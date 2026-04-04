import MetaTrader5 as mt5
import time

TERMINAL_PATH = r"C:\Users\HP Power\AppData\Roaming\FundedNext MT5 Terminal\terminal64.exe"
SYMBOL = "XAUUSD"

def test_connection_with_trade():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("MT5 initialize failed", mt5.last_error())
        return

    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"{SYMBOL} not found")
        mt5.shutdown()
        return

    # Check supported filling modes using bitmask
    # symbol_info.filling_mode bitmask: 1=FOK, 2=IOC
    filling_mode = mt5.ORDER_FILLING_RETURN
    if symbol_info.filling_mode & 1:
        filling_mode = mt5.ORDER_FILLING_FOK
    elif symbol_info.filling_mode & 2:
        filling_mode = mt5.ORDER_FILLING_IOC

    print(f"Using filling mode: {filling_mode}")
    print(f"Connected to {mt5.terminal_info().name}. Placing test trade...")
    
    tick = mt5.symbol_info_tick(SYMBOL)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "magic": 999999,
        "comment": "Connection Test",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed (Code {result.retcode}): {result.comment}")
        mt5.shutdown()
        return

    print(f"SUCCESS: Trade opened at {result.price}. Waiting 5 seconds...")
    time.sleep(5)
    
    position_id = result.order
    tick = mt5.symbol_info_tick(SYMBOL)
    
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_SELL,
        "position": position_id,
        "price": tick.bid,
        "magic": 999999,
        "comment": "Closing Test",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    result_close = mt5.order_send(close_request)
    if result_close.retcode != mt5.TRADE_RETCODE_DONE:
        print("Close failed:", result_close.comment)
    else:
        print(f"SUCCESS: Trade closed at {result_close.price}.")
        
    mt5.shutdown()

if __name__ == "__main__":
    test_connection_with_trade()
