import json
import os

STORAGE_PATH = 'data/user_portfolio.json'

def ensure_data_exists():
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, 'w') as f:
            json.dump([], f)

def get_portfolio():
    ensure_data_exists()
    with open(STORAGE_PATH, 'r') as f:
        return json.load(f)

def toggle_ticker(ticker):
    ensure_data_exists()
    data = get_portfolio()
    # Add if missing, remove if present (Toggle)
    if ticker in data:
        data.remove(ticker)
    else:
        data.append(ticker)
    with open(STORAGE_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    return data