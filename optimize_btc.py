import pandas as pd
import math
from prepare import load_data

def backtest(df, params):
    bb_period = params['bb_period']
    rsi_period = params['rsi_period']
    rsi_low = params['rsi_low']
    rsi_high = params['rsi_high']
    rr = params['rr']
    risk = params['risk']
    trail = params['trail']
    
    # Vectorized indicators
    df['ma'] = df['close'].rolling(bb_period).mean()
    df['std'] = df['close'].rolling(bb_period).std()
    df['upper'] = df['ma'] + (2 * df['std'])
    df['lower'] = df['ma'] - (2 * df['std'])
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    trades = []
    in_pos = False
    pos_type = 0
    entry_price = 0
    sl = 0
    tp = 0
    spread = 1.0
    
    # Iterate to simulate trailing stops properly
    for i in range(max(bb_period, rsi_period), len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        if not in_pos:
            # Signal
            if prev['close'] < prev['lower'] and prev['rsi'] < rsi_low:
                in_pos = True
                pos_type = 1
                entry_price = row['open'] + spread
                sl = entry_price - risk
                tp = entry_price + (risk * rr)
            elif prev['close'] > prev['upper'] and prev['rsi'] > rsi_high:
                in_pos = True
                pos_type = -1
                entry_price = row['open'] - spread
                sl = entry_price + risk
                tp = entry_price - (risk * rr)
        else:
            # Trailing
            if trail > 0:
                if pos_type == 1:
                    new_sl = row['close'] - trail
                    if new_sl > sl: sl = new_sl
                else:
                    new_sl = row['close'] + trail
                    if new_sl < sl: sl = new_sl
            
            # Exit
            if pos_type == 1:
                if row['low'] <= sl:
                    trades.append(sl - entry_price)
                    in_pos = False
                elif row['high'] >= tp:
                    trades.append(tp - entry_price)
                    in_pos = False
            else:
                if row['high'] >= sl:
                    trades.append(entry_price - sl)
                    in_pos = False
                elif row['low'] <= tp:
                    trades.append(entry_price - tp)
                    in_pos = False
                    
    if not trades: return 0, 0, 0
    returns = pd.Series(trades)
    if returns.std() == 0: return 0, 0, len(trades)
    sharpe = (returns.mean() / returns.std()) * math.sqrt(len(trades))
    return sharpe, returns.sum(), len(trades)

if __name__ == '__main__':
    print("Loading recent BTCUSD M1 data...")
    df = load_data().tail(10000).copy() # Last ~7 days
    print(f"Data loaded. Running Deep Optimization on {len(df)} bars...")
    best_sharpe = -999
    best_params = None
    best_pnl = 0
    
    for bb in [14, 20]:
        for rsi_p in [7, 14]:
            for rsi_ext in [(30, 70), (25, 75)]:
                for rr in [1.0, 1.5, 2.0, 3.0]:
                    for risk in [10.0, 20.0, 30.0]:
                        for trail in [5.0, 10.0, 20.0]:
                            p = {'bb_period': bb, 'rsi_period': rsi_p, 'rsi_low': rsi_ext[0], 'rsi_high': rsi_ext[1], 'rr': rr, 'risk': risk, 'trail': trail}
                            sharpe, pnl, num_trades = backtest(df, p)
                            if sharpe > best_sharpe and num_trades > 5 and pnl > 0:
                                best_sharpe = sharpe
                                best_params = p
                                best_pnl = pnl
                                print(f"New Best: {p} | Sharpe: {sharpe:.2f} | PnL: ${pnl*0.1:.2f} (0.1 lot) | Trades: {num_trades}")

    print("FINAL BEST:", best_params)
