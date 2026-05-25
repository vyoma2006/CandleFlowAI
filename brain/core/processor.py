import os
import yfinance as yf
import pandas as pd
import numpy as np
from core.indicators import calculate_indicators

TICKERS = [
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 
    'SBIN.NS', 'LT.NS', 'BHARTIARTL.NS', 'ITC.NS', 'AXISBANK.NS', 'SUNPHARMA.NS',
    'TMPV.NS', 'ETERNAL.NS', 'BAJFINANCE.NS', 'ADANIENT.NS', 'HAL.NS', 
    'BEL.NS', 'IRFC.NS', 'TRENT.NS', 'INDIGO.NS', 'COALINDIA.NS'
]

def clean_and_normalize_asset_dataframe(df: pd.DataFrame, features: list) -> pd.DataFrame:
    """
    Cleans features and removes lookahead bias. Uses an expanding window 
    to handle outlier clipping and Z-score standardization dynamically.
    """
    df = df.copy()
    
    # 🧼 STAGE 1: Lookahead-Free IQR Outlier Clipping
    for col in features:
        Q1 = df[col].expanding(min_periods=30).quantile(0.25)
        Q3 = df[col].expanding(min_periods=30).quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)
        df[col] = np.clip(df[col], lower_bound, upper_bound)
        
    # 🧼 STAGE 2: Expanding Window Z-Score Normalization
    for col in features:
        running_mean = df[col].expanding(min_periods=20).mean()
        running_std = df[col].expanding(min_periods=20).std() + 1e-9
        df[col] = (df[col] - running_mean) / running_std
        
    return df

def prepare_master_dataset():
    print("🌍 Fetching Global Market Regime Benchmark Index (^NSEI)...")
    nifty_df = yf.download("^NSEI", period="5y", interval="1d", progress=False)
    if isinstance(nifty_df.columns, pd.MultiIndex):
        nifty_df.columns = nifty_df.columns.get_level_values(0)
    nifty_df = calculate_indicators(nifty_df)
    
    nifty_benchmark = pd.DataFrame({
        'Market_RSI': nifty_df['RSI']
    }, index=nifty_df.index)

    all_frames = []

    for ticker in TICKERS:
        print(f"🧹 Deep Cleaning & Processing Asset Vector: {ticker}...")
        df = yf.download(ticker, period="5y", interval="1d", progress=False)
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[(df['Close'] >= 30) & (df['Volume'] > 25000)].copy()
        if len(df) < 150: continue

        df = calculate_indicators(df)
        df = df.join(nifty_benchmark, how='left')

        df['RSI_Lag_1'] = df['RSI'].shift(1)

        # 🎯 THE NON-REDUNDANT HIGH-SIGNAL FEATURE MONITOR
        FEATURES = [
            'RSI', 'RSI_Lag_1', 'Price_to_SMA20', 'MACD_Hist_Pct', 
            'BB_Width', 'ATR_Pct', 'CMF', 'Volume_Shock', 'Market_RSI'
        ]
        
        # 🎯 VOLATILITY-GATED HIGH-CONTRAST DIRECTIONAL FILTERING
        # Uses a 0.15x ATR hurdle to separate real trends from flat market noise
        forward_2d_return = (df['Close'].shift(-2) - df['Close']) / df['Close']
        volatility_hurdle = df['ATR_Pct'] * 0.15
        
        conditions = [
            (forward_2d_return > volatility_hurdle),   # Confirmed Bullish Breakout (1)
            (forward_2d_return < -volatility_hurdle)   # Confirmed Bearish Breakdown (0)
        ]
        # Assign a placeholder flag (-1) for rows trapped in the flat middle zone
        df['Target'] = np.select(conditions, [1, 0], default=-1)

        # Process lookahead-free normalization scaling across our 9 pristine variables
        df_cleaned = clean_and_normalize_asset_dataframe(df, FEATURES)
        
        # 🪓 THE NOISE EXCLUSION GATEWAY: Discards all flat, un-actionable range sequences
        df_final = df_cleaned[df_cleaned['Target'] != -1].copy()
        
        df_final['Target'] = df_final['Target'].astype(int)
        df_final['Ticker'] = ticker
        all_frames.append(df_final)

    master_df = pd.concat(all_frames)
    os.makedirs('data', exist_ok=True)
    master_df.to_csv('data/training_data.csv', index=True)
    
    print(f"\n========================================================")
    print(f"✅ Success! High-Contrast Volatility-Gated Dataset Compiled.")
    print(f"📈 Total Continuous Balanced Rows Generated: {len(master_df)}")
    print(master_df['Target'].value_counts().sort_index())
    print(f"========================================================")

if __name__ == "__main__":
    prepare_master_dataset()