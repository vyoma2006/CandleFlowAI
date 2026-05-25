import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

LOG_FILE = 'data/live_signal_logs.csv'

def track_forward_performance():
    """
    Scans live signal ledger logs, updates historical forward-day close targets 
    from yfinance, and checks system accuracy milestones natively.
    """
    if not os.path.exists(LOG_FILE):
        print("❌ Error: live_signal_logs.csv does not exist yet. Run some API lookups first!")
        return

    # Load logging sheet
    df = pd.read_csv(LOG_FILE)
    if df.empty:
        print("ℹ️ Signal ledger is currently empty. No validation targets to track.")
        return

    # Convert Timestamp string to datetime objects safely
    df['Timestamp_dt'] = pd.to_datetime(df['Timestamp'])
    now = datetime.now()
    
    updated_rows = 0
    print("📡 Scanning for unresolved forward validation paths...")

    for idx, row in df.iterrows():
        # Only process logs that are still marked as OPEN
        if row['Status'] != 'OPEN':
            continue
            
        ticker = row['Ticker']
        signal_time = row['Timestamp_dt']
        days_elapsed = (now - signal_time).days
        
        # If it has not been at least 1 day since the signal, skip for now
        if days_elapsed < 1:
            continue

        # Download a clean forward historical slice starting from signal timestamp
        start_fetch = signal_time.strftime('%Y-%m-%d')
        end_fetch = (now + timedelta(days=2)).strftime('%Y-%m-%d')
        
        try:
            hist = yf.download(ticker, start=start_fetch, end=end_fetch, interval='1d', progress=False)
            if hist.empty:
                continue
                
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)
                
            hist = hist.dropna(subset=['Close'])
            
            # Extract closing price values chronologically after the signal date
            forward_closes = hist['Close'].values
            
            # The first entry in history is typically the day of/day after signal execution
            # Assign parameters depending on how many bars have completed post-event
            if len(forward_closes) >= 2 and pd.isna(row['Forward_Day1_Price']):
                df.at[idx, 'Forward_Day1_Price'] = round(float(forward_closes[1]), 2)
                updated_rows += 1
                
            if len(forward_closes) >= 4 and pd.isna(row['Forward_Day3_Price']):
                df.at[idx, 'Forward_Day3_Price'] = round(float(forward_closes[3]), 2)
                updated_rows += 1
                
            if len(forward_closes) >= 6 and pd.isna(row['Forward_Day5_Price']):
                df.at[idx, 'Forward_Day5_Price'] = round(float(forward_closes[5]), 2)
                df.at[idx, 'Status'] = 'RESOLVED' # Seal the log entry row
                updated_rows += 1
                
        except Exception as err:
            print(f"⚠️ Failed to resolve tracking parameters for {ticker} on row {idx}: {err}")

    if updated_rows > 0:
        # Drop temporary tracking column and rewrite ledger with complete metrics
        df = df.drop(columns=['Timestamp_dt'])
        df.to_csv(LOG_FILE, index=False)
        print(f"✅ Performance Tracker completed: Updated {updated_rows} entries in the ledger.")
    else:
        print("ℹ️ No new forward closing targets ready for tracking yet. Waiting for market sessions.")

def generate_validation_summary():
    """
    Computes real-time precision and breakout capturing stats on the logged data.
    """
    if not os.path.exists(LOG_FILE):
        return
        
    df = pd.read_csv(LOG_FILE)
    resolved_df = df[df['Forward_Day1_Price'].notna()].copy()
    
    if resolved_df.empty:
        print("\n📊 Validation Statistics: Waiting for Day 1 forward close points...")
        return
        
    print("\n" + "="*50)
    print("📈 FORWARD VALIDATION LIVE AUDIT SUMMARY")
    print("="*50)
    print(f"Total Logged Predictions Tracked: {len(df)}")
    print(f"Resolved Performance Samples:    {len(resolved_df)}")
    
    # Calculate directional outcome on Day 1
    resolved_df['Day1_Return'] = ((resolved_df['Forward_Day1_Price'] - resolved_df['Live_Price']) / resolved_df['Live_Price']) * 100
    
    # Look closely at how STRONG BUY alerts perform
    buys = resolved_df[resolved_df['Final_Signal'] == 'STRONG BUY']
    if not buys.empty:
        win_rate = (buys['Day1_Return'] > 0).mean() * 100
        avg_ret = buys['Day1_Return'].mean()
        print(f"\n🟢 [STRONG BUY] Signal Intercepts: {len(buys)}")
        print(f"   ↳ Forward Day 1 Accuracy (Win Rate): {win_rate:.2f}%")
        print(f"   ↳ Average Forward Day 1 Return:       {avg_ret:.2f}%")
    else:
        print("\n🟢 [STRONG BUY] Signal Intercepts: 0 entries captured yet.")
        
    print("="*50 + "\n")

if __name__ == "__main__":
    track_forward_performance()
    generate_validation_summary()