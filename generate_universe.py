import os
import json
from nselib import capital_market

print("📡 Fetching live master equity directory from National Stock Exchange...")

try:
    # 🚀 Download the entire live equity sheet in 1 single request
    df = capital_market.equity_list()
    
    stocks_dict = {}
    
    # Iterate through the rows safely
    for _, row in df.iterrows():
        symbol = str(row['SYMBOL']).strip()
        name = str(row['NAME OF COMPANY']).strip()
        
        # Skip headings or empty rows if any exist in the exchange sheet
        if not symbol or "SYMBOL" in symbol.upper():
            continue
            
        # Clean corporate suffixes slightly to keep dropdown layout crisp
        clean_name = name.replace(" Limited", " Ltd").replace(" LTD", " Ltd")
        
        # Save key-value format to match your brain/main.py configuration
        stocks_dict[symbol] = clean_name

    # Ensure target folder directory exists
    target_dir = os.path.join("brain", "data")
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "nse_tickers.json")

    # Save directly over your backend's local database file
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(stocks_dict, f, indent=4)
        
    print(f"✨ Success! Generated '{target_file}' with {len(stocks_dict)} live NSE corporate equities.")

except Exception as e:
    print(f"🚨 Generation failed: {e}")