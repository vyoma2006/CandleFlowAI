import os
import json
import pandas as pd
import numpy as np

LOG_FILE = "logs/calibration_matrix.json"

def log_inference_outcome(ticker: str, raw_prob: float, price_at_inference: float, lookahead_days: int = 2):
    """
    Logs raw inference scores alongside market entry prices. 
    Used to build historical reliability bins and fit Platt Scaling models.
    """
    os.makedirs("logs", exist_ok=True)
    
    log_entry = {
        "ticker": ticker,
        "raw_prob": float(raw_prob),
        "entry_price": float(price_at_inference),
        "timestamp": str(pd.Timestamp.now()),
        "lookahead_days": lookahead_days,
        "realized_outcome": None # Populated asynchronously during walk-forward validation passes
    }
    
    # Append to chronological array cache
    records = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                records = json.load(f)
        except:
            records = []
            
    records.append(log_entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(records, f, indent=4)
    print(f"📊 Tracking metric logged for {ticker} | Score: {raw_prob:.4f}")