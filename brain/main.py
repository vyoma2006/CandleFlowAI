import sys
import os
# Adds the parent directory (CandleFlow/) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now the imports will work
from bridge.portfolio_manager import get_portfolio, toggle_ticker
import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
import json 
import logging
from contextlib import asynccontextmanager 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from core.indicators import calculate_indicators
from bridge.portfolio_manager import get_portfolio, toggle_ticker

# 🎯 SECURITY & DESERIALIZATION PROTECTION LAYER
from core.lstm_engine import TemporalAttention
from core.paper_broker import PaperBroker

try:
    from tensorflow.keras.models import load_model as load_lstm_model
    HAS_TF = True
except ImportError:
    HAS_TF = False

load_dotenv()

# Bind directly into Uvicorn's live terminal logging channel output stream
logger = logging.getLogger("uvicorn.error")

# ----------------------------------------------------------------------
# 💾 APPLICATION LIFESPAN & HIGH-SPEED RAM CACHE MATRIX
# ----------------------------------------------------------------------
GLOBAL_TICKER_CACHE = []

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Triggers exactly once on server boot up using modern FastAPI specifications.

    Loads and builds the master stock registry universe straight from local storage.
    """
    global GLOBAL_TICKER_CACHE
    logger.info("📡 --- [CandleFlow Core] INITIALIZING LOCAL FILESYSTEM SEEDER ---")
    
    # Calculate file location paths dynamically relative to this main.py file position
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_json_path = os.path.join(base_dir, "data", "nse_tickers.json")
    
    try:
        if os.path.exists(local_json_path):
            with open(local_json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                
            GLOBAL_TICKER_CACHE = [
                {
                    "symbol": f"{symbol}.NS", 
                    "raw_symbol": symbol.strip().lower(),
                    "name": name.strip()
                }
                for symbol, name in raw_data.items()
            ]
            logger.info(f"✅ [CandleFlow Core] Local Cache Seeding Complete! Loaded {len(GLOBAL_TICKER_CACHE)} structural equities cleanly from disk.")
        else:
            raise FileNotFoundError(f"Master dataset matrix asset missing at: {local_json_path}")
            
    except Exception as e:
        logger.error(f"🚨 Local filesystem initialization failure: {e}. Reverting to safety baseline array.")
        fallback_raw = {
            "ADANIENT": "Adani Enterprises Ltd", "AXISBANK": "Axis Bank Ltd",
            "BAJFINANCE": "Bajaj Finance Ltd", "BHARTIARTL": "Bharti Airtel Ltd",
            "COALINDIA": "Coal India Ltd", "FEDERALBNK": "The Federal Bank Ltd",
            "HDFCBANK": "HDFC Bank Ltd", "HINDUNILVR": "Hindustan Unilever Ltd",
            "INFY": "Infosys Ltd", "ITC": "ITC Ltd", "ICICIBANK": "ICICI Bank Ltd",
            "JSWSTEEL": "JSW Steel Ltd", "MARUTI": "Maruti Suzuki India Ltd",
            "NESTLEIND": "Nestle India Ltd", "RELIANCE": "Reliance Industries Ltd",
            "SBIN": "State Bank of India", "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
            "TCS": "Tata Consultancy Services Ltd", "TATASTEEL": "Tata Steel Ltd",
            "TITAN": "Titan Company Ltd", "WIPRO": "Wipro Ltd"
        }
        GLOBAL_TICKER_CACHE = [
            {"symbol": f"{s}.NS", "raw_symbol": s.lower(), "name": n}
            for s, n in fallback_raw.items()
        ]
        logger.info(f"✅ Safe Backstop Array Engaged: Loaded {len(GLOBAL_TICKER_CACHE)} fallback nodes.")

    yield 
    logger.info("🛑 Cleaning memory tracking channels.")

# Initialize application instance under lifecycle constraints
app = FastAPI(title="CandleFlow Core Brain Engine Layer", lifespan=application_lifespan)

broker = PaperBroker()

# 🧠 DIRECTORY LSTM ATTENTION PARSING LAYER
LSTM_PATH = 'models/candleflow_lstm.keras'  
lstm_model = None

if HAS_TF and os.path.exists(LSTM_PATH):
    try:
        def focal_loss_fixed(y_true, y_pred): return y_pred

        lstm_model = load_lstm_model(
            LSTM_PATH, 
            custom_objects={
                "focal_loss_fixed": focal_loss_fixed,
                "TemporalAttention": TemporalAttention  
            },
            compile=False
        )
        print("🤖 Upgraded Dual-Class Pure Directional Sigmoid Engine mounted successfully!")
    except Exception as e:
        print(f"🚨 Warning: Model file reconstruction failed: {e}")
else:
    print("❌ Error: Primary directional weight matrix missing!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_local_indian_news(ticker_symbol):
    clean_name = ticker_symbol.split('.')[0]
    rss_url = f"https://news.google.com/rss/search?q={clean_name}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        response = requests.get(rss_url, timeout=3)
        root = ET.fromstring(response.content)
        return [{"headline": item.find('title').text.rsplit(' - ', 1)[0], "url": item.find('link').text, "source": "Google News"} for item in root.findall('.//item')[:3]]
    except:
        return []

# ----------------------------------------------------------------------
# 🔍 INTERACTIVE ROUTE: STRICT SCREENER PREFIX-ONLY SEARCH ENGINE
# ----------------------------------------------------------------------
@app.get("/api/tickers/search")
def search_tickers_dynamically(q: str = ""):
    """Scans cache instantly and enforces strict prefix matching.

    Completely eliminates random inner-string substring matches.
    """
    query = q.lower().strip()
    if not query:
        return []
        
    prefix_matches = []
    
    # Iterate through cache and collect ONLY literal prefix starters
    for stock in GLOBAL_TICKER_CACHE:
        raw_sym = stock["raw_symbol"]
        name_lower = stock["name"].lower().strip()
        
        # 🎯 STRICT RULE: Ticker code OR company name MUST start directly with the typed string
        if raw_sym.startswith(query) or name_lower.startswith(query):
            prefix_matches.append({"symbol": stock["symbol"], "name": stock["name"]})

    # Sort everything cleanly from A to Z by company name
    sorted_results = sorted(prefix_matches, key=lambda x: x["name"])
    
    # Return the clean capped results
    return sorted_results[:8]

# ----------------------------------------------------------------------
# 📂 ROUTE: PERSISTENT WATCHLIST MANAGEMENT
# ----------------------------------------------------------------------
@app.get("/api/user-portfolio")
def api_get_portfolio():
    return {"tickers": get_portfolio()}

@app.post("/api/user-portfolio/toggle")
def api_toggle_portfolio(payload: dict):
    ticker = payload.get("ticker", "").upper().strip()
    if not ticker:
        return {"status": "error", "message": "No ticker provided"}
    updated_list = toggle_ticker(ticker)
    return {"status": "success", "tickers": updated_list}

# ----------------------------------------------------------------------
# 📈 ROUTE 1: REAL-TIME PORTFOLIO & RISK BOUNDARY TRACKER
# ----------------------------------------------------------------------
@app.get("/api/portfolio")
def get_live_portfolio_dashboard():
    active_positions = broker.wallet["active_positions"]
    current_prices = {}
    for ticker in active_positions.keys():
        try:
            t_data = yf.Ticker(ticker).history(period="1d")
            if not t_data.empty:
                current_prices[ticker] = float(t_data['Close'].iloc[-1])
        except Exception as e:
            print(f"🚨 Real-time pricing feed connection interrupted for {ticker}: {e}")

    broker.scan_active_positions_for_exits(current_prices)
    return broker.get_portfolio_summary(current_prices)

# ----------------------------------------------------------------------
# 💳 TRANSACTION GATEWAY: LIVE PORTFOLIO POSITION ROUTING
# ----------------------------------------------------------------------
@app.post("/api/portfolio/add")
def allocate_asset_to_portfolio(payload: dict):
    """Intercepts frontend selections to book a new virtual position inside 

    the running paper broker memory instance.
    """
    ticker = payload.get("ticker", "").upper().strip()
    if not ticker:
        return {"status": "error", "message": "Missing symbol token."}
        
    try:
        ticker_data = yf.Ticker(ticker).history(period="1d")
        if ticker_data.empty:
            return {"status": "error", "message": f"Could not stream market ticks for {ticker}"}
            
        latest_close = float(ticker_data['Close'].iloc[-1])
        
        # Open an initial buy allocation position inside our running ledger data
        was_opened = broker.open_position_live(
            ticker=ticker,
            direction="BUY",
            close_price=latest_close,
            net_spread=0.15,               
            atr_buffer=latest_close * 0.02 
        )
        
        if was_opened:
            return {"status": "success", "message": f"Successfully allocated {ticker} into portfolio matrix."}
        else:
            return {"status": "error", "message": "Transaction rejected: Insufficient cash balance or limit breached."}
            
    except Exception as e:
        return {"status": "error", "message": f"Execution gate error: {str(e)}"}

# ----------------------------------------------------------------------
# 📡 ROUTE 2: LOOKUP GATEWAY & AUTOMATED LIVE ORDER EXECUTION
# ----------------------------------------------------------------------
@app.get("/api/stock-info/{query}")
def get_stock_full_info(query: str):
    try:
        u_query = query.upper().strip()
        best_ticker = None
        
        if u_query.endswith(".NS"):
            best_ticker = u_query
        else:
            if u_query in ["RELIANCE", "RIL"]: best_ticker = "RELIANCE.NS"
            elif u_query in ["WIPRO", "WIT"]: best_ticker = "WIPRO.NS"
            elif u_query in ["INFY", "INFOSYS"]: best_ticker = "INFY.NS"
            elif u_query in ["TCS", "TATA CONSULTANCY"]: best_ticker = "TCS.NS"
            elif u_query == "SAIL": best_ticker = "SAIL.NS"
                
            if not best_ticker:
                search = yf.Search(query, max_results=10)
                for result in search.quotes:
                    symbol = result.get('symbol', '')
                    if result.get('quoteType') == 'EQUITY' and symbol.endswith('.NS'):
                        best_ticker = symbol
                        break
                if not best_ticker:
                    best_ticker = f"{u_query}.NS"

        if best_ticker.endswith(".NS.NS"):
            best_ticker = best_ticker.replace(".NS.NS", ".NS")

        df = yf.download(best_ticker, period="2y", interval="1d", progress=False, ignore_tz=True)
        nifty_df = yf.download("^NSEI", period="2y", interval="1d", progress=False, ignore_tz=True)
        
        if df.empty or len(df) < 100 or nifty_df.empty:
            return {"error": "Insufficient history available for expanding sequence scaling."}

        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if isinstance(nifty_df.columns, pd.MultiIndex): nifty_df.columns = nifty_df.columns.get_level_values(0)
            
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        nifty_df = nifty_df.dropna(subset=['Open', 'High', 'Low', 'Close'])

        latest_close = float(df['Close'].iloc[-1])
        previous_close = float(df['Close'].iloc[-2])
        daily_change = latest_close - previous_close
        daily_change_pct = (daily_change / previous_close) * 100

        df_features = calculate_indicators(df)
        nifty_features = calculate_indicators(nifty_df)
        
        nifty_features['Market_RSI'] = nifty_features['RSI']
        df_features = df_features.drop(columns=['Market_RSI'], errors='ignore')
        df_features = df_features.join(nifty_features[['Market_RSI']], how='left')
        df_features['Market_RSI'] = df_features['Market_RSI'].ffill().bfill()

        df_features['RSI_Lag_1'] = df_features['RSI'].shift(1)

        FEATURES = [
            'RSI', 'RSI_Lag_1', 'Price_to_SMA20', 'MACD_Hist_Pct', 
            'BB_Width', 'ATR_Pct', 'CMF', 'Volume_Shock', 'Market_RSI'
        ]
        
        df_inference = df_features[FEATURES].dropna().copy()

        df_scaled = pd.DataFrame(index=df_inference.index)
        for col in FEATURES:
            running_mean = df_inference[col].expanding(min_periods=20).mean()
            running_std = df_inference[col].expanding(min_periods=20).std() + 1e-9
            df_scaled[col] = (df_inference[col] - running_mean) / running_std

        df_inference_ready = df_scaled.dropna(subset=FEATURES)
        if len(df_inference_ready) < 20:
            return {"error": "Insufficient valid frames for lookahead-free parsing."}

        all_features_matrix = df_inference_ready[FEATURES].to_numpy()
        scaled_sequence = all_features_matrix[-20:]

        p_sell, p_buy = 0.50, 0.50
        engine_mode = "Dual-Class Sigmoid Compass + Active Paper Trader"

        if lstm_model is not None:
            lstm_tensor_input = np.expand_dims(scaled_sequence, axis=0)
            raw_pred = float(lstm_model.predict(lstm_tensor_input, verbose=0)[0][0])
            p_buy = raw_pred
            p_sell = 1.0 - raw_pred
        else:
            return {"error": "Directional recurrent array is uninitialized."}

        # ⚡ 4. SUPERVISOR GATEWAY ENGINE (UPDATED THRESHOLDS)
        net_spread = abs(p_buy - p_sell)
        direction = "BUY" if p_buy > p_sell else "SELL"
        display_confidence = p_buy if direction == "BUY" else p_sell
        current_bb_width = float(df_features['BB_Width'].iloc[-1] * 100)
        
        atr_raw_val = float(df_features['ATR'].iloc[-1])
        position_status_text = "No Live Positions Modified // Monitoring Feature Matrix"

        print(f"\n📡 --- QUANT LIVE TELEMETRY LOG FOR {best_ticker} ---")
        print(f"  [Raw Sigmoid Node Prediction]: {raw_pred:.4f}")
        print(f"  [p_sell]: {p_sell:.4f}  |  [p_buy]: {p_buy:.4f}")
        print(f"  [Spread]: {net_spread:.4f}  |  [BB Width]: {current_bb_width:.2f}%")
        print(f"----------------------------------------------------------\n")

        # 🛠️ RULE 1: VOLATILITY COMPRESSION OVERRIDE
        if current_bb_width < 3.0:  
            ai_signal_text = "HOLD"
            confidence_band = f"Volatility Squeeze Active ({current_bb_width:.1f}% Compression) // Range Bound Trap"
            
        # 🛠️ RULE 2: DIRECTIONAL PROBABILITY SPREAD EVALUATION
        else:
            if direction == "BUY":
                if net_spread >= 0.08:  
                    ai_signal_text = "STRONG BUY"
                    confidence_band = f"High-Velocity Breakout Trajectory Confirmed ({p_buy*100:.1f}%)"
                elif net_spread >= 0.01:  
                    ai_signal_text = "BUY"
                    confidence_band = f"Structural Momentum Alignment Confirmed ({p_buy*100:.1f}%)"
                else:
                    ai_signal_text = "HOLD"
                    confidence_band = f"Neutral Model Confidence Spread Matrix ({net_spread*100:.1f}%)"
            else:
                if net_spread >= 0.08:  
                    ai_signal_text = "STRONG SELL"
                    confidence_band = f"Premium Bearish Acceleration Confirmed ({p_sell*100:.1f}%)"
                elif net_spread >= 0.01:  
                    ai_signal_text = "SELL"
                    confidence_band = f"Validated Downside Trend Continuity ({p_sell*100:.1f}%)"
                else:
                    ai_signal_text = "HOLD"
                    confidence_band = f"Neutral Model Confidence Spread Matrix ({net_spread*100:.1f}%)"

        # 🛠️ RULE 3: BROADER MARKET PROTECTION COVERAGE
        market_slope = float(df_features['MACD_Hist_Slope'].iloc[-1]) if 'MACD_Hist_Slope' in df_features.columns else 0.0
        if market_slope < -0.25 and "BUY" in ai_signal_text:  
            ai_signal_text = "HOLD"
            confidence_band = "Macro Index Downside Momentum Protection Override Active"
            
        if "BUY" in ai_signal_text or "SELL" in ai_signal_text:
            was_opened = broker.open_position_live(
                ticker=best_ticker,
                direction="BUY" if "BUY" in ai_signal_text else "SELL",
                close_price=latest_close,
                net_spread=net_spread,
                atr_buffer=atr_raw_val
            )
            if was_opened:
                position_status_text = f"Live Signal Verified // Allocation Committed to Database"
            else:
                position_status_text = f"Signal Ignored // Stand Alone Rules Applied (Active Position Limit or Low Cash)"

        local_news = fetch_local_indian_news(best_ticker)

        def safe_float(val, default=0.0):
            try:
                f_val = float(val)
                return default if np.isnan(f_val) or np.isinf(f_val) else f_val
            except: return default

        return {
            "ticker": best_ticker,
            "price": round(safe_float(latest_close), 2),
            "daily_change": round(safe_float(daily_change), 2),
            "daily_change_pct": round(safe_float(daily_change_pct), 2),
            "ai_signal": ai_signal_text,
            "confidence": f"{round(display_confidence * 100, 2)}%",  
            "confidence_band": confidence_band,
            "position_status": position_status_text,
            "engine_mode": engine_mode,
            "news": local_news,
            "metrics": {
                "rsi": round(safe_float(df_features['RSI'].iloc[-1]), 2),
                "price_to_sma20": round(safe_float(df_features['Price_to_SMA20'].iloc[-1]), 3),
                "macd": round(safe_float(df_features['MACD'].iloc[-1]), 2),       
                "macd_hist": round(safe_float(df_features['MACD_Hist'].iloc[-1]), 2), 
                "bb_width": round(safe_float(df_features['BB_Width'].iloc[-1] * 100), 2),     
                "atr": round(safe_float(df_features['ATR'].iloc[-1]), 2),          
                "adx": round(safe_float(df_features['ADX'].iloc[-1]), 2) if 'ADX' in df_features.columns else 0.0
            }
        }
    except Exception as e:
        return {"error": f"Inference System Exception: {str(e)}"}