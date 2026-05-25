import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Advanced feature engineering pipeline for CandleFlow AI.
    Upgraded with institutional volume anchors, non-linear variance,
    momentum derivatives, and macro regime filters.
    """
    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ----------------------------------------------------
    # 1. CORE TREND & MOMENTUM BASE LAYERS
    # ----------------------------------------------------
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Price_to_SMA20'] = df['Close'] / df['SMA_20']
    
    # 🔥 REGIME FEATURE 1: Trend Strength Core (Normalized EMA Spread)
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_Diff_Pct'] = (df['EMA_20'] - df['EMA_50']) / (df['EMA_50'] + 1e-9)
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))

    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # ----------------------------------------------------
    # 2. VOLATILITY ENGINE (BOLLINGER & ATR CRUNCHING)
    # ----------------------------------------------------
    df['BB_Middle'] = df['SMA_20']
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']

    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()

    # ----------------------------------------------------
    # 3. VOLUME VALIDATION & TREND STRENGTH
    # ----------------------------------------------------
    df['Vol_SMA5'] = df['Volume'].rolling(window=5).mean()
    df['Volume_Shock'] = df['Volume'] / (df['Vol_SMA5'] + 1e-9)

    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / ((df['High'] - df['Low']) + 1e-9)
    mf_volume = mf_multiplier * df['Volume']
    df['CMF'] = mf_volume.rolling(window=21).sum() / (df['Volume'].rolling(window=21).sum() + 1e-9)

    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff()
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)
    
    tr_sum = true_range.rolling(window=14).sum() + 1e-9
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=14).sum() / tr_sum)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=14).sum() / tr_sum)
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    df['ADX'] = dx.rolling(window=14).mean()

    # ----------------------------------------------------------------------
    # 🚀 STATIONARY QUANT MATRIX ENGINE ENHANCEMENTS
    # ----------------------------------------------------------------------
    df['MACD_Pct'] = df['MACD'] / (df['Close'] + 1e-9)
    df['MACD_Hist_Pct'] = df['MACD_Hist'] / (df['Close'] + 1e-9)

    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    df['VWAP'] = (typical_price * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1e-9)
    df['VWAP_Dist'] = df['Close'] / df['VWAP']

    df['MACD_Hist_Slope'] = (df['MACD_Hist'].diff(periods=2) / (df['Close'] + 1e-9)) * 100

    price_trend_5d = df['Close'].diff(periods=5)
    rsi_trend_5d = df['RSI'].diff(periods=5)
    df['RSI_Divergence'] = np.where(price_trend_5d * rsi_trend_5d < 0, 1.0, 0.0)

    df['ATR_Volatility'] = df['ATR'] / df['Close']
    df['ATR_Pct'] = df['ATR_Volatility']

    # 1. Garman-Klass Intraday Volatility
    log_hl = np.log(df['High'] / (df['Low'] + 1e-9))
    log_cc = np.log(df['Close'] / (df['Open'] + 1e-9))
    df['Garman_Klass'] = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_cc ** 2)

    # 2. Momentum Derivatives (Velocity & Acceleration)
    df['RSI_Velocity'] = df['RSI'].diff(periods=1)
    df['RSI_Acceleration'] = df['RSI_Velocity'].diff(periods=1)

    # 🔥 REGIME FEATURE 2: Momentum Pressure Core (5-Day Rate of Change)
    df['ROC_5'] = df['Close'].pct_change(periods=5)

    df = df.dropna()
    return df