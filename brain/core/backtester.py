import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model

# 🎯 IMPORT THE ACTUAL ATTENTION LAYERS TO PREVENT DESERIALIZATION CRASHES
from core.lstm_engine import TemporalAttention

def run_portfolio_backtest():
    CSV_PATH = 'data/training_data.csv'
    MODEL_PATH = 'models/candleflow_lstm.keras'

    if not os.path.exists(CSV_PATH) or not os.path.exists(MODEL_PATH):
        print("❌ Error: Missing core assets. Ensure training_data.csv and model exist.")
        return

    print("🧠 Loading Sigmoid Compass Model weights...")
    def focal_loss_fixed(y_true, y_pred): return y_pred
    model = load_model(MODEL_PATH, custom_objects={
        "focal_loss_fixed": focal_loss_fixed,
        "TemporalAttention": TemporalAttention
    }, compile=False)

    print("📊 Ingesting Compiled Multi-Asset Market Matrix...")
    df = pd.read_csv(CSV_PATH)
    
    # Target features for structured sequence alignment
    features = ['RSI', 'RSI_Lag_1', 'Price_to_SMA20', 'MACD_Hist_Pct', 'BB_Width', 'ATR_Pct', 'CMF', 'Volume_Shock', 'Market_RSI']
    
    starting_capital = 100000.0  # ₹1 Lakh initial simulation workspace
    cash = starting_capital
    active_position = None       # Tracks single active position setup to mirror user dashboard
    portfolio_history = []
    
    trade_logs = []

    print("\n🚀 Commencing Sequential Multi-Asset Backtest Simulation...")
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date').reset_index(drop=True)
    
    # Group by date to process day-by-day cross-sectional inference steps
    unique_dates = df['Date'].unique()
    TIME_STEPS = 20
    
    # Sample a continuous window of the final 250 trading sessions (1 Year)
    test_dates = sorted(unique_dates)[-250:]

    for current_date in test_dates:
        day_data = df[df['Date'] == current_date]
        
        # 🛡️ 1. MANAGE ACTIVE POSITION ENVELOPE (IF OPEN)
        if active_position is not None:
            ticker = active_position['ticker']
            ticker_day = day_data[day_data['Ticker'] == ticker]
            
            if not ticker_day.empty:
                current_price = float(ticker_day['Close'].iloc[-1])
                
                # Check Risk Boundaries against current session exit targets
                if active_position['type'] == 'BUY':
                    if current_price >= active_position['take_profit']:
                        pnl_pct = (current_price - active_position['entry_price']) / active_position['entry_price']
                        realized_pnl = active_position['capital'] * pnl_pct
                        cash += active_position['capital'] + realized_pnl
                        trade_logs.append({"date": current_date, "ticker": ticker, "type": "BUY", "pnl": realized_pnl, "result": "TP"})
                        active_position = None
                    elif current_price <= active_position['stop_loss']:
                        pnl_pct = (current_price - active_position['entry_price']) / active_position['entry_price']
                        realized_pnl = active_position['capital'] * pnl_pct
                        cash += active_position['capital'] + realized_pnl
                        trade_logs.append({"date": current_date, "ticker": ticker, "type": "BUY", "pnl": realized_pnl, "result": "SL"})
                        active_position = None
                else: # Short Positions
                    if current_price <= active_position['take_profit']:
                        pnl_pct = (active_position['entry_price'] - current_price) / active_position['entry_price']
                        realized_pnl = active_position['capital'] * pnl_pct
                        cash += active_position['capital'] + realized_pnl
                        trade_logs.append({"date": current_date, "ticker": ticker, "type": "SELL", "pnl": realized_pnl, "result": "TP"})
                        active_position = None
                    elif current_price >= active_position['stop_loss']:
                        pnl_pct = (active_position['entry_price'] - current_price) / active_position['entry_price']
                        realized_pnl = active_position['capital'] * pnl_pct
                        cash += active_position['capital'] + realized_pnl
                        trade_logs.append({"date": current_date, "ticker": ticker, "type": "SELL", "pnl": realized_pnl, "result": "SL"})
                        active_position = None

        # 🤖 2. SCATTER SCANNER THROUGH MARKET FOR ENTRIES IF PORTFOLIO LIQUID
        if active_position is None:
            for _, row in day_data.iterrows():
                ticker = row['Ticker']
                
                # Extract pre-scaled sequences up to the current simulation time step
                ticker_history = df[(df['Ticker'] == ticker) & (df['Date'] <= current_date)].tail(TIME_STEPS)
                if len(ticker_history) < TIME_STEPS: continue
                
                # 🎯 DIRECTLY PULL PRE-NORMALIZED MATRIX VECTORS FROM CSV
                scaled_seq = ticker_history[features].to_numpy()
                
                # Inference execution step
                tensor_in = np.expand_dims(scaled_seq, axis=0)
                raw_pred = float(model.predict(tensor_in, verbose=0)[0][0])
                
                p_buy = raw_pred
                p_sell = 1.0 - raw_pred
                net_spread = abs(p_buy - p_sell)
                direction = "BUY" if p_buy > p_sell else "SELL"
                
                # Pull original indicator layouts out of row records
                bb_width_normalized = float(row['BB_Width'])
                close_price = float(row['Close'])
                
                # ⚡ SUPERVISOR GATEWAYS (Adjusted for Z-scored data lines)
                if bb_width_normalized < -0.5: continue  # Exclude extreme range compressions
                if net_spread < 0.05: continue          # Enforce an active 5% confirmation edge spread
                
                # Sizing calculations based on model conviction parameters
                allocated_capital = cash * 0.50 if net_spread < 0.12 else cash * 1.0
                cash -= allocated_capital
                
                # Generate clean fixed standard percentage bounds to insulate from normalized variables
                atr_surrogate_buffer = close_price * 0.015
                
                if direction == "BUY":
                    stop_loss_target = close_price - (1.5 * atr_surrogate_buffer)
                    take_profit_target = close_price + (3.0 * atr_surrogate_buffer)
                else:
                    stop_loss_target = close_price + (1.5 * atr_surrogate_buffer)
                    take_profit_target = close_price - (3.0 * atr_surrogate_buffer)
                    
                active_position = {
                    "ticker": ticker,
                    "type": direction,
                    "entry_price": close_price,
                    "capital": allocated_capital,
                    "stop_loss": stop_loss_target,
                    "take_profit": take_profit_target
                }
                break  # Order matching committed for this timestamp

        # 🧼 3. RECORD DAILY BALANCED VALUATION TAPE
        current_portfolio_value = cash
        if active_position is not None:
            current_portfolio_value += active_position['capital']
        portfolio_history.append(current_portfolio_value)

    # 📊 4. COMPUTE INSTITUTIONAL METRICS SUMMARY
    portfolio_history = np.array(portfolio_history)
    total_return = ((portfolio_history[-1] - starting_capital) / starting_capital) * 100
    
    running_max = np.maximum.accumulate(portfolio_history)
    drawdowns = (portfolio_history - running_max) / running_max
    max_drawdown = np.min(drawdowns) * 100 if len(drawdowns) > 0 else 0.0
    
    trades_df = pd.DataFrame(trade_logs)
    win_rate = 0.0
    profit_factor = 0.0
    
    if not trades_df.empty:
        wins = trades_df[trades_df['result'] == 'TP']
        losses = trades_df[trades_df['result'] == 'SL']
        win_rate = (len(wins) / len(trades_df)) * 100
        
        gross_profits = wins['pnl'].sum()
        gross_losses = abs(losses['pnl'].sum())
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else gross_profits

    print(f"\n========================================================")
    print(f"🎯 BACKTEST SIMULATION COMPLETE (1-YEAR TIME HORIZON)")
    print(f"========================================================")
    print(f"📈 Final Account Value  : ₹{portfolio_history[-1]:,.2f}")
    print(f"🚀 Cumulative Return     : {total_return:.2f}%")
    print(f"🛡️ Maximum Drawdown (MDD): {max_drawdown:.2f}%")
    print(f"📊 Closed Trade Counts  : {len(trades_df)}")
    print(f"🟢 Win Rate percentage  : {win_rate:.2f}%")
    print(f"💸 Profit Factor        : {profit_factor:.2f}")
    print(f"========================================================")

    plt.figure(figsize=(12, 6))
    plt.plot(test_dates, portfolio_history, color='#00ffcc', linewidth=2, label='CandleFlow Equity Curve')
    plt.title('CandleFlow Attention-LSTM Compounding Account Equity Performance Plot')
    plt.xlabel('Timeline Sessions')
    plt.ylabel('Portfolio Valuation (INR)')
    plt.grid(True, color='#2d3748', linestyle='--')
    plt.style.use('dark_background')
    plt.savefig('data/backtest_performance.png')
    print("📈 Equity curve plot saved successfully to data/backtest_performance.png")

if __name__ == "__main__":
    run_portfolio_backtest()