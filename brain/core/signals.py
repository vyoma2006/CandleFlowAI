def generate_basic_signal(data):
    """Generates a simple Buy/Sell/Hold signal based on RSI."""
    # 1. Grab the last row
    latest = data.iloc[-1]
    
    # 2. Extract the value safely
    # We use .values[0] if it's a Series, or just the value if it's a scalar
    try:
        rsi_value = latest['RSI']
        if hasattr(rsi_value, 'values'):
            rsi = float(rsi_value.values[0])
        else:
            rsi = float(rsi_value)
    except Exception:
        # Fallback if indexing is still weird
        rsi = 50.0 

    # 3. Decision Logic
    if rsi < 30:
        return "BUY"
    elif rsi > 70:
        return "SELL"
    else:
        return "NEUTRAL"