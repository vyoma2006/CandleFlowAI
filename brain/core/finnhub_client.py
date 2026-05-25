import requests

FINNHUB_KEY = "YOUR_FREE_KEY_HERE" # Get this from finnhub.io

def get_company_meta(ticker):
    """Fetches company logo and industry from Finnhub."""
    # Note: Finnhub uses 'RELIANCE' instead of 'RELIANCE.NS' usually
    clean_ticker = ticker.split('.')[0]
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={clean_ticker}&token={FINNHUB_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {"error": "Could not fetch metadata"}